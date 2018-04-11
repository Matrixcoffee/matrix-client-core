# stdlib
import time

DEBUG=False


class Notifier:
	def __init__(self):
		self.listeners = []

	def add_listener(self, listener):
		if listener in self.listeners: return False
		self.listeners.append(listener)
		return True

	def remove_listener(self, listener):
		if not listener in self.listeners: return False
		self.listeners.remove(listener)
		return True

	def notify(self, service, event, data=None):
		result = None	# None - No listeners
				# False - no listeners handled this
				# True - at least one listener handled this
				# Meaning of 'handled' intentionally left unspecified

		for listener in self.listeners:
			r = listener(service, event, data)
			if not result: result = bool(r)

		return result

GLOBAL_NOTIFIER = Notifier()
add_listener = GLOBAL_NOTIFIER.add_listener
remove_listener = GLOBAL_NOTIFIER.remove_listener
notify = GLOBAL_NOTIFIER.notify


class BaseNotificationListener:
	def __init__(self, autoconnect=True):
		if autoconnect: add_listener(self.handle_notification)

	def handle_notification(self, service, event, data=None):
		hname = "on_" + event.replace(".", "_")
		handler = getattr(self, hname, self.default_handler)
		return handler(service, event, data)

	@staticmethod
	def default_handler(service, event, data):
		if DEBUG: print("NotificationListenerBase.default_handler({!r}, {!r}, {!r})".format(service, event, data))


class NotificationListener(BaseNotificationListener):
	@staticmethod
	def on_mcc_mxc_login_connect(service, event, data):
		print("Connecting to {} as {}".format(*data))

	def on_mcc_mxc_first_sync_sync(self, service, event, data):
		self.sync_start_time = time.time()
		print("Syncing...")

	def on_mcc_mxc_first_sync_sync_done(self, service, event, data):
		sync_time = time.time() - self.sync_start_time
		print("Synced in {} seconds.".format(sync_time))


if __name__ == '__main__':
	print("Hello!")

	def notifier(service, event, data=None):
		print(("Notifier: service = {!r}\n" + \
		       "          event   = {!r}\n" + \
		       "          data    = {!r}").format(service, event, data))

	class SomeClass:
		def class_notifier(self, service, event, data=None):
			print(("Other: service = {!r}\n" + \
			       "       event   = {!r}\n" + \
			       "       data    = {!r}").format(service, event, data))
			return True

	other_notifier = SomeClass().class_notifier

	r = notify(__file__, 'e.test.noshow', "This event should not show.")
	print("None:", repr(r))
	r = add_listener(notifier)
	print("True:", repr(r))
	r = add_listener(notifier)
	print("False:", repr(r))
	r = remove_listener(other_notifier)
	print("False:", repr(r))
	r = add_listener(other_notifier)
	print("True:", repr(r))
	r = add_listener(other_notifier)
	print("False:", repr(r))
	r = notify(__file__, 'e.test.twice', "This event should show twice.")
	print("True:", repr(r))
	r = remove_listener(other_notifier)
	print("True:", repr(r))
	r = notify(__file__, 'e.test.once', "This event should show once (through Notifier only).")
	print("False:", repr(r))
	r = remove_listener(other_notifier)
	print("False:", repr(r))
	r = remove_listener(notifier)
	print("True:", repr(r))
	r = remove_listener(notifier)
	print("False:", repr(r))
	r = notify(__file__, 'e.test.noshow', "This event should not show.")
	print("None:", repr(r))

	print("[]:", repr(GLOBAL_NOTIFIER.listeners))
