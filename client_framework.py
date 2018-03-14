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


class MXClient:
	def __init__(self, accountfilename=None, account=None):
		self.accountfilename = accountfilename
		self.account = account
		self.sdkclient = None

	def login(self):
		self._ensure_account()
		t = self.account.login_type()
		if t == self.account.T_PASSWORD:
			self.sdkclient = matrix_client.client.MatrixClient(self.account.hs_client_api_url)
			token = self.sdkclient.login_with_password(self.account.mxid, self.account.password)
			self.account.access_token = token
			self.account.mxid = self.sdkclient.user_id
			self.account.savetofile(self.accountfilename)
		if t == self.account.T_TOKEN:
			self.sdkclient = matrix_client.client.MatrixClient(
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

