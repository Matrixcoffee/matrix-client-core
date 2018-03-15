# stdlib

# external deps
import matrix_client

# in-tree deps
import client_framework

class UnRedactBot(client_framework.MXClient):
	def run(self):
		self.sync_filter = '''{
			"presence": { "types": [ "" ] },
			"room": {
				"ephemeral": { "types": [ "" ] },
				"state": {
					"types": [
						"m.room.canonical_alias",
						"m.room.aliases",
						"m.room.name",
						"m.room.topic"
					]
				},
				"timeline": {
					"types": [ "*" ],
					"limit": 3
				}
			}
		}'''

		self.is_bot = True
		self.login()
		rooms = self.sdkclient.get_rooms()
		print("Rooms:", repr(rooms))
		self.hook()
		self.repl()

if __name__ == '__main__':
	bot = UnRedactBot('account.json')
	bot.run()
