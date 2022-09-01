import json
import logging
import subprocess
from collections import namedtuple, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Union, List

from GUI_utils import NodesFactory
from results_utils import AddressBook, ActionResult
from post_analysis import get_post_analysis, SUCCESS, A11Y_WARNING, OTHER, INEFFECTIVE, \
    CRASHED, API_SMELL, EXTERNAL_SERVICE, LOADING, TB_WEBVIEW_LOADING, API_A11Y_ISSUE, TB_A11Y_ISSUE
from search_utils import contains_node_with_attrs, compare_bool, compare_int
from utils import convert_bounds


class SearchActionResult:
    def __init__(self, address_book: AddressBook, action_result: ActionResult):
        self.address_book = address_book
        self.action_result = action_result


class SearchActionQuery:
    def __init__(self):
        self.filters = []
        self.valid_app = None

    def is_valid_app(self, app_name):
        if self.valid_app is None:
            return True
        return app_name == self.valid_app

    def set_valid_app(self, app_name):
        if app_name != 'All':
            self.valid_app = app_name
        return self

    def satisfies(self, address_book: AddressBook, action_result: ActionResult) -> bool:
        for i_filter in self.filters:
            if not i_filter(address_book, action_result):
                return False
        return True

    def contains_action_with_attrs(self, attr_names: List[str], attr_queries: List[str]):
        def action_attr_satisfies(address_book: AddressBook, action_result: ActionResult) -> bool:
            return contains_node_with_attrs([action_result.node], attr_names, attr_queries)
        if attr_names and attr_queries:
            self.filters.append(action_attr_satisfies)
        return self

    def contains_layout_with_attrs(self, attr_names: List[str], attr_queries: List[str]):
        def layout_attr_satisfies(address_book: AddressBook, action_result: ActionResult) -> bool:
            nodes = NodesFactory() \
                .with_layout_path(address_book.get_layout_path(AddressBook.BASE_MODE, AddressBook.INITIAL)) \
                .with_xpath_pass() \
                .with_ad_detection() \
                .build()
            return contains_node_with_attrs(nodes, attr_names, attr_queries)
        if attr_names and attr_queries:
            self.filters.append(layout_attr_satisfies)
        return self

    def contains_tags(self, include_tags: List[str], exclude_tags: List[str]):
        include_tags = [x for x in include_tags if x]
        exclude_tags = [x for x in exclude_tags if x]

        def tag_satisfies(address_book: AddressBook, action_result: ActionResult) -> bool:
            if not address_book.tags_path.exists():
                return len(exclude_tags) >= 0 and len(include_tags) == 0
            action_tags = address_book.whelper.get_tags(action_result.index)

            for tag in include_tags:
                if tag not in action_tags:
                    return False

            for tag in action_tags:
                if tag in exclude_tags:
                    return False

            return True

        self.filters.append(tag_satisfies)
        return self

    def has_summary(self, summary_names: List[str], summary_values: List[str]):
        def has_summary_satisfies(address_book: AddressBook, action_result: ActionResult) -> bool:
            summary = address_book.whelper.action_summary(action_result.index)
            for name, value in zip(summary_names, summary_values):
                if name == 'ANY' or not value:
                    continue
                if name == "only_touch_change_event":
                    res = len(summary["changed_elements_touch"]) > 0 and len(summary["changed_elements_tb_touch"]) == 0 and len(summary["changed_elements_a11y_api"]) == 0
                    if not res:
                        return False
                    continue
                if name not in summary:
                    return False
                if name == "children_nodes_action_indices" or name.startswith("changed_elements_"):
                    if not compare_int(len(summary[name]), value):
                        return False
                    continue

                if not compare_bool(summary[name], value):
                    return False

            return True

        if summary_names and summary_values:
            self.filters.append(has_summary_satisfies)
        return self

    def post_analysis(self, post_analysis_result: str):
        def post_analysis_satisfies(action, post_analysis_results, address_book: AddressBook, is_sighted) -> bool:
            if post_analysis_result == 'PROCESSED':
                return len(post_analysis_results) > 0
            issue_status = [result['issue_status'] for result in post_analysis_results.values()]
            if post_analysis_result == 'ACCESSIBLE':
                return SUCCESS in issue_status
            elif post_analysis_result == 'TB_A11Y_ISSUE':
                return TB_A11Y_ISSUE in issue_status
            elif post_analysis_result == 'API_A11Y_ISSUE':
                return API_A11Y_ISSUE in issue_status
            elif post_analysis_result == 'A11Y_WARNING':
                return A11Y_WARNING in issue_status
            elif post_analysis_result == 'API_SMELL':
                return API_SMELL in issue_status
            elif post_analysis_result == 'EXTERNAL_SERVICE':
                return EXTERNAL_SERVICE in issue_status
            elif post_analysis_result == 'LOADING':
                return LOADING in issue_status
            elif post_analysis_result == 'INEFFECTIVE':
                return INEFFECTIVE in issue_status
            elif post_analysis_result == 'TB_WEBVIEW_LOADING':
                return TB_WEBVIEW_LOADING in issue_status
            elif post_analysis_result == 'CRASHED':
                return CRASHED in issue_status
            elif post_analysis_result == 'OTHER':
                return OTHER in issue_status # or not any(x in [SUCCESS, UNREACHABLE, DIFFERENT_BEHAVIOR, EXEC_FAILURE] for x in issue_status)
            return False
        if post_analysis_result != 'ANY':
            self.filters.append(post_analysis_satisfies)
        return self

    def executor_result(self, mode: str, result: str):
        def executor_result_satisfies(address_book: AddressBook, action_result: ActionResult) -> bool:
            response = None
            if mode == 'tb':
                response = action_result.tb_action_result
            elif mode == 'touch':
                response = action_result.touch_action_result
            elif mode == 'a11y_api':
                response = action_result.a11y_api_action_result
            else:
                return False
            return response.state == result

        if result != 'ALL':
            self.filters.append(executor_result_satisfies)
        return self

    def compare_xml(self, first_mode: str, second_mode: str, should_be_same: bool):
        def has_same_xml_satisfies(action, post_analysis_results, address_book: AddressBook, is_sighted) -> bool:
            modes = ['exp', 'tb', 'reg', 'areg']
            if first_mode not in modes or second_mode not in modes:
                return True
            if len(post_analysis_results) == 0:
                return True
            key = f'{first_mode}_{second_mode}'
            for post_analysis_result in post_analysis_results.values():
                xml_similar_map = post_analysis_result.get('xml_similar_map', {})
                if key not in xml_similar_map:
                    continue
                if xml_similar_map[key] != should_be_same:
                    return False
            return True

        self.filters.append(has_same_xml_satisfies)
        return self

    def compare_screen(self, first_mode: str, second_mode: str, should_be_same: bool):
        def has_same_screen_satisfies(action, post_analysis_results, address_book: AddressBook, is_sighted) -> bool:
            modes = ['exp', 'tb', 'reg', 'areg']
            if first_mode not in modes or second_mode not in modes:
                return True
            prefix = 's_' if is_sighted else ''
            left_screen_path = address_book.get_screenshot_path(f"{prefix}{first_mode}", action['index'], should_exists=True)
            right_screen_path = address_book.get_screenshot_path(f"{prefix}{second_mode}", action['index'], should_exists=True)
            if left_screen_path is None or right_screen_path is None:
                return False
            cmd = f"diff --unified {left_screen_path} {right_screen_path}"
            diff_string = subprocess.run(cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8')
            return (len(diff_string) == 0) == should_be_same

        self.filters.append(has_same_screen_satisfies)
        return self


class SearchActionManager:
    def __init__(self, result_path: Path):
        self.result_path = result_path

    def search(self,
               search_query: SearchActionQuery,
               action_limit: int = 10000,
               action_per_snapshot_limit: int = 1000,
               ) -> List[SearchActionResult]:
        search_action_result_list = []
        for app_path in self.result_path.iterdir():
            if len(search_action_result_list) >= action_limit:
                break
            if not app_path.is_dir():
                continue
            if not search_query.is_valid_app(app_path.name):
                continue
            for snapshot_path in app_path.iterdir():
                if len(search_action_result_list) >= action_limit:
                    break
                if not snapshot_path.is_dir():
                    continue

                action_in_snapshot_count = 0
                address_book = AddressBook(snapshot_path)
                if "ManualIgnored" in address_book.whelper.get_note():  # TODO: REMOVED
                    continue
                if not address_book.perform_actions_results_path.exists():
                    continue
                for action_result in address_book.whelper.get_actions():
                    if len(search_action_result_list) >= action_limit or action_in_snapshot_count >= action_per_snapshot_limit:
                        break
                    if not search_query.satisfies(address_book, action_result):
                        continue
                    search_action_result = SearchActionResult(address_book, action_result)
                    search_action_result_list.append(search_action_result)
                    action_in_snapshot_count += 1
        return search_action_result_list


@lru_cache(maxsize=None)
def get_search_manager(result_path: Union[str, Path]):
    """
    Given the result_path, creates and returns a SearchManager. The return value is cached
    """
    if isinstance(result_path, str):
        result_path = Path(result_path)
    return SearchActionManager(result_path)