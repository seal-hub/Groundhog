import logging
import asyncio
import json
from collections import defaultdict
from typing import List, Tuple, Union, Dict
from ppadb.client_async import ClientAsync as AdbClient

from GUI_utils import get_nodes, get_actions_from_layout, is_clickable_element_or_none, \
    get_element_from_xpath, Node
from a11y_service import A11yServiceManager
from adb_utils import load_snapshot, save_snapshot, is_android_activity_on_top, get_current_activity_name
from latte_executor_utils import tb_navigate_next, tb_perform_select, tb_focused_node, execute_command, \
    get_missing_actions, latte_capture_layout as capture_layout, report_atf_issues
from padb_utils import ParallelADBLogger
from results_utils import AddressBook, ResultWriter
from sb_utils import statice_analyze
from utils import annotate_elements
from consts import EXPLORE_VISIT_LIMIT, DEVICE_NAME, ADB_HOST, ADB_PORT, BLIND_MONKEY_TAG, \
    BLIND_MONKEY_INSTRUMENTED_TAG, BLIND_MONKEY_EVENTS_TAG

logger = logging.getLogger(__name__)


class BM_SnapshotManager:
    def __init__(self,
                 snapshot_name: str,
                 address_book: AddressBook,
                 visited_elements_in_app: Dict[str, Node] = None,
                 is_oversight: bool = False,
                 instrumented_log: bool = False,
                 directional_action_limit: int = 1000,
                 point_action_limit: int = 1000,
                 device=None):
        self.initial_snapshot = snapshot_name
        self.tmp_snapshot = self.initial_snapshot + "_TMP"
        self.directional_action_limit = directional_action_limit
        self.point_action_limit = point_action_limit
        self.address_book = address_book
        self.instrumented_log = instrumented_log
        self.is_oversight = is_oversight
        self.writer = ResultWriter(address_book)
        self.is_next_direction = True
        self.visited_elements_in_app = {} if visited_elements_in_app is None else visited_elements_in_app
        # -------------
        self.init_layout = None
        self.visible_elements = []
        self.valid_resource_ids = set()
        self.valid_xpaths = {}
        self.visited_resource_ids = set()
        self.visited_xpath_count = defaultdict(int)
        self.performed_actions = []
        # -------------
        if device is None:
            client = AdbClient(host=ADB_HOST, port=ADB_PORT)
            device = asyncio.run(client.device(DEVICE_NAME))
        self.device = device

    def has_element_in_other_snapshots(self, node: Node) -> bool:
        for other_node in self.visited_elements_in_app.get(node.xpath, []):
            if node.practically_equal(other_node):
                logger.debug(f"Exclude the visited element in the app {node}")
                return True
        return False

    async def emulator_setup(self) -> bool:
        """
        Loads the snapshot into emulator, configures the required services, and sets up Latte.
        Then saves the configured snapshot into Temp Snapshot.
        Finally, it analyzes all elements in the screen and exclude the already seen (in other snapshots)
        :return: Whether the setup is succeeded or not
        """
        if not await load_snapshot(self.initial_snapshot, device_name=self.device.serial):
            logger.error("Error in loading snapshot")
            return False
        if not self.is_oversight and await is_android_activity_on_top(device_name=self.device.serial):
            logger.error("The snapshot is broken! There is an Android Activity on Top")
            return False
        await A11yServiceManager.setup_latte_a11y_services(tb=True)
        logger.info("Enabled A11y Services:" + str(await A11yServiceManager.get_enabled_services()))
        await asyncio.sleep(3)
        await save_snapshot(self.tmp_snapshot)
        self.writer.start_explore()
        # ------------- TODO: think about it later ----------
        # dom = await capture_layout()

        self.init_layout = await self.writer.capture_current_state(self.device, mode="exp", index="INITIAL",
                                                                   has_layout=True)
        oac_nodes = statice_analyze(layout_path=self.writer.address_book.get_layout_path("exp", "INITIAL"),
                        screenshot_path=self.writer.address_book.get_screenshot_path("exp", "INITIAL"),
                        address_book=self.writer.address_book)
        xpath_to_oac_node = {}
        for node in oac_nodes:
            xpath_to_oac_node[node.xpath] = node
        atf_issues = await report_atf_issues()
        logger.info(f"There are {len(atf_issues)} ATF issues in this screen!")
        with open(self.address_book.atf_issues_path, "w") as f:
            for issue in atf_issues:
                f.write(json.dumps(issue) + "\n")
        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.atf_issues_screenshot,
                          atf_issues)
        self.visible_elements = get_nodes(self.init_layout)
        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.all_element_screenshot,
                          self.visible_elements)
        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.all_action_screenshot,
                          await self.get_important_actions(initialize=False, layout=self.init_layout),
                          outline=(138, 43, 226),
                          width=15)
        self.valid_resource_ids = set()
        self.valid_xpaths = {}
        already_visited_elements = []
        for node in self.visible_elements:
            if self.has_element_in_other_snapshots(node):
                already_visited_elements.append(node)
                if not self.is_oversight:
                    logger.debug(f"Exclude the visited element in the app {node}")
                    continue
            if node.xpath:
                if self.is_oversight:
                    if node.xpath not in xpath_to_oac_node:
                        continue
                self.valid_xpaths[node.xpath] = node
            if node.resource_id:
                self.valid_resource_ids.add(node.resource_id)

        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.redundant_action_screenshot,
                          already_visited_elements)
        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.valid_action_screenshot,
                          list(self.valid_xpaths.values()))
        logger.info(f"There are {len(self.valid_xpaths)} valid elements,"
                    f" and {len(already_visited_elements)} elements have been seen in other snapshots!")
        with open(self.address_book.valid_elements_path, "w") as f:
            for valid_node in self.valid_xpaths.values():
                f.write(f"{valid_node.toJSONStr()}\n")
        self.visited_resource_ids = set()
        self.visited_xpath_count = defaultdict(int)
        self.performed_actions = []
        # -------------
        return True

    async def navigate_next(self, padb_logger: ParallelADBLogger, initialize: bool = True) -> Tuple[str, Union[str, None]]:
        """
        Loads the tmp Snapshot (the latest snapshot in navigation), navigate to next element by TalkBack until it either
        reaches a new important element or finishes the navigation. An important element should belong to the initial
        snapshot, should not have been visited before in this or other snapshots.

        :param: padb_logger: To capture the logs of Latte during TalkBack navigation
        :return: A tuple of
                'Log Message' (the logs during the navigation) and
                'Next Command' (the newly focused element). If Next Command is None, the navigation is finished.
        """
        logger.info("Navigating to the next element")
        if initialize:
            if not await load_snapshot(self.tmp_snapshot):
                logger.debug("Error in loading snapshot")
                return "The snapshot could not be loaded!", None
        all_log_message = ""
        tags = [BLIND_MONKEY_TAG]
        if self.instrumented_log:
            tags.append(BLIND_MONKEY_INSTRUMENTED_TAG)

        while True:
            log_message_map, next_command_str = await padb_logger\
                .execute_async_with_log(
                    tb_navigate_next(not self.is_next_direction),
                    tags=tags)
            if len(tags) == 1:
                all_log_message += list(log_message_map.values())[0]
            else:
                all_log_message += "".join(f"---Start {key}-----\n"
                                           f"{value}\n"
                                           f"----End {key}----\n"
                                           for (key, value) in log_message_map.items())
            if not next_command_str or next_command_str == "Error":
                logger.error("TalkBack cannot navigate to the next element")
                return all_log_message, None
            if not self.is_oversight and await is_android_activity_on_top():
                logger.info("We are not in the app under test!")
                return f"The current activity is {await get_current_activity_name()}", None
            command_json = json.loads(next_command_str)
            logger.debug(f"Current element: {command_json}")
            if command_json['xpath'] != 'null':
                self.visited_xpath_count[command_json['xpath']] += 1
                if self.visited_xpath_count[command_json['xpath']] > EXPLORE_VISIT_LIMIT:
                    logger.info(
                        f"The XPath {command_json['xpath']}"
                        f" is visited more than {EXPLORE_VISIT_LIMIT} times, break. ")
                    return all_log_message, None
            else:
                logger.error(f"The xpath is null for element {command_json}")
            # TODO: Update visited* with next_command_json
            # TODO: Skip if the position is also the same
            if command_json['xpath'] not in self.valid_xpaths:
                self.writer.visit_element(command_json, 'skipped', None)
                logger.debug("Not a valid xpath!")
                continue
            if next_command_str in self.performed_actions:
                self.writer.visit_element(command_json, 'repetitive', self.valid_xpaths[command_json['xpath']])
                logger.debug("Has seen this command before!")
                continue
            # if command_json['resourceId'] in self.visited_resource_ids:
            #     self.writer.visit_element(command_json, 'repetitive', self.valid_xpaths[command_json['xpath']])
            #     logger.debug("Has seen this resourceId")
            #     continue
            if self.visited_xpath_count[command_json['xpath']] > 1:  # TODO: Configurable
                self.writer.visit_element(command_json, 'repetitive', self.valid_xpaths[command_json['xpath']])
                logger.debug("Has seen this xpath more than twice")
                continue
            if not is_clickable_element_or_none(self.init_layout, command_json['xpath']):
                self.writer.visit_element(command_json, 'unclickable', self.valid_xpaths[command_json['xpath']])
                logger.debug("The element is not clickable!")
                continue
            self.writer.visit_element(command_json, 'selected', self.valid_xpaths[command_json['xpath']])
            # TODO: make it a counter
            if command_json['resource_id'] != 'null':
                self.visited_resource_ids.add(command_json['resource_id'])
            break
        return all_log_message, next_command_str

    async def directed_explore(self) -> bool:
        if not await self.emulator_setup():
            logger.error("Error in emulator setup!")
            return False
        padb_logger = ParallelADBLogger(self.device)
        await self.writer.capture_current_state(self.device, mode="exp",
                                                index=self.writer.get_action_index(),
                                                log_message_map={BLIND_MONKEY_TAG: "First State"},
                                                has_layout=True)
        while True:
            # ------------------- Navigate Next -------------------
            tb_navigate_log, next_focused_element = await self.navigate_next(padb_logger, initialize=False)
            if not next_focused_element:
                if self.is_next_direction:
                    logger.info("Change the direction!")
                    self.is_next_direction = False
                    for key, value in self.visited_xpath_count.items():
                        self.visited_xpath_count[key] = value - 1
                    if not await load_snapshot(self.initial_snapshot):
                        logger.debug("Error in loading snapshot")
                        return False
                    tb_navigate_log, next_focused_element = await self.navigate_next(padb_logger, initialize=False)
                if not next_focused_element:
                    logger.info("Navigation is finished!")
                    self.writer.write_last_navigate_log(tb_navigate_log)
                    break
            logger.debug("Next focused element is " + next_focused_element)
        visited_elements = [visited_element['element'] if visited_element['node'] is None
                            else visited_element['node'] for visited_element in self.writer.visited_elements]
        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.visited_elements_screenshot,
                          visited_elements)
        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.visited_elements_gif,
                          visited_elements)
        logger.info("Done Exploring!")
        return True

    async def point_action(self):
        if not self.address_book.visited_elements_path.exists():
            if not await self.emulator_setup():
                logger.error("Error in emulator setup!")
            return False
        logger.info("Performing actions")
        self.writer.start_stb()
        important_actions = await self.get_important_actions()
        logger.info(f"There are {len(important_actions)} actions in explore!")
        initial_layout = await self.writer.capture_current_state(self.device, 's_exp', 'INITIAL')
        with open(self.address_book.s_possible_action_path, "w") as f:
            for node in important_actions:
                f.write(f"{node.toJSONStr()}\n")
        annotate_elements(self.address_book.get_screenshot_path('s_exp', 'INITIAL'),
                          self.address_book.s_action_screenshot,
                          important_actions)
        is_in_app_activity = not await is_android_activity_on_top()
        padb_logger = ParallelADBLogger(self.device)
        if self.is_oversight or is_in_app_activity:
            for index, action in enumerate(important_actions):
                if self.writer.get_action_index() >= self.point_action_limit:
                    logger.info(f"Reached point action limit: {self.point_action_limit}")
                    break
                logger.info(
                    f"Point Action {self.writer.get_action_index()}, count: {index+1} / {len(important_actions)}")
                if get_element_from_xpath(initial_layout, action.xpath) is None:
                    logger.warning(f"Couldn't find this element on the screen")
                    continue
                result_map = {mode: None for mode in ['reg', 'areg', 'tb']}
                modes = ['tb', 'reg', 'areg']
                tags = [BLIND_MONKEY_TAG, BLIND_MONKEY_EVENTS_TAG]
                if self.instrumented_log:
                    tags.append(BLIND_MONKEY_INSTRUMENTED_TAG)
                for mode in modes:
                    if not await load_snapshot(self.initial_snapshot):
                        logger.error("Error in loading snapshot")
                        return []
                    executor = mode if mode != 'tb' else 'stb'
                    log_message_map, result_map[mode] = await padb_logger.execute_async_with_log(
                        execute_command(action.toJSONStr(), executor_name=executor, api_focus=False), tags=tags)
                    layout = await self.writer.capture_current_state(self.device, f"s_{mode}",
                                                                     self.writer.get_action_index(),
                                                                     log_message_map=log_message_map)

                logger.info(f"Writing action {self.writer.get_action_index()}")
                self.writer.add_action(element=json.loads(action.toJSONStr()),
                                       tb_action_result=result_map['tb'],
                                       reg_action_result=result_map['reg'],
                                       areg_action_result=result_map.get('areg', None),
                                       node=action,
                                       is_sighted=True)
        logger.info("Done validating remaining actions.")

    async def directed_explore_action(self) -> bool:
        if not await self.emulator_setup():
            logger.error("Error in emulator setup!")
            return False
        padb_logger = ParallelADBLogger(self.device)
        await self.writer.capture_current_state(self.device, mode="exp",
                                                index=self.writer.get_action_index(),
                                                log_message_map={BLIND_MONKEY_TAG: "First State"},
                                                has_layout=True)
        next_focused_element = None
        while True:
            if len(self.performed_actions) >= self.directional_action_limit:
                logger.info(f"Reached directional action limit: {self.directional_action_limit}")
                break
            logger.info(f"Action Index: {self.writer.get_action_index()}")
            await save_snapshot(self.tmp_snapshot)
            click_command_str = await tb_focused_node()

            if not click_command_str or click_command_str == 'Error':
                logger.error(f"The focused node is None, expected focused node: {next_focused_element}")
            else:
                click_command = json.loads(click_command_str)
                if not is_clickable_element_or_none(self.init_layout, click_command['xpath']):
                    logger.info(f"The focused node is not clickable, Action: {click_command}")
                else:
                    if click_command_str != next_focused_element and next_focused_element is not None:
                        logger.error(f"The current focused element is different from the navigation's result."
                                     f"Current: {click_command_str}, NextFocusedElement: {next_focused_element}")
                    self.performed_actions.append(click_command_str)
                    modes = ['tb', 'reg', 'areg']
                    result_map = {}
                    for mode in modes:
                        logger.info(f"Executing select in Mode: {mode}")
                        tags = [BLIND_MONKEY_TAG, BLIND_MONKEY_EVENTS_TAG]
                        if self.instrumented_log:
                            tags.append(BLIND_MONKEY_INSTRUMENTED_TAG)
                        if mode != 'tb':
                            if not await load_snapshot(self.initial_snapshot):
                                logger.error("Error in loading snapshot")
                                return False
                            log_message_map, result_map[mode] = await padb_logger.execute_async_with_log(
                                execute_command(click_command_str, executor_name=mode),
                                tags=tags)
                        else:
                            log_message_map, result_map[mode] = await padb_logger.execute_async_with_log(
                                tb_perform_select(),
                                tags=tags)
                        layout = await self.writer.capture_current_state(self.device, mode,
                                                                         self.writer.get_action_index(),
                                                                         log_message_map=log_message_map)
                    # ------------------- Add action to results ---------------
                    self.writer.add_action(element=click_command,
                                           tb_action_result=result_map['tb'],
                                           reg_action_result=result_map['reg'],
                                           areg_action_result=result_map.get('areg', None),
                                           node=self.valid_xpaths.get(click_command['xpath'], None),
                                           is_sighted=False)

            # ------------------- Navigate Next -------------------
            tb_navigate_log, next_focused_element = await self.navigate_next(padb_logger)
            if not next_focused_element:
                if self.is_next_direction:
                    logger.info("Change the direction!")
                    self.is_next_direction = True
                    for key, value in self.visited_xpath_count.items():
                        self.visited_xpath_count[key] = value - 1
                    if not await load_snapshot(self.initial_snapshot):
                        logger.debug("Error in loading snapshot")
                        return False
                    tb_navigate_log, next_focused_element = await self.navigate_next(padb_logger, initialize=False)
                if not next_focused_element:
                    logger.info("Navigation is finished!")
                    self.writer.write_last_navigate_log(tb_navigate_log)
                    break
            logger.debug("Next focused element is " + next_focused_element)
            await self.writer.capture_current_state(self.device, mode="exp",
                                                    index=self.writer.get_action_index(),
                                                    log_message_map={BLIND_MONKEY_TAG: tb_navigate_log},
                                                    has_layout=True)
            # ------------------- End Navigate Next -------------------
            logger.info("Groundhog Day!")

        if next_focused_element is not None or self.directional_action_limit == 0:
            logger.info("Continue linear directional explore")
            # TODO: Refactor this
            #  The directional exploration is not done yet
            while True:
                tb_navigate_log, next_focused_element = await self.navigate_next(padb_logger, initialize=False)
                if not next_focused_element:
                    if not self.is_next_direction:
                        logger.info("Change the direction!")
                        self.is_next_direction = True
                        if not await load_snapshot(self.initial_snapshot):
                            logger.debug("Error in loading snapshot")
                            return False
                        tb_navigate_log, next_focused_element = await self.navigate_next(padb_logger)
                    if not next_focused_element:
                        logger.info("Navigation is finished!")
                        self.writer.write_last_navigate_log(tb_navigate_log)
                        break


        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.visited_action_screenshot,
                          [json.loads(str_command) for str_command in self.performed_actions])
        annotate_elements(self.address_book.get_screenshot_path('exp', 'INITIAL'),
                          self.address_book.visited_elements_screenshot,
                          [visited_element['element'] if visited_element['node'] is None
                           else visited_element['node'] for visited_element in self.writer.visited_elements])
        logger.info("Done Exploring!")
        return True

    async def get_important_actions(self, initialize: bool = True, layout: str = None) -> List[Node]:
        if initialize:
            if not await load_snapshot(self.initial_snapshot):
                logger.error("Error in loading snapshot")
                return []
        await asyncio.sleep(2)
        if layout is None:
            layout = await capture_layout()
        if self.is_oversight:
            all_actions = get_actions_from_layout(layout, only_visible=False, use_naf=False)
        else:
            all_actions = get_actions_from_layout(layout, only_visible=True, use_naf=True)
        oacs = {}
        for node in self.address_book.get_oacs():
            oacs[node.xpath] = node
        result = []
        for node in all_actions:
            if self.is_oversight:
                if node.xpath not in oacs:
                    continue
            else:
                if self.has_element_in_other_snapshots(node):
                    logger.debug(f"Sighted: Exclude the visited element in the app {node}")
                    continue
            result.append(node)
        return result

    def get_tb_done_elements(self) -> List[dict]:
        result = []
        explore_result = []
        with open(self.address_book.action_path) as f:
            for line in f.readlines():
                explore_result.append(json.loads(line))
        for action in explore_result:
            result.append(action['element'])
        return result

    async def sighted_explore_action(self):
        logger.info("Validating remaining actions.")
        self.writer.start_stb()
        important_actions = await self.get_important_actions()
        tb_done_actions = self.get_tb_done_elements()
        directional_unreachable_actions = get_missing_actions(important_actions, tb_done_actions)
        logger.info(f"There are {len(directional_unreachable_actions)} missing actions in explore!")
        initial_layout = await self.writer.capture_current_state(self.device, 's_exp', 'INITIAL')
        with open(self.address_book.s_possible_action_path, "w") as f:
            for node in directional_unreachable_actions:
                f.write(f"{node.toJSONStr()}\n")
        annotate_elements(self.address_book.get_screenshot_path('s_exp', 'INITIAL'),
                          self.address_book.s_action_screenshot,
                          directional_unreachable_actions)
        is_in_app_activity = not await is_android_activity_on_top()
        padb_logger = ParallelADBLogger(self.device)
        if self.is_oversight or is_in_app_activity:
            for index, action in enumerate(directional_unreachable_actions):
                if self.writer.get_action_index() >= self.point_action_limit:
                    logger.info(f"Reached point action limit: {self.point_action_limit}")
                    break
                logger.info(
                    f"Missing action {self.writer.get_action_index()}, count: {index} / {len(directional_unreachable_actions)}")
                if get_element_from_xpath(initial_layout, action.xpath) is None:
                    continue
                result_map = {mode: None for mode in ['reg', 'areg', 'tb']}
                modes = ['reg', 'areg']
                tags = [BLIND_MONKEY_TAG, BLIND_MONKEY_EVENTS_TAG]
                if self.instrumented_log:
                    tags.append(BLIND_MONKEY_INSTRUMENTED_TAG)
                for mode in modes:
                    if not await load_snapshot(self.initial_snapshot):
                        logger.error("Error in loading snapshot")
                        return []
                    executor = mode if mode != 'tb' else 'stb'
                    log_message_map, result_map[mode] = await padb_logger.execute_async_with_log(
                        execute_command(action.toJSONStr(), executor_name=executor), tags=tags)
                    layout = await self.writer.capture_current_state(self.device, f"s_{mode}",
                                                                     self.writer.get_action_index(),
                                                                     log_message_map=log_message_map)

                logger.info(f"Writing action {self.writer.get_action_index()}")
                self.writer.add_action(element=json.loads(action.toJSONStr()),
                                       tb_action_result=result_map['tb'],
                                       reg_action_result=result_map['reg'],
                                       areg_action_result=result_map.get('areg', None),
                                       node=action,
                                       is_sighted=True)
        logger.info("Done validating remaining actions.")
