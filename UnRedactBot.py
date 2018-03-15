# stdlib

# external deps
import matrix_client

# in-tree deps
import client_framework

class UnRedactBot(client_framework.MXClient):
	def on_room_message(self, event):
		self.message_store[event['event_id']] = event
		print("Message with ID {0} stored.".format(event['event_id']))

	def on_redact(self, event):
		roomid = event['room_id']
		redact_id = event['redacts']
		redacted_event = self.message_store.get(redact_id, None)
		if redacted_event:
			self.sdkclient.api.send_notice(roomid, "{0} redacted {1}'s event with ID {2}. Content follows:".format(
				event['sender'],
				redacted_event['sender'],
				redact_id))
			self.sdkclient.api.send_message_event(roomid, redacted_event['type'], redacted_event['content'])
		else:
			self.sdkclient.api.send_notice(roomid, "{0} redacted an event with ID {1}, which is not available.".format(
				event['sender'],
				redact_id))

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
		self.message_store = {}

		self.login()

		self.sdkclient.add_listener(self.on_room_message, 'm.room.message')
		self.sdkclient.add_listener(self.on_redact, 'm.room.redaction')

		self.hook()
		print("Ready.")
		self.repl()

if __name__ == '__main__':
	import logging
	logging.basicConfig(level=logging.CRITICAL)
	bot = UnRedactBot('account.json')
	bot.run()
