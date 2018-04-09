# stdlib

# external deps
import matrix_client

# in-tree deps
import matrix_client_core as client_framework


class TestClient(client_framework.MXClient):
	def connect(self):
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

		self.is_bot = False
		self.message_store = {}
		self.login()
		self.first_sync()
		self.hook()

	def run_forever(self):
		print("Ready.")
		self.repl()

if __name__ == '__main__':
	try: import site_config
	except ImportError: pass

	import logging
	logging.basicConfig(level=logging.CRITICAL)
	tc = TestClient('testclient-account.json')
	tc.connect()
	tc.run_forever()
