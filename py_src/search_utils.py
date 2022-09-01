from typing import List

from GUI_utils import Node


def compare_string(value: str, query: str):
    value = value.strip().lower()
    query = query.strip().lower()
    if query == '~':
        return len(value) == 0
    elif query[0] == '!':
        return query[1:].strip() not in value
    elif query[0] == '"' and query[-1] == '"':
        return query[1:-1] == value
    else:
        return query in value


def compare_bool(value: bool, query: str):
    query = query.strip().lower()
    if query == 'any':
        return True
    return value == (query == 'true')


def compare_int(value: int, query: str):
    query = query.strip().lower()
    if query.startswith('<'):
        return value < int(query[1:])
    elif query.startswith('>'):
        return value > int(query[1:])
    elif query.startswith('<='):
        return value <= int(query[2:])
    elif query.startswith('>='):
        return value >= int(query[2:])
    return value == int(query)


def compare_list(value: List, query: str):
    query = query.strip().lower()
    if query[0] == '!':
        parts = query[1:].split(",")
        for part in parts:
            if part.strip() in value:
                return False
        return True
    parts = query.split(",")
    for part in parts:
        if part.strip() not in value:
            return False
    return True


def contains_node_with_attrs(nodes: List[Node], attrs: List[str], queries: List[str]) -> bool:
    for node in nodes:
        is_satisfied = True
        for (attr, query) in zip(attrs, queries):
            if not query:
                continue  # TODO
            if attr == 'ALL':
                is_satisfied = is_satisfied and query in node.toJSONStr()
            elif attr == 'text':
                is_satisfied = is_satisfied and compare_string(node.text, query)
            elif attr == 'content_desc':
                is_satisfied = is_satisfied and compare_string(node.content_desc, query)
            elif attr == 'class_name':
                is_satisfied = is_satisfied and compare_string(node.class_name, query)
            elif attr == 'resource_id':
                is_satisfied = is_satisfied and compare_string(node.resource_id, query)
            elif attr == 'clickable':
                is_satisfied = is_satisfied and compare_bool(node.clickable, query)
            elif attr == 'checkable':
                is_satisfied = is_satisfied and compare_bool(node.checkable, query)
            elif attr == 'visible':
                is_satisfied = is_satisfied and compare_bool(node.visible, query)
            elif attr == 'enabled':
                is_satisfied = is_satisfied and compare_bool(node.enabled, query)
            elif attr == 'clickable_span':
                is_satisfied = is_satisfied and compare_bool(node.clickable_span, query)
            elif attr == 'invalid':
                is_satisfied = is_satisfied and compare_bool(node.invalid, query)
            elif attr == 'context_clickable':
                is_satisfied = is_satisfied and compare_bool(node.context_clickable, query)
            elif attr == 'long_clickable':
                is_satisfied = is_satisfied and compare_bool(node.long_clickable, query)
            elif attr == 'important_for_accessibility':
                is_satisfied = is_satisfied and compare_bool(node.important_for_accessibility, query)
            elif attr == 'a11y_actions':
                is_satisfied = is_satisfied and compare_list(node.a11y_actions, query)
            elif attr == 'area':
                is_satisfied = is_satisfied and compare_int(node.area(), query)
            elif attr == 'width':
                is_satisfied = is_satisfied and compare_int(node.bounds[2]-node.bounds[0], query)
            elif attr == 'height':
                is_satisfied = is_satisfied and compare_int(node.bounds[3]-node.bounds[1], query)
            if not is_satisfied:
                break
        if is_satisfied:
            return True
    return False