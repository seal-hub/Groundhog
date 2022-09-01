import asyncio
import json
import logging

from command import create_command_from_dict
from consts import BLIND_MONKEY_TAG
from controller import TouchController, TalkBackAPIController
from padb_utils import ParallelADBLogger
from results_utils import capture_current_state, AddressBook
from snapshot import DeviceSnapshot
from task.app_task import AppTask

logger = logging.getLogger(__name__)


class ExecuteUsecaseTask(AppTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.usecase_path = self.app_path.joinpath("usecase.jsonl")

    async def execute(self):
        if not self.usecase_path.exists():
            logger.error(f"The usecase of app {self.app_name()} doesn't exist!")
            return
        commands = []
        with open(self.usecase_path) as f:
            for line in f.readlines():
                json_command = json.loads(line)
                command = create_command_from_dict(json_command)
                commands.append(command)
        padb_logger = ParallelADBLogger(self.device)
        controller = TalkBackAPIController()
        for index, command in enumerate(commands):
            logger.info(f"Command {index}: {command}")
            address_book = AddressBook(self.app_path.joinpath(f"command_{index}"))
            snapshot = DeviceSnapshot(address_book=address_book, device=self.device)
            await snapshot.setup(first_setup=True)
            log_message_map, response = await padb_logger.execute_async_with_log(
                controller.execute(command, first_setup=True),
                tags=[BLIND_MONKEY_TAG])
            await asyncio.sleep(2)
