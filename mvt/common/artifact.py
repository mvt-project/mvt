class Artifact:
    def __init__(self, *args, **kwargs):
        self.results = []
        self.detected = []
        super().__init__(*args, **kwargs)
