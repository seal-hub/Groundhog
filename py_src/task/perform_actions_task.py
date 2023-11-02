import json
import logging
import os

import cv2

from GUI_utils import Node
from command import ClickCommand, CommandResponse, LocatableCommandResponse
from consts import BLIND_MONKEY_TAG, BLIND_MONKEY_EVENTS_TAG
from controller import TalkBackTouchController, TouchController, A11yAPIController, TalkBackAPIController
from latte_executor_utils import report_atf_issues
from padb_utils import ParallelADBLogger
from results_utils import AddressBook, Actionables, capture_current_state, ActionResult
from snapshot import EmulatorSnapshot
from task.snapshot_task import SnapshotTask
from utils import annotate_elements, annotate_rectangle, compare_images

logger = logging.getLogger(__name__)


class PerformActionsTask(SnapshotTask):
    def __init__(self, snapshot: EmulatorSnapshot):
        if not isinstance(snapshot, EmulatorSnapshot):
            raise Exception("Perform Actions task requires a EmulatorSnapshot!")
        super().__init__(snapshot)

    async def execute(self):
        snapshot: EmulatorSnapshot = self.snapshot
        if not snapshot.address_book.audit_path_map[AddressBook.EXTRACT_ACTIONS].exists():
            logger.error("The actions should be extracted first!")
            return
        snapshot.address_book.initiate_perform_actions_task()
        controllers = {
            'tb_touch': TalkBackTouchController(),
            'tb_api': TalkBackAPIController(),
            'a11y_api': A11yAPIController(),
            'touch': TouchController()
        }
        padb_logger = ParallelADBLogger(snapshot.device)
        await self.write_ATF_issues()
        selected_actionable_nodes = []
        with open(snapshot.address_book.extract_actions_nodes[Actionables.Selected]) as f:
            for line in f.readlines():
                node = Node.createNodeFromDict(json.loads(line.strip()))
                selected_actionable_nodes.append(node)
        logger.info(f"There are {len(selected_actionable_nodes)} actionable nodes!")
        tags = [BLIND_MONKEY_TAG, BLIND_MONKEY_EVENTS_TAG]
        a11y_ineffective_node = []
        tb_api_unlocatable_node = []
        tb_touch_ineffective_node = []
        tb_touch_unlocatable_node = []
        for index, node in enumerate(selected_actionable_nodes):
            command = ClickCommand(node)
            logger.info(f"Action {index}/({len(selected_actionable_nodes) - 1}): Clicking on node {node.xpath}!")
            action_results = {}
            for controller_mode in ['tb_touch', 'a11y_api', 'touch']:
                logger.info(f"Reloading the snapshot for controller {controller_mode}")
                await snapshot.reload()
                controller = controllers[controller_mode]
                await controller.setup()
                logger.info(f"Executing the command with controller {controller_mode}")
                result = await padb_logger.execute_async_with_log(
                    controller.execute(command),
                    tags=tags)
                log_message_map: dict = result[0]
                action_response: LocatableCommandResponse = result[1]
                if controller_mode == 'tb_touch' and action_response.state != 'COMPLETED':
                    tb_touch_unlocatable_node.append(node)
                    action_results['tb_touch_failed'] = action_response.toJSON()
                    logger.info(f"The TalkBack Touch Controller could not locate the element! {node.xpath}")
                    # TODO: Need to write something
                    controller = controllers['tb_api']
                    await controller.setup()
                    result = await padb_logger.execute_async_with_log(
                        controller.execute(command),
                        tags=tags)
                    log_message_map: dict = result[0]
                    if controller_mode == 'tb_api' and action_response.state != 'COMPLETED':
                        tb_api_unlocatable_node.append(node)
                    action_response: LocatableCommandResponse = result[1]
                logger.info(f"The action is performed in {action_response.duration}ms! State: {action_response.state} ")
                action_results[controller_mode] = action_response
                await capture_current_state(snapshot.address_book,
                                            snapshot.device,
                                            mode=controller_mode,
                                            index=index,
                                            log_message_map=log_message_map,
                                            dumpsys=True,
                                            has_layout=True)
            a11y_api_res = snapshot.address_book.mode_path_map["a11y_api"]
            tb_touch_res = snapshot.address_book.mode_path_map["tb_touch"]
            touch_res = snapshot.address_book.mode_path_map["touch"]

            # files_a11y_api = sorted([f for f in os.listdir(a11y_api_res) if f.endswith('.png')])
            # files_tb_touch = sorted([f for f in os.listdir(tb_touch_res) if f.endswith('.png')])
            # files_touch = sorted([f for f in os.listdir(touch_res) if f.endswith('.png')])
            #
            # for file_a11y_api, file_tb_touch, file_touch in zip(files_a11y_api, files_tb_touch, files_touch):

            image_a11y = cv2.imread(os.path.join(a11y_api_res, str(index) + ".png"))
            image_tb_touch = cv2.imread(os.path.join(tb_touch_res, str(index) + ".png"))
            benchmark = cv2.imread(os.path.join(touch_res, str(index) + ".png"))
            a11y_action_res = compare_images(image_a11y, benchmark)
            tb_touch_action_res = compare_images(image_tb_touch, benchmark)
            if a11y_action_res == False:
                a11y_ineffective_node.append(node)
            if tb_touch_action_res == False and node not in tb_touch_unlocatable_node:
                tb_touch_ineffective_node.append(node)

            action_result = ActionResult(index=index,
                                         node=node,
                                         tb_action_result=action_results['tb_touch'],
                                         touch_action_result=action_results['touch'],
                                         a11y_api_action_result=action_results['a11y_api'],
                                         tb_touch_failed=action_results.get('tb_touch_failed', None))
            with open(snapshot.address_book.perform_actions_results_path, "a") as f:
                f.write(f"{action_result.toJSONStr()}\n")
            # Post process
            annotate_rectangle(snapshot.initial_screenshot,
                               snapshot.address_book.audit_path_map[AddressBook.PERFORM_ACTIONS].joinpath(
                                   f"{index}.png"),
                               bounds=[node.bounds,
                                       action_results['tb_touch'].acted_node.bounds,
                                       action_results['touch'].acted_node.bounds,
                                       action_results['a11y_api'].acted_node.bounds, ],
                               outline=[(244, 164, 96), (144, 238, 144), (220, 20, 60), (0, 139, 139)],
                               width=[5, 15, 5, 5],
                               scale=[1, 20, 7, 13])
        if len(tb_touch_unlocatable_node) !=0:
            annotate_elements(self.snapshot.initial_screenshot,
                              self.snapshot.address_book.tb_touch_unlocatable_nodes_screenshot,
                              tb_touch_unlocatable_node)
        if len(tb_api_unlocatable_node) !=0:
            annotate_elements(self.snapshot.initial_screenshot,
                              self.snapshot.address_book.tb_api_unlocatable_nodes_screenshot,
                              tb_api_unlocatable_node)
        if len(tb_touch_ineffective_node) !=0:
            annotate_elements(self.snapshot.initial_screenshot,
                              self.snapshot.address_book.tb_touch_ineffective_nodes_screenshot,
                              tb_touch_ineffective_node)
        if len(a11y_ineffective_node) !=0:
            annotate_elements(self.snapshot.initial_screenshot,
                              self.snapshot.address_book.a11y_ineffective_nodes_screenshot,
                              a11y_ineffective_node)

    async def write_ATF_issues(self):
        atf_issues = await report_atf_issues()
        logger.info(f"There are {len(atf_issues)} ATF issues in this screen!")
        with open(self.snapshot.address_book.perform_actions_atf_issues_path, "w") as f:
            for issue in atf_issues:
                f.write(json.dumps(issue) + "\n")
        annotate_elements(self.snapshot.initial_screenshot,
                          self.snapshot.address_book.perform_actions_atf_issues_screenshot,
                          atf_issues)
