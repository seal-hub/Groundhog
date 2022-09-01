import json
import logging
import random
import string
from typing import Union, Tuple, List

from adb_utils import run_bash, read_local_android_file
from consts import IS_LIVE_TIMEOUT_TIME, DEVICE_NAME

logger = logging.getLogger(__name__)

LATTE_INTENT = "dev.navids.latte.COMMAND"
IS_LIVE_FILE_PATTERN = "is_live_{0}.txt"


def _encode_latte_message(message: str) -> str:
    message = message \
        .replace('"', "__^__") \
        .replace(" ", "__^^__") \
        .replace(",", "__^^^__") \
        .replace("'", "__^_^__") \
        .replace("+", "__^-^__") \
        .replace("|", "__^^^^__") \
        .replace("$", "__^_^^__") \
        .replace("*", "__^-^^__") \
        .replace("&", "__^^_^__") \
        .replace("[", "__^^-^__") \
        .replace("]", "__^^^^^__")
    message = message.replace(")", "").replace("(", "")  # TODO: Must be changed
    return message


async def send_command_to_latte(command: str, extra: str = "NONE", device_name: str = DEVICE_NAME) -> bool:
    logger.debug(f"Sending command {command} with extra {extra} to Latte!")
    extra = _encode_latte_message(extra)
    bash_cmd = f'adb -s {device_name} shell am broadcast -a {LATTE_INTENT} --es command "{command}" --es extra "{extra}"'
    r_code, *_ = await run_bash(bash_cmd)
    if r_code != 0:
        logger.error(f"Error in sending command {command} with extra {extra}!")
    return r_code == 0


async def send_commands_sequence_to_latte(command_sequence: List[Union[str, Tuple[str, str]]], device_name: str = DEVICE_NAME) -> bool:
    command_extra = []
    for item in command_sequence:
        command = item if isinstance(item, str) else item[0]
        extra = item[1] if isinstance(item, tuple) and len(item) > 1 else "NONE"
        command_extra.append({"command": command, "extra": extra})
    return await send_command_to_latte('sequence', json.dumps(command_extra), device_name=device_name)


async def is_latte_live(device_name: str = DEVICE_NAME) -> bool:
    random_message = ''.join(random.choice(string.ascii_lowercase) for i in range(20))
    if not await send_command_to_latte('is_live', random_message, device_name=device_name):
        return False
    file_path = IS_LIVE_FILE_PATTERN.format(random_message)
    result = await read_local_android_file(file_path, wait_time=IS_LIVE_TIMEOUT_TIME, device_name=device_name)
    return result is not None
