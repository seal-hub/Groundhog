import re
import subprocess
import os
from collections import defaultdict, namedtuple
from typing import Union
from pathlib import Path
import json
import argparse
import logging
from results_utils import AddressBook, get_snapshot_paths
from latte_executor_utils import ExecutionResult

logger = logging.getLogger(__name__)

POST_ANALYSIS_PREFIX = 'post_analysis_result'

LAST_VERSION = "V3"
# V3
##  > 20 Accessible
##  <=20, > 10 Couldn't determine issue
##  <=10, >0 Accessibility Warning
## <=0, Accessiblity Failure
ACCESSIBLE = 30
OTHER = 20
EXTERNAL_SERVICE = 19
LOADING = 18
TB_WEBVIEW_LOADING = 17
INEFFECTIVE = 15
CRASHED = 13
API_SMELL = 2
A11Y_WARNING = 1
API_A11Y_ISSUE = 0
TB_A11Y_ISSUE = -1
# V2
SUCCESS = 30
EXEC_FAILURE = 20
EXEC_TIMEOUT = 10
TB_TIMEOUT = 9
TB_FAILURE = 8
REG_TIMEOUT = 7
REG_FAILURE = 6
AREG_TIMEOUT = 5
AREG_FAILURE = 4
XML_PROBLEM = 3
UNREACHABLE = 2
DIFFERENT_AREG = 1
DIFFERENT_BEHAVIOR = 0


class PostAnalysisResult:
    def __init__(self, action, issue_status: int, message: str, is_sighted: bool, xml_similar_map: dict = None):
        self.action = action
        self.index = action['index']
        self.issue_status = issue_status
        self.message = message
        self.is_sighted = is_sighted
        self.xml_similar_map = xml_similar_map

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__)


def old_report_issues(address_book: AddressBook):
    different_behaviors = []
    directional_unreachable = []
    unlocatable = []
    different_behaviors_directional_unreachable = []
    tb_xpaths = {}
    pending = False
    if address_book.snapshot_result_path.joinpath("explore.json").exists():
        with open(address_book.snapshot_result_path.joinpath("explore.json")) as f:
            explore_result = json.load(f)
            for index in explore_result:
                tb_xpaths[explore_result[index]['command']['xpath']] = explore_result[index]['command']
                if not explore_result[index]['same']:
                    different_behaviors.append(explore_result[index]['command'])
    else:
        pending = True

    if address_book.snapshot_result_path.joinpath("stb_result.json").exists():
        with open(address_book.snapshot_result_path.joinpath("stb_result.json")) as f:
            stb_results = json.load(f)
            for key in stb_results:
                e = ExecutionResult(*stb_results[key]['stb_result'])
                if e.state == 'COMPLETED_BY_HELP':
                    unlocatable.append(stb_results[key]['command'])
                elif e.state == 'FAILED' or not stb_results[key]['same']:
                    different_behaviors_directional_unreachable.append(stb_results[key]['command'])
                else:
                    if e.xpath not in tb_xpaths.keys():
                        directional_unreachable.append(stb_results[key]['command'])
    else:
        pending = True
    return different_behaviors, directional_unreachable, unlocatable, \
           different_behaviors_directional_unreachable, pending


def post_analyzer_v1(action, address_book: AddressBook, is_sighted: bool) -> PostAnalysisResult:
    """
    Given a performed action,
    acts as an oracle and generates the accessibility result of the action
    :param action: The action created during BlindMonkey exploration or sighted clicking
    :param address_book: AddressBook
    :param is_sighted: Determines if the actions is performed during Sighted clicking
    :return: a dictionary of action index to its result with a message
    """
    action_index = action['index']
    prefix = "s_" if is_sighted else ""
    tb_xml_path = address_book.get_layout_path(f'{prefix}tb', action_index)
    reg_xml_path = address_book.get_layout_path(f'{prefix}reg', action_index)
    xml_problem = False
    if not tb_xml_path.exists():
        xml_problem = True
    else:
        with open(tb_xml_path, "r") as f:
            tb_xml = f.read()
            if "PROBLEM_WITH_XML" in tb_xml:
                xml_problem = True
    if not reg_xml_path.exists():
        xml_problem = True
    else:
        with open(reg_xml_path, "r") as f:
            reg_xml = f.read()
            if "PROBLEM_WITH_XML" in reg_xml:
                xml_problem = True
    issue_status = SUCCESS
    message = "Accessible"
    if "FAILED" in action['tb_action_result'][0]:
        message = "TalkBack Failed"
        issue_status = TB_FAILURE
    elif "FAILED" in action['reg_action_result'][0]:
        message = "Regular Failed"
        issue_status = REG_FAILURE
    elif xml_problem:
        message = "Problem with XML"
        issue_status = XML_PROBLEM
    else:
        if is_sighted:
            if tb_xml == reg_xml:
                message = "Unreachable"
                issue_status = UNREACHABLE
            else:
                message = "Different Behavior"
                issue_status = DIFFERENT_BEHAVIOR
        else:
            if tb_xml != reg_xml:
                message = "Different Behavior"
                issue_status = DIFFERENT_BEHAVIOR

    result = PostAnalysisResult(action=action,
                                issue_status=issue_status,
                                message=message,
                                is_sighted=is_sighted)
    return result


def post_analyzer_v2(action, address_book: AddressBook, is_sighted: bool) -> PostAnalysisResult:
    """
    Given a performed action,
    acts as an oracle and generates the accessibility result of the action.
    In this version, the result of A11yNodeInfo Regular (or areg) is also considered
    :param action: The action created during BlindMonkey exploration or sighted clicking
    :param address_book: AddressBook
    :param is_sighted: Determines if the actions is performed during Sighted clicking
    :return: a dictionary of action index to its result with a message
    """
    action_index = action['index']
    prefix = "s_" if is_sighted else ""
    modes = ['exp', 'tb', 'reg', 'areg']
    xml_path_map = {}
    for mode in modes:
        if mode == 'exp' and is_sighted:
            xml_path_map[mode] = address_book.get_layout_path(f'{prefix}{mode}', "INITIAL")
        else:
            xml_path_map[mode] = address_book.get_layout_path(f'{prefix}{mode}', action_index)
    xml_content_map = {}
    xml_problem = False
    for mode in modes:
        if not xml_path_map[mode].exists():
            xml_problem = True
        else:
            with open(xml_path_map[mode], "r") as f:
                xml_content_map[mode] = f.read()

    issue_status = SUCCESS
    message_list = []
    for mode in modes:
        if mode == 'exp':
            continue
        if "FAILED" in action[f'{mode}_action_result'][0] or "COMPLETED_BY_HELP" in action[f'{mode}_action_result'][0]:
            message_list.append(f"{mode} Failed!")
            issue_status = EXEC_FAILURE
        elif "TIMEOUT" in action[f'{mode}_action_result'][0]:
            message_list.append(f"{mode} Timeout!")
            issue_status = EXEC_TIMEOUT
    xml_similar = {}
    for i, mode in enumerate(modes):
        for mode2 in modes[i+1:]:
            xml_similar[f"{mode}_{mode2}"] = (xml_content_map[mode] == xml_content_map[mode2])
            xml_similar[f"{mode2}_{mode}"] = xml_similar[f"{mode}_{mode2}"]
    if issue_status == SUCCESS:
        if xml_problem:
            message_list.append("Problem with XML")
            issue_status = XML_PROBLEM
        else:
            if is_sighted:
                if xml_similar['tb_reg']:
                    message_list.append("Unreachable")
                    issue_status = UNREACHABLE
                else:
                    message_list.append("Different Behavior")
                    issue_status = DIFFERENT_BEHAVIOR
                if not xml_similar['reg_areg']:
                    message_list.append("Different Behavior in Areg")
                    issue_status = DIFFERENT_AREG
            else:
                if not xml_similar['tb_reg']:
                    message_list.append("Different Behavior")
                    issue_status = DIFFERENT_BEHAVIOR
                elif not xml_similar['reg_areg']:
                    message_list.append("Different Behavior in Areg")
                    issue_status = DIFFERENT_AREG

    if issue_status == SUCCESS:
        message_list = ["Accessible"]

    result = PostAnalysisResult(action=action,
                                issue_status=issue_status,
                                message="\n".join(message_list),
                                is_sighted=is_sighted,
                                xml_similar_map=xml_similar)
    return result


def post_analyzer_v3(action, address_book: AddressBook, is_sighted: bool) -> PostAnalysisResult:
    """
    Given a performed action,
    acts as an oracle and generates the accessibility result of the action.
    In this version, the result of A11yNodeInfo Regular (or areg) is also considered
    :param action: The action created during BlindMonkey exploration or sighted clicking
    :param address_book: AddressBook
    :param is_sighted: Determines if the actions is performed during Sighted clicking
    :return: a dictionary of action index to its result with a message
    """
    modes = ['exp', 'tb', 'reg', 'areg']

    def is_ineffective(xml_similar, xml_content_map, action, is_sighted) -> bool:
        if all(xml_similar[f'exp_{mode}'] for mode in modes):
            return True
        if all(xml_similar[f'exp_{mode}'] for mode in ['tb', 'areg']):
            if "FAILED" in action[f'tb_action_result'][0] or \
                "COMPLETED_BY_HELP" in action[f'tb_action_result'][0]:
                return True
            if is_sighted and all(not xml_similar[f'reg_{mode}'] for mode in ['tb', 'areg']):
                return True
        return False

    def is_crashed(xml_similar, xml_content_map, action, is_sighted) -> bool:
        for mode in modes:
            if 'package="android"' in xml_content_map[mode] and \
                    ("keeps stopping" in xml_content_map[mode] or "isn't responding" in xml_content_map[mode]):
                return True
        return False

    def is_api_reachable(xml_similar, xml_content_map, action, is_sighted) -> bool:
        # if is_sighted and
        return False

    def is_tb_web_view_adaptive(xml_similar, xml_content_map, action, is_sighted) -> bool:
        if xml_similar['tb_reg']:
            return False
        prefix = "s_" if is_sighted else ""
        cmd = f"diff {address_book.get_layout_path(f'{prefix}tb',action['index'])} {address_book.get_layout_path(f'{prefix}reg', action['index'])}"
        diff_string = subprocess.run(cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8')
        diffs = []
        last_diff = []
        state = 0
        for line in diff_string.split("\n"):
            if not line:
                continue
            if state == 0:
                if line[0].isdecimal():
                    last_diff.append(line)
                    last_diff.append("")
                    state = 1
                    continue
            elif state == 1:
                if line[0] == '<':
                    last_diff[1] += (line[1:]+"\n")
                elif line[0] == '-':
                    state = 2
                    last_diff.append("")
                elif line[0].isdecimal():
                    last_diff.append("")
                    diffs.append(tuple(last_diff))
                    last_diff = [line, ""]
                    state = 1
                    continue
                elif line[0] == '>':
                    last_diff.append(line[1:]+"\n")
                    state = 2
                else:
                    logger.error("Issue with format")
                    last_diff.append("ERROR")
                    diffs.append(tuple(last_diff))
                    break
            elif state == 2:
                if line[0] == '>':
                    last_diff[2] += line[1:]+"\n"
                elif line[0].isdecimal():
                    diffs.append(tuple(last_diff))
                    last_diff = [line, ""]
                    state = 1
                    continue
                else:
                    logger.error("Issue with format")
                    last_diff[-1] = "ERROR"
                    diffs.append(tuple(last_diff))
                    last_diff = []
                    break
        if len(last_diff) == 2:
            last_diff.append("")
        if len(last_diff) == 3:
            diffs.append(tuple(last_diff))
        else:
            logger.error(diff_string)
        if len(diffs) != 1:
            if len(diffs) == 0:
                logger.error(state)
            return False
        diff = diffs[0]
        if diff[2] == "ERROR" or len(diff[2]) == 0:
            return False
        if 'class="android.webkit.WebView"' in diff[2] and 'NAF="true"' in diff[2]:
            first_line = diff[1].split("\n")[0]
            if 'class="android.webkit.WebView"' in first_line and 'importantForAccessibility="false"' in first_line:
                return True
        return False


    def is_loading(xml_similar, xml_content_map, action, is_sighted) -> bool:
        return any("android.widget.ProgressBar" in xml_content_map[mode] for mode in ['tb', 'reg', 'areg']) and \
            "android.widget.ProgressBar" not  in xml_content_map['exp']

    def login_with(xml_similar, xml_content_map, action, is_sighted) -> bool:
        action_texts = [action['element']['text'].lower(), action['element']['contentDescription'].lower()]
        return any(service in action_text for service in ['microsoft', 'google', 'facebook'] for action_text in action_texts)

    action_index = action['index']
    prefix = "s_" if is_sighted else ""
    xml_path_map = {}
    for mode in modes:
        if mode == 'exp' and is_sighted:
            xml_path_map[mode] = address_book.get_layout_path(f'{prefix}{mode}', "INITIAL")
        else:
            xml_path_map[mode] = address_book.get_layout_path(f'{prefix}{mode}', action_index)
    xml_content_map = {}
    xml_problem = False
    for mode in modes:
        if not xml_path_map[mode].exists():
            xml_problem = True
        else:
            with open(xml_path_map[mode], "r") as f:
                xml_content_map[mode] = ""
                bounds_re_pattern = r'bounds="\[\d+,\d+\]\[\d+,\d+\]"\s'
                drawing_re_pattern = f'drawingOrder="\d+"\s'
                focused_re_pattern = f'focused="[a-z]+"\s'
                index_re_pattern = f'index="\d+"\s'
                a11y_actions_re_pattern = f'z-a11y-actions=".*"'
                for line in f.readlines():
                    line = re.sub(bounds_re_pattern, '', line)
                    line = re.sub(drawing_re_pattern, '', line)
                    line = re.sub(focused_re_pattern, '', line)
                    line = re.sub(index_re_pattern, '', line)
                    line = re.sub(a11y_actions_re_pattern, '', line)
                    xml_content_map[mode] += line +"\n"
                    # xml_content_map[mode] += line + "\n"

    issue_status = ACCESSIBLE
    message_list = []
    for mode in modes:
        if mode == 'exp':
            continue
        if "FAILED" in action[f'{mode}_action_result'][0] or "COMPLETED_BY_HELP" in action[f'{mode}_action_result'][0]:
            message_list.append(f"{mode} Failed!")
            issue_status = min(issue_status, OTHER)
        elif "TIMEOUT" in action[f'{mode}_action_result'][0]:
            message_list.append(f"{mode} Timeout!")
            issue_status = min(issue_status, OTHER)
        if 'package="android"' in xml_content_map[mode] and \
                ("keeps stopping" in xml_content_map[mode] or "isn't responding" in xml_content_map[mode]):
            message_list.append(f"{mode} crashed!")
            issue_status = min(issue_status, CRASHED)
    xml_similar = {}
    for i, mode in enumerate(modes):
        xml_similar[f"{mode}_{mode}"] = True
        for mode2 in modes[i+1:]:
            xml_similar[f"{mode}_{mode2}"] = (xml_content_map[mode] == xml_content_map[mode2])
            xml_similar[f"{mode2}_{mode}"] = xml_similar[f"{mode}_{mode2}"]

    if issue_status == ACCESSIBLE or "FAILED" in action[f'areg_action_result'][0] or "COMPLETED_BY_HELP" in action[f'tb_action_result'][0]:
        if xml_problem:
            message_list.append("Problem with XML")
            issue_status = OTHER
        else:
            if is_sighted:
                if "COMPLETED_BY_HELP" in action[f'tb_action_result'][0]:
                    if xml_similar['exp_areg']:
                        message_list.append("Ineffective")
                        issue_status = INEFFECTIVE
                    elif not xml_similar['reg_areg']:
                        message_list.append("areg overlapping!")
                        issue_status = API_SMELL
                    else:
                        message_list.append("Directional Unreachable")
                        issue_status = A11Y_WARNING
                elif "FAILED" in action[f'areg_action_result'][0]:
                    if xml_similar['exp_tb']:
                        message_list.append("Ineffective")
                        issue_status = INEFFECTIVE
                elif xml_similar['tb_reg']:
                    if xml_similar['exp_tb']:
                        message_list.append("Ineffective")
                        issue_status = INEFFECTIVE
                    else:
                        message_list.append("Directional Unreachable")
                        issue_status = A11Y_WARNING
                else:
                    if is_tb_web_view_adaptive(xml_similar, xml_content_map, action, is_sighted):
                        message_list.append("Loading WebView for TalkBack")
                        issue_status = TB_WEBVIEW_LOADING
                    elif xml_similar['exp_reg']:
                        message_list.append("Overlapping")
                        issue_status = API_SMELL
                    elif login_with(xml_similar, xml_content_map, action, is_sighted):
                        message_list.append("External Service")
                        message_list.append("Directional Unreachable")
                        issue_status = A11Y_WARNING
                    elif 'package="com.android.chrome"' in xml_content_map['tb']\
                            and 'package="com.android.chrome"' in xml_content_map['reg']:
                        message_list.append("Directional Unreachable")
                        issue_status = A11Y_WARNING
                    elif is_loading(xml_similar, xml_content_map, action, is_sighted):
                        message_list.append("Directional Unreachable")
                        message_list.append("Loading")
                        issue_status = A11Y_WARNING
                    else:
                        message_list.append("Different Behavior")
                        issue_status = TB_A11Y_ISSUE
            else:
                if "FAILED" in action[f'areg_action_result'][0]:
                    if xml_similar['exp_tb']:
                        message_list.append("Ineffective")
                        issue_status = INEFFECTIVE
                elif not xml_similar['tb_reg']:
                    if is_tb_web_view_adaptive(xml_similar, xml_content_map, action, is_sighted):
                        message_list.append("Loading WebView for TalkBack")
                        issue_status = TB_WEBVIEW_LOADING
                    elif xml_similar['exp_reg']:
                        if 'android.widget.NumberPicker' in action['element']['xpath']:
                            message_list.append("NumberPicker")
                            issue_status = OTHER
                        else:
                            message_list.append("Overlapping")
                            issue_status = A11Y_WARNING
                    elif 'package="com.android.chrome"' in xml_content_map['tb'] \
                            and 'package="com.android.chrome"' in xml_content_map['reg']:
                        message_list.append("Accessible")
                        issue_status = ACCESSIBLE
                    else:
                        if login_with(xml_similar, xml_content_map, action, is_sighted):
                            message_list.append("Login with Service")
                            issue_status = EXTERNAL_SERVICE
                        elif is_loading(xml_similar, xml_content_map, action, is_sighted):
                            message_list.append("Loading")
                            issue_status = LOADING
                        else:
                            message_list.append("Different Behavior")
                            issue_status = TB_A11Y_ISSUE
                elif not xml_similar['reg_areg']:
                    if is_loading(xml_similar, xml_content_map, action, is_sighted):
                        message_list.append("Loading")
                        issue_status = LOADING
                    else:
                        message_list.append("Different Behavior in areg!")
                        issue_status = API_A11Y_ISSUE

    if issue_status == ACCESSIBLE:
        message_list = ["Accessible"]

    result = PostAnalysisResult(action=action,
                                issue_status=issue_status,
                                message="\n".join(reversed(message_list)),
                                is_sighted=is_sighted,
                                xml_similar_map=xml_similar)
    return result

def do_post_analysis(name: str = None,
                     result_path: Union[str, Path] = None,
                     app_path: Union[str, Path] = None,
                     snapshot_path: Union[str, Path] = None,
                     force: bool = False,
                     override: bool = False,
                     remove: bool = False) -> int:
    post_analyzers = {
        "V1": post_analyzer_v1,
        "V2": post_analyzer_v2,
        "V3": post_analyzer_v3,
    }
    if name is None:
        name = LAST_VERSION
    if name not in post_analyzers:
        logger.error(f"Error. The post analyzer with name {name} doesn't exist!")
        return 0
    post_analyzer = post_analyzers[name]
    logger.info(f"Post Analyzer: {name}")

    snapshot_paths = get_snapshot_paths(result_path, app_path, snapshot_path)

    output_name = f"{POST_ANALYSIS_PREFIX}_{name}.jsonl"
    analyzed = 0
    for snapshot_path in snapshot_paths:
        logger.info(f"Post-analyzing Snapshot in path'{snapshot_path}'...")
        address_book = AddressBook(snapshot_path)
        if remove:
            if address_book.snapshot_result_path.joinpath(output_name).exists():
                address_book.snapshot_result_path.joinpath(output_name).unlink()
            continue

        if not force and not address_book.finished_path.exists():
            logger.error(f"The snapshot didn't finish!")
            continue
        if not override and address_book.snapshot_result_path.joinpath(output_name).exists():
            logger.debug(f"The post analysis is already done!")
            continue
        try:
            with open(address_book.snapshot_result_path.joinpath(output_name), 'w') as write_file:
                with open(address_book.action_path) as read_file:
                    for line in read_file.readlines():
                        action = json.loads(line)
                        result = post_analyzer(action, address_book, is_sighted=False)
                        write_file.write(result.toJSON() + "\n")
                with open(address_book.s_action_path) as read_file:
                    for line in read_file.readlines():
                        action = json.loads(line)
                        result = post_analyzer(action, address_book, is_sighted=True)
                        write_file.write(result.toJSON() + "\n")
        except Exception as e:
            logger.error(f"Exception:", exc_info=e)
            if address_book.snapshot_result_path.joinpath(output_name).exists():
                os.remove(address_book.snapshot_result_path.joinpath(output_name))
        analyzed += 1
    return analyzed


def get_post_analysis(snapshot_path: Union[str, Path]) -> dict:
    if isinstance(snapshot_path, str):
        snapshot_path = Path(snapshot_path)
    post_analysis_results = {'sighted': defaultdict(dict), 'unsighted': defaultdict(dict)}
    if not snapshot_path.is_dir():
        return post_analysis_results

    for post_result_path in snapshot_path.iterdir():
        if post_result_path.name.startswith(POST_ANALYSIS_PREFIX):
            analysis_name = post_result_path.name[len(POST_ANALYSIS_PREFIX)+1:-len('.jsonl')]
            with open(str(post_result_path), "r") as f:
                for line in f.readlines():
                    result = json.loads(line)
                    if result['is_sighted']:
                        post_analysis_results['sighted'][result['index']][analysis_name] = result
                    else:
                        post_analysis_results['unsighted'][result['index']][analysis_name] = result
    return post_analysis_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot-path', type=str, help="Path of the snapshot's result")
    parser.add_argument('--app-path', type=str, help="Path of the app's result")
    parser.add_argument('--result-path', type=str, help="Path of the result's path")
    parser.add_argument('--name', type=str, required=True, help="Analysis Name")
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--override', action='store_true')
    parser.add_argument('--remove', action='store_true')
    parser.add_argument('--log-path', type=str, help="Path where logs are written")
    args = parser.parse_args()

    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    if args.log_path:
        logging.basicConfig(level=level,
                            handlers=[
                                logging.FileHandler(args.log_path, mode='w'),
                                logging.StreamHandler()])
    else:
        logging.basicConfig(level=level)

    do_post_analysis(name=args.name,
                     result_path=args.result_path,
                     app_path=args.app_path,
                     snapshot_path=args.snapshot_path,
                     force=args.force,
                     override=args.override,
                     remove=args.remove)
