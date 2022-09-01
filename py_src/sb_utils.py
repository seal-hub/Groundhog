import argparse
import json
import logging
from collections import defaultdict
from itertools import cycle
from pathlib import Path
from typing import Union, List, Tuple

from GUI_utils import NodesFactory, Node
from results_utils import OAC, AddressBook, get_snapshot_paths
from utils import annotate_elements

logger = logging.getLogger(__name__)


def statice_analyze(address_book: AddressBook,
                    screenshot_path: Union[str, Path],
                    layout_path: Union[str, Path] = None,
                    layout: str = None) -> List[Node]:
    if isinstance(layout_path, str):
        layout_path = Path(layout_path)
    if isinstance(screenshot_path, str):
        screenshot_path = Path(screenshot_path)

    pkg_name = address_book.app_name()  # TODO: It's not always correct

    node_factory = NodesFactory()
    if layout_path:
        node_factory.with_layout_path(layout_path)
    elif layout:
        node_factory.with_layout(layout)
    else:
        return []
    node_factory.with_ad_detection() \
                .with_xpath_pass() \
                .with_covered_pass()
    nodes = node_factory.build()
    screen_bounds = nodes[0].bounds

    oa_conditions = {
        OAC.P1_BELONGS: lambda node: not node.belongs(pkg_name),
        OAC.P2_OUT_OF_BOUNDS: lambda node: node.is_out_of_bounds(screen_bounds),
        OAC.P3_COVERED: lambda node: node.covered and not node.is_out_of_bounds(screen_bounds),
        OAC.P4_ZERO_AREA: lambda node: node.area() == 0,
        OAC.P5_AINVISIBLE: lambda node: not node.visible and
                                        not node.is_out_of_bounds(screen_bounds) and
                                        node.area() != 0,
        OAC.A2_CONDITIONAL_DISABLED: lambda node: not node.enabled,
        OAC.A3_INCONSISTENT_ABILITIES: lambda node: not node.clickable and "16" in node.a11y_actions,
        OAC.A4_CAMOUFLAGED: lambda node: (node.text == node.content_desc == "") and
                                         node.class_name == "android.widget.TextView" and
                                         node.visible and
                                         not node.is_out_of_bounds(screen_bounds) and
                                         not node.area() == 0,
        OAC.O_AD: lambda node: node.is_ad
    }
    oa_conditions[OAC.A1_PINVISIBLE] = lambda node: any(oa_conditions[oac](node) for oac in OAC if oac.name.startswith("P"))

    node_to_oac_map = defaultdict(list)
    oac_count = {}
    for key, query in oa_conditions.items():
        queries = [query]
        if key.name.startswith("P"):
            queries.append(lambda node: not node.is_ad and node.potentially_data())
        elif key.name.startswith("A"):
            queries.append(lambda node: not node.is_ad and node.potentially_function())
        else:
            queries.append(lambda node: node.potentially_data() or node.potentially_function())
        oa_nodes = [node for node in nodes if all(q(node) for q in queries)]
        annotate_elements(screenshot_path,
                          address_book.get_os_result_path(key, extension='png'),
                          oa_nodes)
        oac_count[key] = len(oa_nodes)
        logger.info(f"{key}: {len(oa_nodes)}")
        with open(address_book.get_os_result_path(key), "w") as f:
            for node in oa_nodes:
                if key != OAC.O_AD:
                    node_to_oac_map[node].append(key)
                f.writelines(f"{node.toJSONStr()}\n")

    annotate_elements(screenshot_path,
                      address_book.get_os_result_path(extension='png'),
                      list(node_to_oac_map.keys()))

    result_path = address_book.get_os_result_path()
    with open(result_path, "w") as f:
        for node, oacs in node_to_oac_map.items():
            entry = {'node': node.toJSON(), 'OACs': [str(x) for x in oacs]}
            f.write(f"{json.dumps(entry)}\n")

    return list(node_to_oac_map.keys())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot-path', type=str, help="Path of the snapshot's result")
    parser.add_argument('--app-path', type=str, help="Path of the app's result")
    parser.add_argument('--result-path', type=str, help="Path of the result's path")
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

    for snapshot_path in get_snapshot_paths(args.result_path, args.app_path, args.snapshot_path):
        address_book = AddressBook(snapshot_path)
        layout_path = address_book.get_layout_path('exp', 'INITIAL', should_exists=True)
        screenshot_path = address_book.get_screenshot_path('exp', 'INITIAL', should_exists=True)
        if layout_path and screenshot_path:
            statice_analyze(layout_path, screenshot_path, address_book)
