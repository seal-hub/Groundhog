import logging
import asyncio
from typing import List, Union
from adb_utils import run_bash
# TODO: Need to decompose latte_utils into latte_comms and latte_navigations
from latte_utils import is_latte_live
from consts import DEVICE_NAME

logger = logging.getLogger(__name__)


class A11yServiceManager:
    services = {"tb": "com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService",
                         "latte": "dev.navids.latte/dev.navids.latte.app.MyLatteService"}

    @staticmethod
    async def get_enabled_services(simplify: bool = False, device_name: str = DEVICE_NAME) -> List[str]:
        _, enabled_services, _ = \
            await run_bash(f"adb -s {device_name} shell settings get secure enabled_accessibility_services")
        if 'null' in enabled_services:
            return []
        result = []
        for service in enabled_services.strip().split(':'):
            service_name = service
            if simplify:
                for key, value in A11yServiceManager.services.items():
                    if value == service_name:
                        service_name = key
                        break
            result.append(service_name)
        return result

    @staticmethod
    async def is_enabled(service_name: str, device_name: str = DEVICE_NAME) -> bool:
        if service_name not in A11yServiceManager.services:
            return False
        enabled_services = await A11yServiceManager.get_enabled_services(device_name=device_name)
        return A11yServiceManager.services[service_name] in enabled_services

    @staticmethod
    async def enable(service_names: Union[str, List[str]], device_name: str = DEVICE_NAME) -> int:
        if isinstance(service_names, str):
            service_names = [service_names]
        enabled_services = await A11yServiceManager.get_enabled_services(device_name=device_name)
        requested_services = []
        for service_name in service_names:
            if service_name not in A11yServiceManager.services:
                continue
            actual_service_name = A11yServiceManager.services[service_name]
            if actual_service_name in enabled_services:
                continue
            requested_services.append(actual_service_name)
        if len(requested_services) == 0:
            return 0

        enabled_services_str = ":".join(enabled_services + requested_services)
        r_code, *_ = await run_bash(
            f"adb -s {device_name} shell settings put secure enabled_accessibility_services {enabled_services_str}")
        return len(requested_services) if r_code == 0 else -1

    @staticmethod
    async def disable(service_name: str, device_name: str = DEVICE_NAME) -> bool:
        if service_name not in A11yServiceManager.services:
            return False
        enabled_services = await A11yServiceManager.get_enabled_services(device_name=device_name)
        if A11yServiceManager.services[service_name] not in enabled_services:
            return True
        enabled_services.remove(A11yServiceManager.services[service_name])
        enabled_services_str = ":".join(enabled_services)
        if len(enabled_services_str) == 0:
            r_code, *_ = await run_bash(
                f"adb -s {device_name} shell settings delete secure enabled_accessibility_services")
        else:
            r_code, *_ = await run_bash(
                f"adb -s {device_name} shell settings put secure enabled_accessibility_services {enabled_services_str}")
        return r_code == 0

    @staticmethod
    async def setup_latte_a11y_services(tb=False, device_name: str = DEVICE_NAME) -> None:
        requested_services = ["latte"]
        if tb:
            requested_services.append("tb")
        elif await A11yServiceManager.is_enabled("tb", device_name=device_name):
            logger.debug("Disabling TalkBack...")
            await A11yServiceManager.disable("tb", device_name=device_name)
            await asyncio.sleep(1)
        for i in range(3):
            enabled_count = await A11yServiceManager.enable(requested_services, device_name=device_name)
            if enabled_count > 0:
                logger.debug(f"{enabled_count} services are enabled from {requested_services}")
                await asyncio.sleep(1)
                break
            elif enabled_count == 0:
                break
            else:
                logger.warning(f"There was an issue with enabling services {requested_services}, Try: {i}")
        live_latte = False
        for i in range(10):
            if await is_latte_live():
                live_latte = True
                break
            else:
                logger.info(f"Waiting for Latte to be alive...")
        if not live_latte:
            # TODO: too harsh, it's better to return live_latte and let the outer method decides
            raise "Latte is not alive"
