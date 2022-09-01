import asyncio
import json
import random
from typing import Union, Tuple, List
import logging
import xmlformatter
from collections import namedtuple

from GUI_utils import Node
from adb_utils import read_local_android_file
from a11y_service import A11yServiceManager
from consts import TB_NAVIGATE_RETRY_COUNT, ACTION_EXECUTION_RETRY_COUNT, TB_SELECT_TIMEOUT, TB_NAVIGATE_TIMEOUT, \
    REGULAR_EXECUTE_TIMEOUT_TIME, REGULAR_EXECUTOR_INTERVAL, TB_EXECUTOR_INTERVAL, LAYOUT_TIMEOUT_TIME, \
    BLIND_MONKEY_TAG, TB_TREELIST_TAG
from latte_utils import send_command_to_latte, send_commands_sequence_to_latte
from utils import convert_bounds
from padb_utils import ParallelADBLogger



logger = logging.getLogger(__name__)

FINAL_ACITON_FILE = "finish_nav_action.txt"
CUSTOM_STEP_RESULT = "custom_step_result.txt"
LAYOUT_FILE_PATH = "a11y_layout.xml"
ATF_ISSUES_FILE_PATH = "aft_a11y_issues.jsonl"
ExecutionResult = namedtuple('ExecutionResult',
                             ['state', 'events', 'time', 'resourceId', 'className', 'contentDescription',
                              'xpath', 'bound'])
formatter = xmlformatter.Formatter(indent="1", indent_char="\t", encoding_output="UTF-8", preserve=["literal"])


def get_unsuccessful_execution_result(state: str = "FAILED", bounds: Tuple = None) -> ExecutionResult:
    if bounds is None:
        bounds = tuple([0]*4)
    return ExecutionResult(state, "", "", "", "", "", "", bounds)


async def latte_capture_layout() -> str:
    layout = None
    is_tb_enabled = await A11yServiceManager.is_enabled('tb')
    for i in range(3):
        logger.debug(f"Capturing layout, Try: {i}")
        await A11yServiceManager.setup_latte_a11y_services(tb=False)
        await send_command_to_latte("capture_layout")
        layout = await read_local_android_file(LAYOUT_FILE_PATH, wait_time=LAYOUT_TIMEOUT_TIME)
        if layout:
            break

    if layout is None:
        logger.error(f"Timeout for capturing layout.")
        layout = f"PROBLEM_WITH_XML {random.random()}"

    try:
        layout = formatter.format_string(layout).decode("utf-8")
    except Exception as e:
        logger.error(f"Exception during capturing layout in Latte: {e}")
        layout = f"PROBLEM_WITH_XML {random.random()}"

    if is_tb_enabled:
        await A11yServiceManager.setup_latte_a11y_services(tb=True)
    return layout


async def report_atf_issues() -> List:
    report_jsonl = None
    for i in range(3):
        logger.debug(f"Reporting ATF issues, Try: {i}")
        await A11yServiceManager.enable('latte')
        await send_command_to_latte("report_a11y_issues")
        report_jsonl = await read_local_android_file(ATF_ISSUES_FILE_PATH, wait_time=LAYOUT_TIMEOUT_TIME)
        if report_jsonl:
            break
    if report_jsonl is None:
        logger.error(f"Timeout for reporting ATF issues.")
        return []
    issues = []
    for line in report_jsonl.split("\n"):
        if line:
            issues.append(json.loads(line))

    return issues

async def talkback_tree_nodes(padb_logger: ParallelADBLogger, verbose: bool = False) -> (dict, str):
    """
    First enables TalkBack and Latte, then send "tb_a11y_tree" command to Latte, and observes the logs
    from both Latte and TalkBack (which should contains the Virtual View Hierarchy). Finally, returns a
    dictionary from window ids to the window's information and elements inside the window
    :param padb_logger:
    :param verbose: Logs the captured logs from TalkBack
    :return: A tuple of WindowInfo and Latte logs. WindowInfo is a map from window id to a map of
    information of window, e.g., title, and its elements. The elements is also a map from element id to
    the element's information such as class name, text, or actions.
    """
    async def send_a11y_tree_command():
        await send_command_to_latte("tb_a11y_tree")
        await asyncio.sleep(2)
    # TODO: At the end of this function, the a11y serviecs should be returned to the initial state
    await A11yServiceManager.setup_latte_a11y_services(tb=True)
    logs, next_command_str = await padb_logger.execute_async_with_log(
        send_a11y_tree_command(),
        tags=[BLIND_MONKEY_TAG, TB_TREELIST_TAG])
    flag = False
    windows_info = {'other': {'info': None, 'elements': {}}}
    for line in logs[TB_TREELIST_TAG].split("\n"):
        if "Node tree traversal order" in line:
            flag = True
            continue
        if not flag:
            continue
        t_line = line[line.index(TB_TREELIST_TAG)+len(TB_TREELIST_TAG):].strip()
        if verbose:
            logger.info(t_line)
        window_tag = "Window: AccessibilityWindowInfo"
        if window_tag in t_line:
            w_line = t_line[t_line.index(window_tag)+len(window_tag):]
            window_attributes = ['title', 'id', 'type', 'bounds', 'focused', 'active']
            w_info = {}
            for attr in window_attributes:
                delimiter = ')' if attr == 'bounds' else ','
                w_info[attr] = w_line[w_line.index(f'{attr}=')+len(f'{attr}='):].split(delimiter)[0]
                if attr == 'bounds':
                    w_info[attr] += ')'
            windows_info[w_info['id']] = {
                'info': w_info,
                'elements': {}
            }
        else:
            # TODO: Replace with regular expression
            e_id = t_line.strip().split(')')[0][1:]
            w_id = t_line.split(')')[1].split('.')[0]
            cls_name = t_line.split('.')[1].split(':')[0]
            bounds = t_line.split(':')[1].split(')')[0] + ')'
            actions = t_line.split(')')[-1][1:].split(':')
            text = '' if ':TEXT{' not in t_line else t_line[t_line.index(':TEXT{')+len(':TEXT{'):].split('}')[0]
            content = '' if ':CONTENT{' not in t_line else t_line[t_line.index(':CONTENT{')+len(':CONTENT{'):].split('}')[0]
            rest = ')'.join(t_line.split(')')[2:-1])
            if text:
                rest = rest.replace(f':TEXT{{{text}}}', '')
            if content:
                rest = rest.replace(f':CONTENT{{{content}}}', '')
            if w_id not in windows_info:
                w_id = 'other'
            windows_info[w_id]['elements'][e_id] = {
                'id': e_id,
                'class_name': cls_name,
                'bounds': bounds,
                'actions': actions,
                'text': text,
                'content': content,
                'rest': rest,
            }

    return windows_info, logs[BLIND_MONKEY_TAG]


async def setup_talkback_executor():
    await A11yServiceManager.setup_latte_a11y_services(tb=True)
    await send_commands_sequence_to_latte([("set_step_executor", "talkback"),
                                           ("set_delay", str(TB_EXECUTOR_INTERVAL)),
                                           ("set_physical_touch", "false"),
                                           "enable"])


async def setup_sighted_talkback_executor(api_focus:bool = False):
    await A11yServiceManager.setup_latte_a11y_services(tb=True)
    await send_commands_sequence_to_latte([("set_step_executor", "sighted_tb"),
                                           ("set_delay", str(TB_EXECUTOR_INTERVAL)),
                                           ("set_physical_touch", "false"),
                                           ("nav_api_focus", "true" if api_focus else "false"),
                                           "enable"])


async def setup_regular_executor(physical_touch=True):
    await A11yServiceManager.setup_latte_a11y_services(tb=False)
    await send_commands_sequence_to_latte([("set_step_executor", "regular"),
                                           ("set_delay", str(REGULAR_EXECUTOR_INTERVAL)),
                                           ("set_physical_touch", "true" if physical_touch else "false"),
                                           "enable"])


async def talkback_nav_command(command) -> bool:
    if not await send_command_to_latte(f"nav_clear_history"):
        return False
    return await send_command_to_latte(f"nav_{command}")


async def do_step(json_cmd):
    await send_command_to_latte("step_clear")
    await send_command_to_latte("step_execute", json_cmd)


async def tb_focused_node() -> Union[str, None]:
    for i in range(TB_NAVIGATE_RETRY_COUNT):
        logger.debug(f"Get Focused Node!, Try: {i}")
        await A11yServiceManager.setup_latte_a11y_services(tb=True)
        await talkback_nav_command("current_focus")
        focused_element_json = await read_local_android_file(FINAL_ACITON_FILE, wait_time=TB_NAVIGATE_TIMEOUT)
        if focused_element_json is None:
            logger.warning("Timeout for finding focused node")
        else:
            return focused_element_json
    logger.error("Timeout for finding focused node")
    return None


async def tb_navigate_next(prev: bool = False) -> Union[str, None]:
    for i in range(TB_NAVIGATE_RETRY_COUNT):
        logger.debug(f"Perform {'Prev' if prev else 'Next'}!, Try: {i}")
        await A11yServiceManager.setup_latte_a11y_services(tb=True)
        if not await talkback_nav_command("prev" if prev else "next"):
            logger.warning("Error in sending Nav command to Latte")
            continue
        next_command_json = await read_local_android_file(FINAL_ACITON_FILE, wait_time=TB_NAVIGATE_TIMEOUT)
        if next_command_json is None or next_command_json == "Error":
            logger.warning("Timeout for performing next using TalkBack")
        else:
            return next_command_json
    logger.error("Timeout for performing next using TalkBack")
    return None


async def tb_perform_select() -> ExecutionResult:
    logger.info("Perform Select!")
    await talkback_nav_command("select")
    result = await read_local_android_file(FINAL_ACITON_FILE, wait_time=TB_SELECT_TIMEOUT)
    if result is None:
        logger.error(f"Timeout, skipping Select for executor TalkBack")
        result = "TIMEOUT"
        await send_command_to_latte("nav_interrupt")
    execution_result = analyze_execution_result(result)
    return execution_result


def analyze_execution_result(result: str, command: str = None) -> ExecutionResult:
    if not result or '$' not in result:
        bounds = None
        error_message = result if result else "FAILED"
        if command:
            command_json = json.loads(command)
            node = Node.createNodeFromDict(command_json)
            bounds = node.bounds
        return get_unsuccessful_execution_result(state=error_message, bounds=bounds)
    parts = result.split('$')
    state = parts[1].split(':')[1].strip()
    events = parts[2].split(':')[1].strip()
    time = parts[3].split(':')[1].strip()
    resourceId = parts[4].split('ID=')[1].split(',')[0].strip() if 'ID=' in parts[4] else 'null'
    className = parts[4].split('CL=')[1].split(',')[0].strip() if 'CL=' in parts[4] else 'null'
    contentDescription = parts[4].split('CD=')[1].split(',')[0].strip() if 'CD=' in parts[4] else 'null'
    xpath = parts[4].split('xpath=')[1].split(',')[0].strip() if 'xpath=' in parts[4] else ''
    bounds = convert_bounds(parts[4].split('bounds=')[1].strip()) if 'bounds=' in parts[4] else tuple([0]*4)
    return ExecutionResult(state, events, time, resourceId, className, contentDescription, xpath, bounds)


async def execute_command(command: str, executor_name: str = "reg", api_focus: bool = False) -> ExecutionResult:
    result = ""
    for i in range(ACTION_EXECUTION_RETRY_COUNT):
        if executor_name == 'reg':
            await setup_regular_executor()
        elif executor_name == 'areg':
            await setup_regular_executor(physical_touch=False)
        elif executor_name == 'tb':
            await setup_talkback_executor()
        elif executor_name == 'stb':
            await setup_sighted_talkback_executor(api_focus=api_focus)
        logger.debug(f"Execute Step Command, Try: {i}")
        await do_step(command)
        result = await read_local_android_file(CUSTOM_STEP_RESULT, wait_time=REGULAR_EXECUTE_TIMEOUT_TIME)
        if result is None:
            logger.warning(f"Timeout, skipping {command} for executor {executor_name}")
            result = "TIMEOUT"
            await send_command_to_latte("step_interrupt")
        else:
            break
    execution_result = analyze_execution_result(result, command)
    return execution_result


async def reg_execute_command(command: str) -> ExecutionResult:
    return await execute_command(command, 'reg')


async def areg_execute_command(command: str) -> ExecutionResult:
    return await execute_command(command, 'areg')


async def tb_execute_command(command: str) -> ExecutionResult:
    return await execute_command(command, 'tb')


async def stb_execute_command(command: str) -> ExecutionResult:
    return await execute_command(command, 'stb')


def get_missing_actions(important_nodes: List[Node], executed_elements: List[dict]) -> List[Node]:
    xpath_to_important_nodes = {}
    xpath_to_done_elements = {}
    for x in important_nodes:
        xpath_to_important_nodes[x.xpath] = x
    for x in executed_elements:
        xpath_to_done_elements[x['xpath']] = x
    all_keys = set(xpath_to_important_nodes.keys()).union(xpath_to_done_elements.keys())
    missing_actions = []
    for k in all_keys:
        if k not in xpath_to_done_elements.keys():
            missing_actions.append(xpath_to_important_nodes[k])
    return missing_actions
