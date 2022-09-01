import logging
import asyncio
import xmlformatter
import random
from typing import Optional
from consts import DEVICE_NAME


logger = logging.getLogger(__name__)

formatter = xmlformatter.Formatter(indent="1", indent_char="\t", encoding_output="UTF-8", preserve=["literal"])
LATTE_PKG_NAME = "dev.navids.latte"


async def run_bash(cmd) -> (int, str, str):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    return proc.returncode, stdout.decode() if stdout else "", stderr.decode() if stderr else ""


async def start_adb() -> None:
    _ = await run_bash("adb start-server")


async def kill_adb() -> None:
    _ = await run_bash("adb kill-server")


async def capture_layout(device_name: str = DEVICE_NAME) -> str:
    cmd = f"adb -s {device_name} exec-out uiautomator dump /dev/tty"
    layout = f"PROBLEM_WITH_XML EMPTY {random.random()}"
    for i in range(3):
        result, stdout, stderr = await run_bash(cmd)
        layout = stdout.replace("UI hierchary dumped to: /dev/tty", "")
        try:
            layout = formatter.format_string(layout).decode("utf-8")
            break
        except Exception as e:
            logger.error(f"Exception during capturing layout: {e}")
            layout = f"PROBLEM_WITH_XML {random.random()}"
        logger.debug(f"Try capture layout with ADB: {i+1}")
        await asyncio.sleep(1)
    return layout


async def load_snapshot(snapshot_name, device_name: str = DEVICE_NAME) -> bool:
    logger.debug(f"Loading snapshot {snapshot_name}..")
    cmd = f"adb -s {device_name} emu avd snapshot load {snapshot_name}"
    r_code, stdout, stderr = await run_bash(cmd)
    if "OK" not in stdout:
        return False
    r_code, *_ = await run_bash(f"adb -s {device_name} wait-for-device")
    return r_code == 0


async def save_snapshot(snapshot_name, device_name: str = DEVICE_NAME) -> None:
    cmd = f"adb -s {device_name} emu avd snapshot save {snapshot_name}"
    await run_bash(cmd)


async def get_current_activity_name(device_name: str = DEVICE_NAME) -> str:
    cmd = f"adb -s {device_name} shell dumpsys window windows  | grep 'mObscuringWindow'"
    r_code, stdout, stderr = await run_bash(cmd)
    return stdout


async def get_windows(device_name: str = DEVICE_NAME) -> str:
    cmd = f"adb -s {device_name} shell dumpsys window windows"
    r_code, stdout, stderr = await run_bash(cmd)
    return stdout


async def get_activities(device_name: str = DEVICE_NAME) -> str:
    cmd = f"adb -s {device_name} shell dumpsys activity activities"
    r_code, stdout, stderr = await run_bash(cmd)
    return stdout


async def is_android_activity_on_top(device_name: str = DEVICE_NAME) -> bool:
    activity_name = await get_current_activity_name(device_name)
    android_names = ["com.android.systemui", "com.google.android"]
    for android_name in android_names:
        if android_name in activity_name:
            return True
    return False


async def local_android_file_exists(file_path: str, pkg_name: str = LATTE_PKG_NAME, device_name: str = DEVICE_NAME) -> bool:
    cmd = f"adb -s {device_name} exec-out run-as {pkg_name} ls files/{file_path}"
    _, stdout, _ = await run_bash(cmd)
    return "No such file or directory" not in stdout


async def remove_local_android_file(file_path: str, pkg_name: str = LATTE_PKG_NAME, device_name: str = DEVICE_NAME):
    rm_cmd = f"adb -s {device_name} exec-out run-as {pkg_name} rm files/{file_path}"
    await run_bash(rm_cmd)


async def read_local_android_file(file_path: str,
                                  pkg_name: str = LATTE_PKG_NAME,
                                  wait_time: int = -1,
                                  remove_after_read: bool = True,
                                  device_name: str = DEVICE_NAME) -> Optional[str]:
    sleep_time = 0.5
    index = 0
    while not await local_android_file_exists(file_path, pkg_name, device_name=device_name):
        if 0 < wait_time < index * sleep_time:
            return None
        index += 1
        if index % 4 == 0:
            logger.debug(f"Waiting {int(index * sleep_time)} seconds for {file_path}")
        await asyncio.sleep(sleep_time)
    cmd = f"adb -s {device_name} exec-out run-as {pkg_name} cat files/{file_path}"
    _, content, _ = await run_bash(cmd)
    if remove_after_read:
        await remove_local_android_file(file_path, pkg_name, device_name=device_name)
    return content
