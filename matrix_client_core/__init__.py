# stdlib
import json
import getpass
import re
import itertools
import sys
import time
import io
import traceback
import queue
import threading

# external deps
import matrix_client.client
import requests

# in-tree deps
import matrix_client_core.notifier as notifier


class CFException(Exception):
	pass


class AccountInfo:
	T_UNDEF = 0
	T_TOKEN = 1
	T_PASSWORD = 2

	def __init__(self):
		self.hs_client_api_url = None
		self.mxid = None
		self.access_token = None
		self.password = None

	def loadfromfile(self, filename):
		with open(filename, "r") as f:
			j = json.load(f)
			self.hs_client_api_url = j['hs_client_api_url']
			self.mxid = j['mxid']
			self.access_token = j['access_token']
		return True

	def savetofile(self, filename):
		d = {
			'hs_client_api_url': self.hs_client_api_url,
			'mxid': self.mxid,
			'access_token': self.access_token	}

		with open(filename, "w") as f:
			s = json.dumps(d, sort_keys=True,
			 indent=4, separators=(',', ': '))
			f.write(s)
		return True

	def _ask(self, question, default, reask, reuse):
		if not reask and default is not None: return default
		if reuse and default is not None:
			prompt = "{0} [{1}]: ".format(question, default)
		else:
			prompt = "{0}: ".format(question)
		answer = input(prompt)
		if reuse and answer == "":
			answer = default
		return answer

	def _askpass(self, question, default, reask):
		if not reask and default is not None: return default
		prompt = "{0}: ".format(question)
		return getpass.getpass(prompt)

	def getfromkeyboard(self, reask=False, reuse=True):
		self.hs_client_api_url = self._ask("Homeserver URL",
							self.hs_client_api_url,
							reask, reuse).rstrip("/")
		self.mxid = self._ask("User ID", self.mxid, reask, reuse)
		self.password = self._askpass("Password", self.password, reask)

	def login_type(self):
		if not self.hs_client_api_url: return self.T_UNDEF
		if not self.mxid: return self.T_UNDEF
		if self.access_token: return self.T_TOKEN
		if self.password: return self.T_PASSWORD
		return self.T_UNDEF

	def __bool__(self):
		return bool(self.login_type())


class RoomList:
	RE_PREFIX = re.compile("^(#[^:]*)")

	def __init__(self, roomsdict):
		# 'roomsdict' should be a dictionary mapping room IDs to room objects,
		# as returned by MatrixClient.get_rooms()

		self.roomsbyid = roomsdict
		self.roomsbyalias = {}
		self.roomsbyprefix = {}	# Note: Can contain list for multiple matches

		for r in roomsdict.values():
			for alias in itertools.chain((r.canonical_alias,), r.aliases):
				if alias is None: continue
				self.roomsbyalias[alias] = r
				m = self.RE_PREFIX.search(alias)
				if not m: continue
				prefix = m.group(1)
				item = self.roomsbyprefix.get(prefix)
				if item is None:
					self.roomsbyprefix[prefix] = r
				elif isinstance(item, list):
					if r not in item: item.append(r)
				elif item != r:
					self.roomsbyprefix[prefix] = [item, r]

	def get_room(self, id_or_alias_or_prefix):
		# Find a room object by ID or alias, and return it

		# We also happen to guarantee that if the result is
		# not None, 'id_or_alias_or_prefix' _uniquely_ identifies the room.

		if id_or_alias_or_prefix in self.roomsbyid:
			return self.roomsbyid[id_or_alias_or_prefix]
		if id_or_alias_or_prefix in self.roomsbyalias:
			return self.roomsbyalias[id_or_alias_or_prefix]
		if id_or_alias_or_prefix in self.roomsbyprefix:
			x = self.roomsbyprefix[id_or_alias_or_prefix]
			try:
				# if it has a length, it's probably a list of rooms
				if len(x) == 1: return x[0]
				return None # Multiple matches is no match
			except TypeError: # x doesn't _have_ a length
				return x  # so probably a room object
		return None

	@staticmethod
	def _best_handle(*args):
		# Return shortest argument which is not None (if any)
		best_match = None
		for a in args:
			if a is None: continue
			if best_match is None \
			   or len(a) < len(best_match): best_match = a
		return best_match

	def get_room_handle(self, id_or_alias_or_prefix):
		# get a convenient short display handle for the room
		# always returns something useful, even if just unmodified id_or_alias_or_prefix
		best_match = None
		room = self.get_room(id_or_alias_or_prefix)
		if room is None: return id_or_alias_or_prefix
		for alias in itertools.chain((room.canonical_alias,), room.aliases):
			if alias is None: continue
			best_match = self._best_handle(best_match, alias)
			m = self.RE_PREFIX.search(alias)
			if not m: continue # This really should never happen, but.
			prefix = m.group(1)
			if self.get_room(prefix) is not None:
				# prefix _uniquely_ identifies the room
				best_match = self._best_handle(best_match, prefix)
		if best_match is None: return id_or_alias_or_prefix
		return best_match


class NoSyncMatrixClient(matrix_client.client.MatrixClient):
	# A subclass of MatrixClient that inhibits syncing until we allow it.

	# This class exists because we want to do some modifications to the
	# object (fixup) before _sync() is called for the first time.

	def __init__(self, *args, **kwargs):
		sync_filter = kwargs.pop('sync_filter', None)
		matrix_client.client.MatrixClient.__init__(self, *args, **kwargs)
		if sync_filter: self.sync_filter = sync_filter

	def _sync(self, *args, **kwargs):
		self.sync_attempted = True
		self.sync_args = args
		self.sync_kwargs = kwargs
		if getattr(self, 'sync_enabled', False):
			matrix_client.client.MatrixClient._sync(self, *args, **kwargs)

	def enable_sync(self):
		self.sync_enabled = True

	def finish_fixup(self):
		# This basically enables syncing, and calls the real _sync if
		# and only if it would have been called by the constructor.

		self.enable_sync()
		if getattr(self, 'sync_attempted', False):
			matrix_client.client.MatrixClient._sync(self, *self.sync_args, **self.sync_kwargs)


class MXClient:
	def __init__(self, accountfilename=None, account=None, sync_filter=None):
		self.accountfilename = accountfilename
		self.account = account
		self.sdkclient = None
		self.sync_filter = sync_filter
		self.initial_sync_timeout_seconds = 600
		self.sync_timeout_seconds = 100
		self.exception_delay_init = 45
		self.exception_delay = self.exception_delay_init
		self.sendq = queue.Queue()
		self.sendcmd = None

	def on_global_timeline_event(self, event):
		self.last_event = event
		roomid = event['room_id']
		roomhandle = self.rooms.get_room_handle(roomid)
		roomprefix = "[{0}]".format(roomhandle)

		sender = event['sender']
		rich_sender = sender
		try:
			rich_sender = "{} ({})".format(sender, event['content']['displayname'])
		except KeyError:
			try:
				rich_sender = "{} ({})".format(sender, event['unsigned']['prev_content']['displayname'])
			except KeyError:
				pass

		if event['type'] == "m.room.member":
			if event['content']['membership'] == "join":
				print(roomprefix, "{} joined".format(rich_sender))
			elif event['content']['membership'] == "leave":
				print(roomprefix, "{} left".format(rich_sender))
			else:
				print(roomprefix, repr(event))
		elif event['type'] == "m.room.message":
			if event['content']['msgtype'] == "m.text":
				inmsg = event['content']['body']
				print(roomprefix, "{}: {}".format(rich_sender, inmsg))
			elif event['content']['msgtype'] == "m.emote":
				print(roomprefix, " * {} {}".format(rich_sender, event['content']['body']))
			else:
				print(roomprefix, " ? {}:{}: {}".format(
					rich_sender,
					event['content']['msgtype'],
					event['content'].get('body', "")))
		else:
			print(roomprefix, repr(event))

		self._reset_exc_delay()

	def _reset_exc_delay(self):
		self.exception_delay = self.exception_delay_init

	def _exc_delay(self):
		ret = self.exception_delay
		self.exception_delay *= 2
		return ret

	def on_exception(self, e):
		print("Exception caught:", traceback.format_exception_only(type(e), e)[-1].strip())
		print("Type /debug to show more info.")
		moreinfo = io.StringIO()
		print("Last event received before exception:", file=moreinfo)
		print(repr(self.last_event), file=moreinfo)
		print("Stack trace:", file=moreinfo)

		traceback.print_exception(type(e), e, e.__traceback__, file=moreinfo)
		self.debug_info = moreinfo.getvalue()
		moreinfo.close()

		delay = self._exc_delay()
		print("Waiting {0} seconds before trying again.".format(delay))
		time.sleep(delay)
		print("Let's go!")

	def sendmsg(self, room_id, msg):
		notifier.notify(__name__, 'mcc.mxc.sendmsg', msg)
		self.sendq.put((room_id, msg))

	def sendrunner(self):
		while True:
			try:
				room_id, msg = self.sendq.get()
				notifier.notify(__name__, 'mcc.mxc.sendrunner.sendcmd', msg)
				self.sendcmd(room_id, msg)
			except queue.Empty:
				print("Queue was empty")
			time.sleep(self.send_sleep_time)

	def start_send_thread(self, sendcmd, send_sleep_time=5):
		self.sendcmd = sendcmd
		self.send_sleep_time = send_sleep_time
		t = threading.Thread(target=self.sendrunner)
		t.daemon = True
		t.start()

	def hook(self):
		# Connect all the listeners, start threads etc.
		self.last_event = None
		m = getattr(self, 'on_global_timeline_event', None)
		if callable(m): self.sdkclient.add_listener(m)
		m = getattr(self, 'on_exception', None)
		if callable(m): self.sdkclient.start_listener_thread(exception_handler=m)
		else: self.sdkclient.start_listener_thread()
		# Only supported by urllib-requests-adapter. NOOP otherwise.
		requests.GLOBAL_TIMEOUT_SECONDS = self.sync_timeout_seconds

	def repl_debug(self, txt):
		""" Show more information about the last error that happened """
		print(getattr(self, 'debug_info', "No errors.\n"), end='')
		return True

	def repl_me(self, txt):
		""" Send an action/emote """
		if not self.foreground_room:
			print("Cannot send message: You have not selected any room. Try /help.")
			return True

		self.foreground_room.send_emote(txt[4:])
		return True

	def repl_list(self, txt):
		""" List the rooms you're a member of """

		print(" ".join(map(self.rooms.get_room_handle, self.rooms.roomsbyid.keys())))
		return True

	def repl_open(self, txt):
		""" Open a room you're already a member of """
		try:
			cmd, handle = txt.split(None, 1)
		except ValueError:
			print("Wrong number of arguments")
			return True

		room = self.rooms.get_room(handle)
		if room is None:
			print("You are not a member of that room. Did you want /join?")
			return True

		print("Opening room %s: %s" % (handle, room.display_name))
		print("Topic:", room.topic)
		self.foreground_room = room

		return True

	def repl_join(self, txt):
		""" Join a room you're not already a member of """
		try:
			cmd, roomid = txt.split(None, 1)
		except ValueError:
			print("Wrong number of arguments")
			return True

		self.foreground_room = self.sdkclient.join_room(roomid)
		print("Opening room %s: %s" % (roomid, self.foreground_room.display_name))
		print("Topic:", self.foreground_room.topic)
		return True

	def repl_quit(self, txt):
		""" Leave """
		return False

	def repl_help(self, txt):
		""" Show this help text """
		cmds = tuple(filter(lambda x: x.startswith('repl_'), dir(self)))
		maxlen = max(map(lambda x: len(x), cmds))
		fmt = "/{{:<{}}}".format(maxlen - 4)
		for mname in cmds:
			cmd = mname[5:]
			m = getattr(self, mname)
			print(fmt.format(cmd + ":"), getattr(m, '__doc__', "").strip())

		return True

	def repl(self, exception_handler=True):
		# Read Eval Print Loop

		# A simple console client loop that can be used as a basis for a client
		# or as a bot manhole.

		if exception_handler is True:
			exception_handler = self.on_exception

		while True:
			try:
				if not self._repl_inner(): break
			except Exception as e:
				if exception_handler is None: raise
				exception_handler(e)

	def _repl_inner(self):
		""" Run a single REPL iteration.

		Returns True if there should be another iteration, False if it
		wants to exit normally. """

		txt = input()
		if txt.startswith('/'):
			if txt.startswith('//'):
				txt = txt[1:]
			else:
				cmd = txt.split(None, 1)[0].lstrip('/')
				m = getattr(self, 'repl_' + cmd, None)
				if callable(m):
					if not m(txt): return False
				else:
					print("Unrecognized command: {!r}. Try /help.".format(cmd))
				return True

		if not self.foreground_room:
			print("Cannot send message: You have not selected any room. Try /help.")
			return True

		send_as_notice = getattr(self, 'is_bot', False)
		if txt.startswith(' '):
			txt = txt[1:]
			send_as_notice = not send_as_notice

		if send_as_notice:
			self.foreground_room.send_notice(txt)
		else:
			self.foreground_room.send_text(txt)

		return True

	def login(self):
		# Only supported by urllib-requests-adapter. NOOP otherwise.
		requests.GLOBAL_TIMEOUT_SECONDS = self.initial_sync_timeout_seconds

		self._ensure_account()
		t = self.account.login_type()
		notifier.notify(__name__, 'mcc.mxc.login.connect', (self.account.hs_client_api_url, self.account.mxid))
		if t == self.account.T_PASSWORD:
			self.sdkclient = NoSyncMatrixClient(self.account.hs_client_api_url, sync_filter=self.sync_filter)
			notifier.notify(__name__, 'mcc.mxc.login.login', (self.account.mxid))
			token = self.sdkclient.login_with_password(self.account.mxid, self.account.password)
			self.account.access_token = token
			self.account.mxid = self.sdkclient.user_id
			self.account.savetofile(self.accountfilename)
		elif t == self.account.T_TOKEN:
			self.sdkclient = NoSyncMatrixClient(
				self.account.hs_client_api_url,
				token=self.account.access_token,
				user_id=self.account.mxid,
				sync_filter=self.sync_filter)
		else:
			raise CFException("MXClient.login(): Cannot login: 'account' is (partially) uninitialized")
		self.sdkclient.enable_sync()

	def first_sync(self):
		notifier.notify(__name__, 'mcc.mxc.first_sync.sync')
		self.sdkclient.finish_fixup()
		notifier.notify(__name__, 'mcc.mxc.first_sync.sync_done')
		self.rooms = RoomList(self.sdkclient.get_rooms())
		self.foreground_room = None

	def _ensure_account(self):
		account = self.account
		if account is None:
			if self.accountfilename is None:
				raise CFException("MXClient.login(): neither 'accountfilename' nor 'account' given")
			account = AccountInfo()
			try:
				account.loadfromfile(self.accountfilename)
			except IOError as e:
				if e.errno != 2: # 2 = File Not Found
					raise
				while True:
					account.getfromkeyboard()
					if account: break
					print("You didn't enter all information correctly. Please try again.")

		self.account = account

