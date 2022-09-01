import asyncio
from pathlib import Path
from typing import List
import logging

from results_utils import AddressBook
from search_utils import contains_node_with_attrs
from snapshot import Snapshot

logger = logging.getLogger(__name__)


class SnapshotSearchQuery:
    def __init__(self):
        self.filters = []
        self.valid_app = None

    def satisfies(self, snapshot: Snapshot) -> bool:
        for i_filter in self.filters:
            if not i_filter(snapshot):
                return False
        return True

    def is_valid_app(self, app_name):
        if self.valid_app is None:
            return True
        return app_name == self.valid_app

    def set_valid_app(self, app_name):
        if app_name != 'All':
            self.valid_app = app_name
        return self

    def contains_node(self, attrs: List[str], queries: List[str]):
        def contains_node_satisfies(snapshot: Snapshot) -> bool:
            if snapshot is None or not snapshot.initial_layout or len(snapshot.nodes) == 0:
                return False
            return contains_node_with_attrs(snapshot.nodes, attrs, queries)

        if len(attrs) == len(queries):
            self.filters.append(contains_node_satisfies)
        return self


class SnapshotSearchManager:
    def __init__(self, result_path: Path):
        self.result_path = result_path

    def search(self,
               search_query: SnapshotSearchQuery,
               snapshot_limit: int = 10000,
               ) -> List[Snapshot]:
        results = []
        for app_path in self.result_path.iterdir():
            if len(results) >= snapshot_limit:
                break
            if not app_path.is_dir():
                continue
            if not search_query.is_valid_app(app_path.name):
                continue
            for snapshot_path in app_path.iterdir():
                if len(results) >= snapshot_limit:
                    break
                if not snapshot_path.is_dir():
                    continue
                address_book = AddressBook(snapshot_path)
                try:
                    snapshot = Snapshot(address_book)
                    asyncio.run(snapshot.setup())
                    if search_query.satisfies(snapshot):
                        results.append(snapshot)
                except Exception as e:
                    logger.error(f"Error in SnapshotSearch for snapshot {address_book.snapshot_result_path}: {e}")
        return results
