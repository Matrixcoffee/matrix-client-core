# stdlib
import threading
import time
from random import SystemRandom
random = SystemRandom()

# in-tree deps
import matrix_client_core.notifier as notifier

class RateLimit:
	def __init__(self, consume_factor=0.9, max_probability=2.0):
		self.consume_factor = consume_factor
		self.max_probability = max_probability
		self.probability = self.max_probability

	def ok(self):
		#return random.random() <= self.probability
		r = random.random()
		ok = r <= self.probability
		notifier.notify("{}.{}".format(__package__, __name__),
			'mcc.ratelimit.ok', (ok, r, self.probability))

		return ok

	def consume(self):
		self.probability *= self.consume_factor
		notifier.notify("{}.{}".format(__package__, __name__),
			'mcc.ratelimit.consume', self.probability)

	def replenish(self):
		self.probability = min(self.probability * 2, self.max_probability)
		notifier.notify("{}.{}".format(__package__, __name__),
			'mcc.ratelimit.replenish', self.probability)

	def _replenish_runner(self, interval):
		while True:
			time.sleep(interval)
			self.replenish()

	def start_replenish_thread(self, interval):
		self.replenish_thread = threading.Thread(target=self._replenish_runner, args=(interval,))
		self.replenish_thread.daemon = True
		self.replenish_thread.start()

