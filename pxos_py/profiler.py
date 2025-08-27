class PerfSession:
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    def frame(self, name):
        return self
    def to_dict(self):
        return {}
    def save_jsonl(self, path):
        pass
