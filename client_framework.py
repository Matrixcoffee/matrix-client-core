# stdlib
import json
import getpass
import re
import itertools
import sys
import time

# external deps
import matrix_client.client


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

	def get_room_handle(self, id_or_alias_or_prefix):
		# get a convenient short display handle for the room
		# always returns something useful, even if just unmodified id_or_alias_or_prefix
		best_match = id_or_alias_or_prefix
		room = self.get_room(id_or_alias_or_prefix)
		if room is None: return best_match
		for alias in itertools.chain((room.canonical_alias,), room.aliases):
			if alias is None: continue
			m = self.RE_PREFIX.search(alias)
			if not m:
				# This really should never happen, but.
				if best_match == id_or_alias_or_prefix: best_match = alias
				continue
			prefix = m.group(1)
			if self.get_room(prefix) is not None:
				return prefix # prefix _uniquely_ identifies the room
			return alias
		if len(room.aliases) > 0: return room.aliases[0]
		return best_match


class NoSyncMatrixClient(matrix_client.client.MatrixClient):
	# A subclass of MatrixClient that inhibits syncing until we allow it.

	# This class exists because we want to do some modifications to the
	# object (fixup) before _sync() is called for the first time.

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

	def _make_sdkclient(self, *args, **kwargs):
		if not self.sync_filter:
			return matrix_client.client.MatrixClient(*args, **kwargs)

		client = NoSyncMatrixClient(*args, **kwargs)
		client.sync_filter = self.sync_filter
		client.finish_fixup()
		return client

	def on_global_timeline_event(self, event):
		self.last_event = event
		roomid = event['room_id']
		roomhandle = self.rooms.get_room_handle(roomid)
		roomprefix = "[{0}]".format(roomhandle)
		sender = event['sender']
		print(roomprefix, repr(event))
		self._reset_exc_delay()

	def _reset_exc_delay(self):
		self.exception_delay = self.exception_delay_init

	def _exc_delay(self):
		ret = self.exception_delay
		self.exception_delay *= 2
		return ret

	def on_exception(self, e):
		print("Exception caught. Hanging in there.")
		print("Last event received:")
		print(repr(self.last_event))
		print("Stack trace:")
		sys.excepthook(type(e), e, e.__traceback__)
		delay = self._exc_delay()
		print("Waiting {0} seconds before trying again.".format(delay))
		time.sleep(delay)
		print("Let's go!")

	def hook(self):
		# Connect all the listeners, start threads etc.
		self.last_event = None
		m = getattr(self, 'on_global_timeline_event', None)
		if callable(m): self.sdkclient.add_listener(m)
		m = getattr(self, 'on_exception', None)
		if callable(m): self.sdkclient.start_listener_thread(exception_handler=m)
		else: self.sdkclient.start_listener_thread()

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

	def repl(self):
		# Read Eval Print Loop

		# A simple console client loop that can be used as a basis for a client
		# or as a bot manhole.

		self.rooms = RoomList(self.sdkclient.get_rooms())
		self.foreground_room = None
		self.exception_delay_init = 30
		self.exception_delay = self.exception_delay_init

		while True:
			txt = input()
			if txt.startswith('/'):
				if txt.startswith('//'):
					txt = txt[1:]
				else:
					cmd = txt.split(None, 1)[0].lstrip('/')
					m = getattr(self, 'repl_' + cmd, None)
					if callable(m):
						if not m(txt): break
					else:
						print("Unrecognized command:", cmd)
					continue

			if not self.foreground_room:
				print("Cannot send message: You have not selected any room. Try /help.")
				continue

			send_as_notice = getattr(self, 'is_bot', False)
			if txt.startswith(' '):
				txt = txt[1:]
				send_as_notice = not send_as_notice

			if send_as_notice:
				self.foreground_room.send_notice(txt)
			else:
				self.foreground_room.send_text(txt)

	def login(self):
		self._ensure_account()
		t = self.account.login_type()
		if t == self.account.T_PASSWORD:
			self.sdkclient = self._make_sdkclient(self.account.hs_client_api_url)
			token = self.sdkclient.login_with_password(self.account.mxid, self.account.password)
			self.account.access_token = token
			self.account.mxid = self.sdkclient.user_id
			self.account.savetofile(self.accountfilename)
		if t == self.account.T_TOKEN:
			self.sdkclient = self._make_sdkclient(
				self.account.hs_client_api_url,
				token=self.account.access_token,
				user_id=self.account.mxid)
		else:
			raise CFException("MXClient.login(): Cannot login: 'account' is (partially) uninitialized")

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

