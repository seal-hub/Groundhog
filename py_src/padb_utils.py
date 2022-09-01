from typing import Any, List, Union
import asyncio
import aiofiles
from consts import BLIND_MONKEY_TAG, CAPTURE_SCREENSHOT_DELAY


async def save_screenshot(device, file_name) -> None:
    result = await device.screencap()
    await asyncio.sleep(CAPTURE_SCREENSHOT_DELAY)
    async with aiofiles.open(file_name, mode='wb') as f:
        await f.write(result)
    return file_name


class ParallelADBLogger:
    def __init__(self, device):
        self.device = device
        self.lock = None
        self.log_message = ""

    async def _logcat(self) -> asyncio.coroutine:
        async def logcat_handler(connection):
            global log_list
            while True:
                data = await connection.read(1024)
                if not data:
                    break
                self.log_message += data.decode('utf-8')
            await connection.close()
        conn = await self.device.create_connection(timeout=None)
        cmd = "shell:{}".format("logcat -c; logcat")
        await conn.send(cmd)
        logcat_handler_task = asyncio.create_task(logcat_handler(conn))
        return logcat_handler_task

    async def execute_async_with_log(self,
                                     coroutine_obj: asyncio.coroutine,
                                     tags: List[str] = None) -> (dict, Any):
        if self.lock is not None:
            raise Exception("Cannot execute more than one coroutine while logging!")
        self.lock = coroutine_obj
        self.log_message = ""
        ll_task = await self._logcat()
        coroutine_result = await coroutine_obj
        await asyncio.sleep(0.5)
        ll_task.cancel()
        self.lock = None
        if tags is None:
            tags = [BLIND_MONKEY_TAG]
        logs = {}
        for tag in tags:
            logs[tag] = "\n".join(line for line in self.log_message.split("\n") if tag in line)
        self.log_message = logs
        return self.log_message, coroutine_result
