# stdlib

# external deps
import matrix_client

# in-tree deps
import client_framework

class UnRedactBot(client_framework.MXClient):
	def run(self):
		self.login()
		rooms = self.sdkclient.get_rooms()
		print("Rooms:", repr(rooms))

if __name__ == '__main__':
	bot = UnRedactBot('account.json')
	bot.run()
