import time

class ProviderAvaliability():
    def __init__(self, name, client, model):
        self.name = name
        self.client = client
        self.model = model
        self.connection_failures = 0
        self.last_failure = 0
        self.refresh = 90

    def availity_check(self):
        if self.connection_failures < 4:
            return True
        time_passed = time.time() - self.last_failure
        return time_passed > self.refresh

    def connection_failed(self):
        self.connection_failures += 1
        self.last_failure = time.time()

    def no_connection_problem(self):
        self.connection_failures = 0