from results_utils import AddressBook
from snapshot import DeviceSnapshot
from task.app_task import AppTask


class RecordUsecaseTask(AppTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.usecase_path = self.app_path.joinpath("usecase.jsonl")

    async def execute(self):
        """
            The use case should be written in `usecase_path` where each line is the JSON representation of a
            `Command`. The initial state of the usecase should be stored in a `Snapshot` called "init"
        """
        # ---------- Setting up the initial snapshot ----------------
        init_snapshot = DeviceSnapshot(address_book=AddressBook(self.app_path.joinpath("init")),
                                       device=self.device)
        await init_snapshot.setup(first_setup=True)
        # ---------- Recording the usecase ----------------
        # TODO: Start Sugilite
        # ----- Wait for user to stops
        # TODO: Receive Sugilite's results
