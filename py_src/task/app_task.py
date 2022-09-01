import asyncio
import logging
from pathlib import Path
from typing import Union

from ppadb.device_async import DeviceAsync

from adb_utils import save_snapshot
from results_utils import AddressBook
from snapshot import DeviceSnapshot, Snapshot

logger = logging.getLogger(__name__)


class AppTask:
    def __init__(self, app_path: Union[Path, str], device: DeviceAsync):
        if isinstance(app_path, str):
            app_path = Path(app_path)
        if not app_path.exists() or not app_path.is_dir():
            raise Exception("The app path doesn't exists")
        self.app_path = app_path
        self.device = device

    def app_name(self):
        return self.app_path.name.split('(')[0]

    async def execute(self):
        pass


class TakeSnapshotTask(AppTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self):
        last_index = 0
        for subdir in self.app_path.iterdir():
            if subdir.is_dir() and subdir.name.startswith("S_"):
                s_index = subdir.name[len("S_"):]
                if s_index.isdigit():
                    last_index = max(last_index, int(s_index))
        snapshot_name = f"S_{last_index+1}"
        address_book = AddressBook(self.app_path.joinpath(snapshot_name))
        snapshot = DeviceSnapshot(address_book=address_book, device=self.device)
        await snapshot.setup(first_setup=True)


class StoatSaveSnapshotTask(AppTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self):
        last_index = 0
        existing_snapshots = []
        for subdir in self.app_path.iterdir():
            if subdir.is_dir() and subdir.name.startswith(f"{self.app_name()}.S_"):
                s_index = subdir.name[len(f"{self.app_name()}.S_"):]
                if s_index.isdigit():
                    last_index = max(last_index, int(s_index))
                    existing_snapshot = Snapshot(AddressBook(subdir))
                    await existing_snapshot.setup()
                    existing_snapshots.append(existing_snapshot)

        tmp_snapshot = Snapshot(address_book=AddressBook(self.app_path.joinpath("tmp")))
        await tmp_snapshot.setup()
        # Check if the app is in crashed state
        if 'package="android"' in tmp_snapshot.initial_layout and \
                ("keeps stopping" in tmp_snapshot.initial_layout or "isn't responding" in tmp_snapshot.initial_layout):
            logger.info("The app is crashed, no snapshot will be taken!")
            return

        should_be_saved = True
        for existing_snapshot in existing_snapshots:
            if tmp_snapshot.is_in_same_state_as(existing_snapshot):
                logger.info(f"There is an existing snapshot in the same state: {existing_snapshot.address_book.snapshot_name()}")
                should_be_saved = False
                break
        if should_be_saved:
            snapshot_name = f"{self.app_name()}.S_{last_index+1}"
            address_book = AddressBook(self.app_path.joinpath(snapshot_name))
            snapshot = tmp_snapshot.clone(address_book)
            await asyncio.sleep(5)
            await save_snapshot(snapshot_name)
            logger.info(f"The new snapshot is saved in {snapshot_name}!")
        await asyncio.sleep(1)
