import json
import logging
from abc import ABC, abstractmethod

from a11y_service import A11yServiceManager
from adb_utils import read_local_android_file
from command import Command, CommandResponse, LocatableCommand, LocatableCommandResponse, NavigateCommand, \
    NavigateCommandResponse, InfoCommand, InfoCommandResponse, create_command_response_from_dict
from consts import ACTION_EXECUTION_RETRY_COUNT, REGULAR_EXECUTE_TIMEOUT_TIME
from latte_utils import send_commands_sequence_to_latte, send_command_to_latte

logger = logging.getLogger(__name__)


class Controller(ABC):
    CONTROLLER_RESULT_FILE_NAME = "controller_result.txt"

    def __init__(self):
        pass

    def name(self):
        return type(self).__name__

    @abstractmethod
    async def setup(self):
        pass

    async def execute(self, command: Command, first_setup: bool = False) -> CommandResponse:
        if first_setup:
            await self.setup()
        result = {}
        for i in range(ACTION_EXECUTION_RETRY_COUNT):
            if i > 0:
                await self.setup()
            logger.debug(f"Execute Command using controller {self.name()}, Try: {i}")
            await send_command_to_latte(command="controller_execute", extra=command.toJSONStr())
            result = await read_local_android_file(Controller.CONTROLLER_RESULT_FILE_NAME, wait_time=REGULAR_EXECUTE_TIMEOUT_TIME)
            if result is None:
                logger.warning(f"Timeout, skipping {command} for controller {self.name()}")
                result = {'state': 'timeout'}
                await send_command_to_latte("controller_interrupt")
            else:
                result = json.loads(result)
                break
        if result is None:
            result = {'state': 'maxed_retry'}
        response = create_command_response_from_dict(command, result)
        return response


class TouchController(Controller):
    async def setup(self):
        await A11yServiceManager.setup_latte_a11y_services(tb=False)
        await send_commands_sequence_to_latte([("controller_set", "touch")])


class A11yAPIController(Controller):
    async def setup(self):
        await A11yServiceManager.setup_latte_a11y_services(tb=False)
        await send_commands_sequence_to_latte([("controller_set", "a11y_api")])


class TalkBackAPIController(Controller):
    async def setup(self):
        await A11yServiceManager.setup_latte_a11y_services(tb=True)
        await send_commands_sequence_to_latte([("controller_set", "tb_api")])


class TalkBackTouchController(Controller):
    async def setup(self):
        await A11yServiceManager.setup_latte_a11y_services(tb=True)
        await send_commands_sequence_to_latte([("controller_set", "tb_touch")])
