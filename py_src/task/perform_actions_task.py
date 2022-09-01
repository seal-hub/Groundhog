import json
import logging

from GUI_utils import Node
from command import ClickCommand, CommandResponse, LocatableCommandResponse
from consts import BLIND_MONKEY_TAG, BLIND_MONKEY_EVENTS_TAG
from controller import TalkBackTouchController, TouchController, A11yAPIController, TalkBackAPIController
from latte_executor_utils import report_atf_issues
from padb_utils import ParallelADBLogger
from results_utils import AddressBook, Actionables, capture_current_state, ActionResult
from snapshot import EmulatorSnapshot
from task.snapshot_task import SnapshotTask
from utils import annotate_elements, annotate_rectangle

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
                    action_results['tb_touch_failed'] = action_response.toJSON()
                    logger.info(f"The TalkBack Touch Controller could not locate the element! {node.xpath}")
                    # TODO: Need to write something
                    controller = controllers['tb_api']
                    await controller.setup()
                    result = await padb_logger.execute_async_with_log(
                        controller.execute(command),
                        tags=tags)
                    log_message_map: dict = result[0]
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

    async def write_ATF_issues(self):
        atf_issues = await report_atf_issues()
        logger.info(f"There are {len(atf_issues)} ATF issues in this screen!")
        with open(self.snapshot.address_book.perform_actions_atf_issues_path, "w") as f:
            for issue in atf_issues:
                f.write(json.dumps(issue) + "\n")
        annotate_elements(self.snapshot.initial_screenshot,
                          self.snapshot.address_book.perform_actions_atf_issues_screenshot,
                          atf_issues)
