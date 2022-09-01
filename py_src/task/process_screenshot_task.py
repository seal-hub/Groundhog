import logging
from pathlib import Path

from adb_utils import run_bash
from consts import UIED_PATH
from results_utils import AddressBook
from task.snapshot_task import SnapshotTask

logger = logging.getLogger(__name__)


class ProcessScreenshotTask(SnapshotTask):

    async def execute(self):
        logger.info(self.snapshot.address_book.snapshot_result_path.resolve())
        self.snapshot.address_book.initiate_process_screenshot_task()
        uied_run_path = Path(UIED_PATH).joinpath("run_single.sh")
        screenshot_path = self.snapshot.initial_screenshot
        output_path = self.snapshot.address_book.audit_path_map[AddressBook.PROCESS_SCREENSHOT]
        _,stdout, stderr = await run_bash(f"{uied_run_path.resolve()} {screenshot_path} {output_path}")
        logger.info(stdout)
        if stderr:
            logger.error(stderr)
