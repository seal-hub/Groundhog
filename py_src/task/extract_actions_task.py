import json
import logging
import re
from collections import Counter, defaultdict

from GUI_utils import Node
from results_utils import Actionables
from snapshot import Snapshot
from task.snapshot_task import SnapshotTask
from utils import annotate_elements

logger = logging.getLogger(__name__)


def is_node_clickable(node: Node, use_naf: bool = True) -> bool:
    return node.clickable or \
           "16" in node.a11y_actions or \
           (node.naf if use_naf else False)


class ExtractActionsTask(SnapshotTask):
    def __init__(self, snapshot: Snapshot):
        super().__init__(snapshot)

    async def execute(self):
        self.snapshot.address_book.initiate_extract_actions_task()
        only_visible: bool = True
        no_ad: bool = True
        actionable_node_queries = [is_node_clickable]
        if only_visible:
            actionable_node_queries.append(lambda node: node.visible)
        if no_ad:
            actionable_node_queries.append(lambda node: not node.is_ad)
        nodes_map = {}
        for mode in self.snapshot.address_book.extract_actions_modes:
            nodes_map[mode] = []
        nodes_map[Actionables.All] = self.snapshot.get_nodes(
            filter_query=lambda node: all(q(node) for q in actionable_node_queries))
        tb_reachable_nodes = {}
        if self.snapshot.address_book.tb_explore_visited_nodes_path.exists():
            with open(self.snapshot.address_book.tb_explore_visited_nodes_path) as f:
                for line in f.readlines():
                    tb_reachable_node = Node.createNodeFromDict(json.loads(line))
                    corresponding_node = None
                    if tb_reachable_node.xpath in self.snapshot.xpath_to_node:
                        corresponding_node = self.snapshot.xpath_to_node[tb_reachable_node.xpath]
                    elif tb_reachable_node.text or tb_reachable_node.content_desc or tb_reachable_node.resource_id:
                        similar_nodes = self.snapshot.get_nodes(
                            filter_query=lambda node: node.class_name == tb_reachable_node.class_name and
                                                      node.resource_id == tb_reachable_node.resource_id and
                                                      node.content_desc == tb_reachable_node.content_desc and
                                                      node.text == tb_reachable_node.text
                            )
                        if len(similar_nodes) == 1:
                            corresponding_node = similar_nodes[0]
                    if corresponding_node is None:
                        continue
                    if no_ad and corresponding_node.is_ad:
                        continue
                    tb_reachable_nodes[corresponding_node.xpath] = corresponding_node
                    if self.is_xpath_actionable(corresponding_node.xpath):
                        nodes_map[Actionables.TBReachable].append(corresponding_node)

        visited_resource_ids = set()
        for node in nodes_map[Actionables.All]:
            if node.xpath not in tb_reachable_nodes:
                nodes_map[Actionables.TBUnreachable].append(node)
            if not node.important_for_accessibility:
                nodes_map[Actionables.NA11y].append(node)
            if node.resource_id:
                if node.resource_id in visited_resource_ids:
                    continue
                visited_resource_ids.add(node.resource_id)
            nodes_map[Actionables.UniqueResource].append(node)

        nodes_map[Actionables.Spanned] = []
        for node in self.snapshot.get_nodes(filter_query=lambda node: node.clickable_span and not node.clickable and node.text and not node.is_ad):
            nodes_map[Actionables.Spanned].append(node)

        pre_selected = []
        for node in nodes_map[Actionables.UniqueResource]:
            pre_selected.append(node)
        for node in nodes_map[Actionables.TBReachable]:
            if not node.visible:
                continue
            if node.resource_id:
                if node.resource_id in visited_resource_ids:
                    continue
                visited_resource_ids.add(node.resource_id)
            pre_selected.append(node)
        xpath_nums = r'\[\d+\]'
        simplified_pre_selected = defaultdict(int)
        for node in pre_selected:
            simple_xpath = re.sub(xpath_nums, '', node.xpath)
            simplified_pre_selected[simple_xpath] += 1
        selected_simple_xpaths = defaultdict(int)
        for node in pre_selected:
            simple_xpath = re.sub(xpath_nums, '', node.xpath)
            if simple_xpath in simplified_pre_selected and simplified_pre_selected[simple_xpath] > 5:
                if simple_xpath in selected_simple_xpaths and selected_simple_xpaths[simple_xpath] > 3:
                    continue
            selected_simple_xpaths[simple_xpath] += 1
            nodes_map[Actionables.Selected].append(node)
        for mode in self.snapshot.address_book.extract_actions_modes:
            unique_node_map = {}
            for node in nodes_map[mode]:
                unique_node_map[node.xpath] = node
            nodes = list(unique_node_map.values())
            with open(self.snapshot.address_book.extract_actions_nodes[mode], "w") as f:
                for node in nodes:
                    f.write(f"{node.toJSONStr()}\n")
            annotate_elements(self.snapshot.initial_screenshot,
                              self.snapshot.address_book.extract_actions_screenshots[mode],
                              nodes)

    def is_xpath_actionable(self, xpath: str) -> bool:

        while len(xpath) > 1 and xpath[0] == '/':
            if xpath not in self.snapshot.xpath_to_node:
                logger.error(f"The element could not be found in layout! Xpath: {xpath}")
                return False
            node = self.snapshot.xpath_to_node[xpath]
            if is_node_clickable(node):
                # TODO: Maybe we need more checks here
                return True
            xpath = xpath[:xpath.rfind("/")]
        return False
