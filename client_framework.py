# stdlib
import json
import getpass

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

	def hook(self):
		# Connect all the listeners, start threads etc.
		pass

	def repl_quit(self, txt):
		""" Leave """
		return False

	def repl_help(self, txt):
		""" Show this help text """
		for mname in dir(self):
			if not mname.startswith('repl_'): continue
			cmd = mname[5:]
			m = getattr(self, mname)
			print("/{0}:".format(cmd), getattr(m, '__doc__', ""))

		return True

	def repl(self):
		# Read Eval Print Loop

		# A simple console client loop that can be used as a basis for a client
		# or as a bot manhole.

		self.foreground_room = None

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

