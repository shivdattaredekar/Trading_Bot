import time
import random
from collections import deque

class RateLimiter:
    def __init__(self, max_per_sec=10, max_per_min=200, backoff=True):
        self.max_per_sec = max_per_sec
        self.max_per_min = max_per_min
        self.sec_calls = deque()
        self.min_calls = deque()
        self.backoff = backoff

    def _cleanup(self, now):
        while self.sec_calls and now - self.sec_calls[0] > 1:
            self.sec_calls.popleft()
        while self.min_calls and now - self.min_calls[0] > 60:
            self.min_calls.popleft()

    def _should_wait(self):
        return len(self.sec_calls) >= self.max_per_sec or len(self.min_calls) >= self.max_per_min

    def wait(self):
        while True:
            now = time.time()
            self._cleanup(now)

            if not self._should_wait():
                break

            print("⚠️ Rate limit hit. Waiting…")

            if self.backoff:
                # Optional jitter/backoff for more natural pacing
                time.sleep(random.uniform(0.2, 0.4))
            else:
                time.sleep(0.2)

        current_time = time.time()
        self.sec_calls.append(current_time)
        self.min_calls.append(current_time)
