import os
from snapshot import Snapshot


class SnapshotTask:
    def __init__(self, snapshot: Snapshot):
        self.snapshot = snapshot

    async def execute(self):
        pass


class RemoveSummaryTask:
    def __init__(self, snapshot: Snapshot):
        self.snapshot = snapshot

    async def execute(self):
        if self.snapshot.address_book.perform_actions_summary.exists():
            os.remove(self.snapshot.address_book.perform_actions_summary)

