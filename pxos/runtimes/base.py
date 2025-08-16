# Placeholder for base Process class
import os

class Process:
    def __init__(self, *args, **kwargs):
        self.policy = kwargs.get('policy', {})
        self.keystore = kwargs.get('keystore', {})
        self.host = kwargs.get('host', {})
        self.packet = kwargs.get('packet', {})
        self.caps = kwargs.get('caps', {})
        self.pid = os.getpid() # Add pid for rate limit identity

    def start(self):
        pass

    def on_prompt(self, text: str):
        pass

    def terminate(self):
        pass
