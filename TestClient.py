# stdlib

# external deps
import matrix_client

# in-tree deps
import matrix_client_core as client_framework


class TestClient(client_framework.MXClient):
	def on_room_message(self, event):
		self.message_store[event['event_id']] = event
		print("Message with ID {0} stored.".format(event['event_id']))
		self._send_read_receipt(event)

	def _send_read_receipt(self, event):
		path = "/rooms/{roomId}/receipt/{receiptType}/{eventId}".format(
			roomId = event['room_id'],
			receiptType = 'm.read',
			eventId = event['event_id'])

		return self.sdkclient.api._send("POST", path)

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
