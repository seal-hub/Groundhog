import json
import logging
from collections import defaultdict

from GUI_utils import NodesFactory
from results_utils import OAC
from snapshot import Snapshot
from task.snapshot_task import SnapshotTask
from utils import annotate_elements

logger = logging.getLogger(__name__)


class OversightStaticTask(SnapshotTask):
    def __init__(self, snapshot: Snapshot):
        super().__init__(snapshot)

    async def execute(self):
        self.snapshot.address_book.initiate_oversight_static_task()
        pkg_name = self.snapshot.address_book.app_name()  # TODO: It's not always correct

        nodes = NodesFactory() \
            .with_layout(self.snapshot.initial_layout) \
            .with_ad_detection() \
            .with_xpath_pass() \
            .with_covered_pass() \
            .build()

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
            annotate_elements(self.snapshot.initial_screenshot,
                              self.snapshot.address_book.get_os_result_path(key, extension='png'),
                              oa_nodes)
            oac_count[key] = len(oa_nodes)
            logger.info(f"{key}: {len(oa_nodes)}")
            with open(self.snapshot.address_book.get_os_result_path(key), "w") as f:
                for node in oa_nodes:
                    if key != OAC.O_AD:
                        node_to_oac_map[node].append(key)
                    f.writelines(f"{node.toJSONStr()}\n")

        annotate_elements(self.snapshot.initial_screenshot,
                          self.snapshot.address_book.get_os_result_path(extension='png'),
                          list(node_to_oac_map.keys()))

        result_path = self.snapshot.address_book.get_os_result_path()
        with open(result_path, "w") as f:
            for node, oacs in node_to_oac_map.items():
                entry = {'node': node.toJSON(), 'OACs': [str(x) for x in oacs]}
                f.write(f"{json.dumps(entry)}\n")

        return list(node_to_oac_map.keys())