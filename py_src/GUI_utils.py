import logging
import re
from collections import defaultdict, Counter
from pathlib import Path
from typing import Callable, List, Union, Tuple, Dict
import json
from lxml import etree
import xml.etree.ElementTree  # BlindSimmer

from json_util import JSONSerializable

logger = logging.getLogger(__name__)


def bounds_included(bounds_parent: Tuple[int, int, int, int], bounds_child: Tuple[int, int, int, int]):
    return bounds_child[2] <= bounds_parent[2] and \
           bounds_child[3] <= bounds_parent[3] and \
           bounds_child[1] >= bounds_parent[1] and \
           bounds_child[0] >= bounds_parent[0]


def calculate_overlap(bounds: Tuple[int, int, int, int],
                      bounds1: Tuple[int, int, int, int]) -> Union[Tuple[int, int, int, int], None]:
    dx = min(bounds[2], bounds1[2]) - max(bounds[0], bounds1[0])
    dy = min(bounds[3], bounds1[3]) - max(bounds[1], bounds1[1])

    ov = tuple([max(bounds[0], bounds1[0]), max(bounds[1], bounds1[1]), min(bounds[2], bounds1[2]),
                min(bounds[3], bounds1[3])])
    if dx >= 0 and dy >= 0 and ov[0] < ov[2] and ov[1] < ov[3]:
        return ov
    return None


class Node(JSONSerializable):
    @staticmethod
    def createNodeFromDict(attributes: dict) -> 'Node':
        if attributes is None or len(attributes) == 0:
            return Node()
        return Node(**attributes)

    @staticmethod
    def createNodeFromXmlElement(element: Union[xml.etree.ElementTree.Element, etree.Element]) -> 'Node':
        if element is None:
            return Node()
        node = Node(**element.attrib)
        node.xml_element = element
        return node

    def __init__(self,
                 index: Union[int, str] = -1,
                 text: str = "",
                 class_name: str = "",
                 resource_id: str = "",
                 content_desc: str = "",
                 visible: Union[bool, str] = True,
                 clickable: Union[bool, str] = False,
                 long_clickable: Union[bool, str] = False,
                 checkable: Union[bool, str] = False,
                 checked: Union[bool, str] = False,
                 enabled: Union[bool, str] = False,
                 focusable: Union[bool, str] = False,
                 focused: Union[bool, str] = False,
                 invalid: Union[bool, str] = False,
                 clickable_span: Union[bool, str] = False,
                 context_clickable: Union[bool, str] = False,
                 naf: Union[bool, str] = False,
                 important_for_accessibility: Union[bool, str] = False,
                 bounds: Union[Tuple[int, int, int, int], str] = (0, 0, 0, 0),
                 drawing_order: Union[int, str] = -1,
                 a11y_actions: Union[List[int], str] = None,
                 xpath: str = "",
                 pkg_name: str = "",
                 **kwargs):
        class_name = kwargs.get('class', class_name)
        resource_id = kwargs.get('resource-id', resource_id)
        content_desc = kwargs.get('content-desc', content_desc)
        pkg_name = kwargs.get('package', pkg_name)
        clickable_span = kwargs.get('clickableSpan', clickable_span)
        long_clickable = kwargs.get('long-clickable', long_clickable)
        context_clickable = kwargs.get('contextClickable', context_clickable)
        naf = kwargs.get('NAF', naf)
        important_for_accessibility = kwargs.get('importantForAccessibility', important_for_accessibility)
        a11y_actions = kwargs.get('actionList', a11y_actions)
        drawing_order = kwargs.get('drawingOrder', drawing_order)

        if isinstance(index, str):
            index = int(index)
        if isinstance(visible, str):
            visible = visible == 'true'
        if isinstance(clickable, str):
            clickable = clickable == 'true'
        if isinstance(long_clickable, str):
            long_clickable = long_clickable == 'true'
        if isinstance(checkable, str):
            checkable = checkable == 'true'
        if isinstance(checked, str):
            checked = checked == 'true'
        if isinstance(enabled, str):
            enabled = enabled == 'true'
        if isinstance(focusable, str):
            focusable = focusable == 'true'
        if isinstance(focused, str):
            focused = focused == 'true'
        if isinstance(invalid, str):
            invalid = invalid == 'true'
        if isinstance(clickable_span, str):
            clickable_span = clickable_span == 'true'
        if isinstance(context_clickable, str):
            context_clickable = context_clickable == 'true'
        if isinstance(naf, str):
            naf = naf == 'true'
        if isinstance(important_for_accessibility, str):
            important_for_accessibility = important_for_accessibility == 'true'
        if isinstance(bounds, str):
            bounds = bounds.strip()
            if not re.search(r"\[-?\d+,-?\d+]\[-?\d+,-?\d+]", bounds):
                raise Exception(f"Problem with bounds! {bounds}")
            bounds = tuple([int(x) for x in bounds.replace("][", ",")[1:-1].split(",")])
        if isinstance(drawing_order, str):
            drawing_order = int(drawing_order)
        if a11y_actions is None:
            a11y_actions = []
        elif isinstance(a11y_actions, str):
            a11y_actions = a11y_actions.split("-")
        self.index = index
        self.class_name = class_name
        self.text = '' if text == 'null' else text
        self.resource_id = '' if resource_id == 'null' else resource_id
        self.content_desc = '' if content_desc == 'null' else content_desc
        self.visible = visible
        self.clickable = clickable
        self.long_clickable = long_clickable
        self.checkable = checkable
        self.checked = checked
        self.enabled = enabled
        self.focusable = focusable
        self.focused = focused
        self.invalid = invalid
        self.clickable_span = clickable_span
        self.context_clickable = context_clickable
        self.naf = naf
        self.important_for_accessibility = important_for_accessibility
        self.bounds = bounds
        self.drawing_order = drawing_order
        self.a11y_actions = a11y_actions
        self.pkg_name = '' if pkg_name == 'null' else pkg_name
        self.xpath = xpath
        # --- Latte ----
        # TODO: Move it to another class
        self.located_by = 'xpath'
        self.skip = False
        self.action = 'click'
        # --- Extra ----
        self.xml_element = None
        self.covered = False
        self.is_ad = False

    def is_none(self) -> bool:
        return self.toJSONStr() == Node().toJSONStr()

    def area(self):
        return (self.bounds[2] - self.bounds[0]) * (self.bounds[3] - self.bounds[1])

    def is_valid_bounds(self):
        return self.area() > 0 and \
               (self.bounds[2] - self.bounds[0]) > 0 and \
               (self.bounds[3] - self.bounds[1]) > 0

    def is_practically_invisible(self):
        if self.covered or not self.visible or not self.is_valid_bounds():
            return True
        if self.xml_element is not None:
            if "Layout" in self.class_name or "ViewGroup" in self.class_name:
                return len(self.xml_element.findall('.//node[@visible="true"]')) == 0
        return False

    def belongs(self, pkg_name: str) -> bool:
        return self.pkg_name == pkg_name

    def is_out_of_bounds(self, screen_bounds: Tuple[int, int, int, int]) -> bool:
        [min_x, min_y, max_x, max_y] = screen_bounds
        return ((max_x < self.bounds[0] or self.bounds[0] < min_x) or
                (max_x < self.bounds[2] or self.bounds[2] < min_x) or
                (max_y < self.bounds[1] or self.bounds[1] < min_y) or
                (max_y < self.bounds[3] or self.bounds[3] < min_y))

    def potentially_data(self):
        return self.text or \
               self.content_desc

    def potentially_function(self):
        return self.clickable or \
               self.long_clickable or \
               set(self.a11y_actions).intersection({"16", "32"})

    def practically_equal(self, other: 'Node', excluded_attrs: List[str] = None) -> bool:
        """
        Determines if two nodes are practically equal.
        Some attributes are excluded since they can be flaky or depend on TalkBack's state
        """
        if excluded_attrs is None:
            excluded_attrs = []
        # TODO: not sure if it should be added or be configurable
        excluded_attrs.extend(['focused', 'bounds', 'index', 'drawing_order', 'a11y_actions'])
        return self.toJSONStr(excluded_attrs) == other.toJSONStr(excluded_attrs)

    def toJSONStr(self, excluded_attributes: List[str] = None) -> str:
        if excluded_attributes is None:
            excluded_attributes = []
        excluded_attributes.append('xml_element')
        return super().toJSONStr(excluded_attributes)

    def toJSON(self, excluded_attributes: List[str] = None) -> dict:
        if excluded_attributes is None:
            excluded_attributes = []
        excluded_attributes.append('xml_element')
        return super().toJSON(excluded_attributes)

    def __str__(self):
        return self.toJSONStr(excluded_attributes=['xpath'])


class NodesFactory:
    """
        A factory class which inputs XML layout (either by file or string), then traverse the tree
        and generate a set of Nodes corresponding to XML elements. The traverse can be accompanied by
        passes to augment more information into Nodes. Each pass input the current visiting Node, its
        extra attribute (a dictionary to contain exclusive information for passes), the children, and
        a map from each child node to its extra attribute.
    """

    def __init__(self):
        self.layout = None
        self.passes = []

    def with_layout(self, layout: str) -> 'NodesFactory':
        self.layout = layout
        return self

    def with_layout_path(self, layout_path: Union[str, Path]) -> 'NodesFactory':
        with open(layout_path, "r") as f:
            self.layout = f.read()
        return self

    def with_xpath_pass(self) -> 'NodesFactory':
        """
        Creates xpath attribute for Nodes
        """

        def create_xpath(node: Node,
                         extra: Dict,
                         children_nodes: List[Node],
                         child_to_extras_map: Dict[Node, Dict]) -> None:
            total_class_count = Counter([x.class_name for x in children_nodes])
            class_counter = defaultdict(int)
            for child_node in children_nodes:
                class_counter[child_node.class_name] += 1
                if class_counter[child_node.class_name] == 1 and total_class_count[child_node.class_name] == 1:
                    child_node.xpath = "{}/{}".format(node.xpath,
                                                      child_node.class_name)
                else:
                    child_node.xpath = "{}/{}[{}]".format(node.xpath,
                                                          child_node.class_name,
                                                          class_counter[child_node.class_name])

        self.passes.append(create_xpath)
        return self

    def with_ad_detection(self) -> 'NodesFactory':
        """
            Detecting Ad nodes
        """

        def detect_ad(node: Node,
                      extra: Dict,
                      children_nodes: List[Node],
                      child_to_extras_map: Dict[Node, Dict]) -> None:
            resource_id = node.resource_id
            remaining = "" if len(resource_id.split("/")) < 1 else "/".join(resource_id.split("/")[1:])
            if resource_id.endswith("_ad") \
                    or resource_id.endswith("_ads") \
                    or '_ad_' in resource_id \
                    or resource_id.endswith("Ads") \
                    or remaining.startswith('ad_') \
                    or remaining.startswith('ads'):
                node.is_ad = True
            if not node.is_ad and node.class_name == "android.widget.FrameLayout":
                flag = False
                for child in children_nodes:
                    if child.text == "Test Ad":
                        flag = True
                        break
                if flag:
                    node.is_ad = True
            if node.is_ad:
                for child_node in children_nodes:
                    child_node.is_ad = True

        self.passes.append(detect_ad)
        return self

    def with_covered_pass(self) -> 'NodesFactory':
        """
        Calculates `covered` value for children nodes.
        """
        prefix = self.with_covered_pass.__name__
        covered_bounds_list_attr = f"{prefix}_covered_bounds_list"  # to distinguish with other passes

        def calculate_covered(node: Node,
                              extra: Dict,
                              children_nodes: List[Node],
                              child_to_extras_map: Dict[Node, Dict]) -> None:
            """
            Calculates `covered` value for children nodes. Given the visiting node, and all the covered boxes (bounds)
            which have been drawn before this node (this list is stored in `extra[covered_bounds_list_attr]`),
            It simulates how the existing covered boxes and the order of drawing in children will affect the
            covered bounds of the descendents of the visiting node. If a child node is completely covered by either
            the existing covered bounds (passed from the visiting node) or the new cover bounds (drawn by
            prior siblings), its `covered` attribute becomes true. A covered node pass the covered attribute to its
            children unless they are practically invisible.

            :param node: The visiting node
            :param extra: The extra attributes of the visiting node
            :param children_nodes: The children of the visiting node
            :param child_to_extras_map: A map from children to their extras, this function
                                        uses attribute 'covered_bounds_list_attr'
            """
            for child_node in children_nodes:
                child_to_extras_map[child_node][covered_bounds_list_attr] = []
            if node.covered:
                for child_node in children_nodes:
                    if not child_node.is_practically_invisible():
                        child_node.covered = True
            else:
                covered_bounds_so_far = list(extra.get(covered_bounds_list_attr, []))
                for child_node in sorted(children_nodes, key=lambda x: -x.drawing_order):
                    if child_node.is_practically_invisible():
                        continue
                    for covered_bounds in covered_bounds_so_far:
                        if bounds_included(covered_bounds, child_node.bounds):
                            child_node.covered = True
                            break
                        else:
                            overlap_bounds = calculate_overlap(covered_bounds, child_node.bounds)
                            if overlap_bounds:
                                child_to_extras_map[child_node][covered_bounds_list_attr].append(overlap_bounds)
                    if not child_node.covered:
                        covered_bounds_so_far.append(child_node.bounds)

        self.passes.append(calculate_covered)
        return self

    def build(self) -> List[Node]:
        if not self.layout:
            return []

        def dfs(node: Node, extra: Dict) -> List[Node]:
            nodes = []
            nodes.append(node)
            children_xml_elements = node.xml_element.findall("node")
            children_nodes = [Node.createNodeFromXmlElement(child_element) for child_element in children_xml_elements]
            child_to_extra_map = defaultdict(dict)
            for t_pass in self.passes:
                t_pass(node, extra, children_nodes, child_to_extra_map)
            for child_node in children_nodes:
                nodes.extend(dfs(child_node, child_to_extra_map[child_node]))
            return nodes

        try:
            layout_utf8 = self.layout.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
            dummy_root_xml = etree.fromstring(layout_utf8, parser)
            dummy_root_node = Node.createNodeFromXmlElement(dummy_root_xml)
            dummy_root_node.xpath = f""
            return dfs(dummy_root_node, {})[1:]
        except Exception as e:
            logger.error(f"Exception in building Nodes from Layout: {e}")
        return []


def is_in_same_state_with_nodes(nodes1: List[Node], nodes2: List[Node], extra_excluded_attributes: List[str] = None,
                                package_name: str = None) -> bool:
    filter_queries = [lambda node: not node.is_ad]
    if package_name:
        filter_queries.append(lambda node: node.belongs(package_name))
    nodes1 = [x for x in nodes1 if all(query(x) for query in filter_queries)]
    nodes2 = [x for x in nodes2 if all(query(x) for query in filter_queries)]
    if len(nodes1) == 0 or len(nodes2) == 0:
        return False
    if len(nodes1) != len(nodes2):
        return False
    excluded_attributes = ['xpath', 'naf', 'focused', 'bounds', 'index', 'drawing_order',
                           'a11y_actions', 'invalid']
    if extra_excluded_attributes is not None:
        excluded_attributes.extend(extra_excluded_attributes)
    for node1, node2 in zip(nodes1, nodes2):
        if not node1.practically_equal(node2, excluded_attrs=excluded_attributes):
            return False
    return True


def is_in_same_state_layout(layout1: str, layout2: str, extra_excluded_attributes: List[str] = None,
                            package_name: str = None) -> bool:
    nodes1 = NodesFactory() \
        .with_layout(layout1) \
        .with_xpath_pass() \
        .with_ad_detection() \
        .build()
    nodes2 = NodesFactory() \
        .with_layout(layout2) \
        .with_xpath_pass() \
        .with_ad_detection() \
        .build()
    return is_in_same_state_with_nodes(nodes1, nodes2, extra_excluded_attributes=extra_excluded_attributes,
                                       package_name=package_name)


def is_in_same_state_with_layout_path(layout_path1: Union[Path, str], layout_path2: Union[Path, str],
                                      extra_excluded_attributes: List[str] = None,
                                      package_name: str = None) -> bool:
    nodes1 = NodesFactory() \
        .with_layout_path(layout_path1) \
        .with_xpath_pass() \
        .with_ad_detection() \
        .build()
    nodes2 = NodesFactory() \
        .with_layout_path(layout_path2) \
        .with_xpath_pass() \
        .with_ad_detection() \
        .build()
    return is_in_same_state_with_nodes(nodes1, nodes2, extra_excluded_attributes=extra_excluded_attributes,
                                       package_name=package_name)


def get_xpath_from_xml_element(xml_element):
    def __get_element_class(xml_element):
        # for XPATH we have to count only for nodes with same type!
        length = 0
        index = -1
        if xml_element.getparent() is not None:
            for x in xml_element.getparent().getchildren():
                if xml_element.attrib.get('class', 'NONE1') == x.attrib.get('class', 'NONE2'):
                    length += 1
                if x == xml_element:
                    index = length
        if length > 1:
            return f"{xml_element.attrib.get('class', '')}[{index}]"
        return xml_element.attrib.get('class', '')

    node_class_name = __get_element_class(xml_element)
    path = '/' + node_class_name if node_class_name != "" else ""
    if xml_element.getparent() is not None and xml_element.getparent().attrib.get('class', 'NONE') != 'hierarchy':
        path = get_xpath_from_xml_element(xml_element.getparent()) + path
    return path


def get_element_from_xpath(layout: str, xpath: str) -> Union[etree.ElementTree, None]:
    possible_nodes = get_nodes(layout, filter_query=lambda node: node.xpath == xpath)
    if len(possible_nodes) != 1:
        return None
    return possible_nodes[0].xml_element


def is_clickable_element_or_none(dom: str, xpath: str) -> bool:
    element = get_element_from_xpath(dom, xpath)
    if element is None:
        logger.error(f"The element could not be found in layout! Xpath: {xpath}")
        return True
    while element is not None:
        attrs = dict(element.attrib.items())
        if attrs.get('clickable', 'false') == 'true':
            return True
        element = element.getparent()
    return False


def get_nodes(dom: str, filter_query: Callable[[Node], bool] = None) -> List[Node]:
    """
    Given a DOM of an Android layout, creates the GUI elements that passes the filter query

    :param dom: The DOM structure of the layout
    :param filter_query: An optional function inputs a :class:`etree.Element` and
            returns if the element should be added to the output
    :return: List of GUI elements in `dom` that passes the `filter_query`
    """
    nodes = NodesFactory() \
        .with_layout(dom) \
        .with_xpath_pass() \
        .build()
    if filter_query is None:
        filter_query = lambda x: True

    return [node for node in nodes if filter_query(node)]
    # dom_utf8 = dom.encode('utf-8')
    # parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
    # tree = etree.fromstring(dom_utf8, parser)
    # if tree is None:
    #     return []
    # commands = []
    # for i, x in enumerate(tree.getiterator()):
    #     if filter_query is not None and not filter_query(x):
    #         continue
    #     x_attrs = dict(x.attrib.items())
    #     info = {'resourceId': x_attrs.get('resource-id', ''),
    #             'contentDescription': x_attrs.get('content-desc', ''),
    #             'text': x_attrs.get('text', ''),
    #             'class': x_attrs.get('class', ''),
    #             'xpath': get_xpath_from_xml_element(x),
    #             'located_by': 'xpath',
    #             'skip': False,
    #             'action': 'click',
    #             'naf': x_attrs.get('NAF', False),
    #             'bounds': x_attrs.get('bounds', ""),
    #             'checkable': x_attrs.get('checkable', ''),
    #             'checked': x_attrs.get('checked', ''),
    #             'clickable': x_attrs.get('clickable', ''),
    #             'enabled': x_attrs.get('enabled', ''),
    #             'focusable': x_attrs.get('focusable', ''),
    #             'focused': x_attrs.get('focused', ''),
    #             'visible': x_attrs.get('visible', True),
    #             'actionList': x_attrs.get('actionList', ''),
    #             }
    #     for k in info:
    #         if type(info[k]) == str and len(info[k]) == 0:
    #             info[k] = 'null'
    #     command = json.loads(json.dumps(info))
    #     commands.append(command)
    # return commands


def get_actions_from_layout(layout: str,
                            only_visible: bool = True,
                            use_naf: bool = True) -> List[Node]:
    action_queries = []
    clickable_query = lambda node: node.clickable or \
                                   "16" in node.a11y_actions or \
                                   (node.naf if use_naf else False)
    action_queries.append(clickable_query)
    if only_visible:
        visible_query = lambda node: node.visible
        action_queries.append(visible_query)

    actionable_nodes = get_nodes(layout, filter_query=lambda node: all(q(node) for q in action_queries))
    visited_resource_ids = set()
    unique_resource_actionable_nodes = []
    for node in actionable_nodes:
        if node.resource_id:
            if node.resource_id in visited_resource_ids:
                continue
            visited_resource_ids.add(node.resource_id)
        unique_resource_actionable_nodes.append(node)
    return unique_resource_actionable_nodes
