import sys
import json
import logging
import subprocess
from typing import Union
from itertools import cycle
from collections import defaultdict
import pathlib
import os
import math
import datetime
from ansi2html import Ansi2HTMLConverter
from json2html import json2html
from flask import Flask, request, jsonify, send_from_directory, render_template, make_response

from consts import BLIND_MONKEY_EVENTS_TAG
from snapshot_search import SnapshotSearchManager, SnapshotSearchQuery

sys.path.append(str(pathlib.Path(__file__).parent.resolve()))
from results_utils import AddressBook, OAC
from post_analysis import do_post_analysis, get_post_analysis, old_report_issues, SUCCESS, TB_FAILURE, REG_FAILURE, \
    XML_PROBLEM \
    , DIFFERENT_BEHAVIOR, UNREACHABLE, POST_ANALYSIS_PREFIX
from action_search import get_search_manager, SearchActionQuery

logger = logging.getLogger(__name__)
flask_app = Flask(__name__, static_url_path='', )

mode_to_repr = defaultdict(lambda: 'UNKNOWN',
                           {
                               'base': 'Initial',
                               'tb_touch': 'TalkBack',
                               'a11y_api': 'A11y API',
                               'touch': 'Touch'
                           })


def fix_path(path: str) -> str:
    return f"../{path}"


def create_snapshot_info(snapshot_path: pathlib.Path) -> Union[dict, None]:
    if not snapshot_path.is_dir():
        return None
    result_path = snapshot_path.parent.parent
    snapshot_name = snapshot_path.name
    address_book = AddressBook(snapshot_path)
    snapshot_info = {}
    count_map = {
        'actions': 0,
        'failure': 0,
        'warning': 0,
        'other': 0,
    }
    analysis_count = 0
    for post_result_path in snapshot_path.iterdir():
        if post_result_path.name.startswith(POST_ANALYSIS_PREFIX):
            analysis_count += 1
            with open(str(post_result_path), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    count_map['actions'] += 1
                    result = json.loads(line)
                    if 10 < result['issue_status'] <= 20:
                        count_map['other'] += 1
                    elif 0 < result['issue_status'] <= 10:
                        count_map['warning'] += 1
                    elif result['issue_status'] < 0:
                        count_map['failure'] += 1

    snapshot_info['id'] = snapshot_name
    snapshot_info['log_path'] = str(snapshot_path.relative_to(result_path.parent)) + ".log"
    if analysis_count == 0:
        snapshot_info['state'] = "Pending" if not address_book.finished_path.exists() else "Unprocessed"
        for key in count_map:
            snapshot_info[key] = f"({snapshot_info['state']})"
    else:
        snapshot_info['state'] = "Processed"
        for key in count_map:
            snapshot_info[key] = math.floor(count_map[key] / analysis_count)
    snapshot_info['last_update'] = datetime.datetime.fromtimestamp(address_book.snapshot_result_path.stat().st_mtime)
    return snapshot_info


def create_app_info(app_path: pathlib.Path) -> Union[dict, None]:
    if not app_path.is_dir():
        return None
    app_name = app_path.name
    snapshots_info = []
    for snapshot_path in app_path.iterdir():
        snapshot_info = create_snapshot_info(snapshot_path)
        if snapshot_info is not None:
            snapshots_info.append(snapshot_info)
    snapshots_info.sort(key=lambda s: s['last_update'], reverse=True)
    app_info = {}
    app_info['name'] = app_name.replace(' ', '_')
    app_info['snapshots'] = snapshots_info
    app_info['has_unprocessed'] = any(s['state'] == 'Unprocessed' for s in snapshots_info)
    app_info['actions'] = sum(
        [0] + [s['actions'] for s in snapshots_info if s['state'] == 'Processed'])
    app_info['failure'] = sum(
        [0] + [s['failure'] for s in snapshots_info if s['state'] == 'Processed'])
    app_info['warning'] = sum(
        [0] + [s['warning'] for s in snapshots_info if s['state'] == 'Processed'])
    app_info['other'] = sum(
        [0] + [s['other'] for s in snapshots_info if s['state'] == 'Processed'])
    app_info['last_update'] = max(s['last_update'] for s in snapshots_info)
    return app_info


def create_step(address_book: AddressBook, static_root_path: pathlib.Path, action: dict,
                action_post_analysis_results: dict, is_sighted: bool) -> dict:
    prefix = "s_" if is_sighted else ""
    step = {}
    step['index'] = action['index']
    step['snapshot_info'] = {
        'result_path': address_book.result_path(),
        'app_name': address_book.app_name(),
        'snapshot_name': address_book.snapshot_name()
    }
    step['action'] = action['element']
    step['action']['node'] = action.get('node', 'null')
    step['tags'] = []
    if address_book.tags_path.exists():
        with open(address_book.tags_path, encoding="utf-8") as f:
            for line in f.readlines():
                tag_info = json.loads(line)
                if tag_info['index'] == action['index'] and tag_info['is_sighted'] == is_sighted:
                    step['tags'].append(tag_info['tag'])
    step['mode_info'] = {}

    modes = ['exp', 'tb', 'reg', 'areg']
    step['xml_similar'] = defaultdict(dict)
    for mode in modes:
        for right_mode in modes:
            if right_mode != mode:
                step['xml_similar'][mode][right_mode] = all(action_post_analysis_results[ana_name]['xml_similar_map'][f"{mode}_{right_mode}"] for ana_name in
                                                        action_post_analysis_results)
            else:
                step['xml_similar'][mode][right_mode] = True
        if mode == 'exp':
            step['mode_info'][f'{mode}_img'] = address_book.get_screenshot_path(f'{prefix}{mode}', action['index'],
                                                                                extension='edited').relative_to(
                static_root_path)
            step['mode_info'][f'{mode}_layout'] = address_book.get_layout_path(f'{prefix}{mode}',
                                                                               action['index']).relative_to(
                static_root_path)
            if not is_sighted:
                step['mode_info'][f'{mode}_log'] = address_book.get_log_path(f'{prefix}{mode}',
                                                                             action['index']).relative_to(
                    static_root_path)
        elif f'{mode}_action_result' in action:
            step['mode_info'][f'{mode}_img'] = address_book.get_screenshot_path(f'{prefix}{mode}',
                                                                                action['index']).relative_to(
                static_root_path)
            step['mode_info'][f'{mode}_log'] = address_book.get_log_path(f'{prefix}{mode}',
                                                                         action['index']).relative_to(static_root_path)
            step['mode_info'][f'{mode}_event_log'] = address_book.get_log_path(f'{prefix}{mode}',
                                                                         action['index'], extension=BLIND_MONKEY_EVENTS_TAG).relative_to(static_root_path)
            step['mode_info'][f'{mode}_layout'] = address_book.get_layout_path(f'{prefix}{mode}',
                                                                               action['index']).relative_to(
                static_root_path)
            step['mode_info'][f'{mode}_result'] = action[f'{mode}_action_result']
        else:
            step['mode_info'][f'{mode}_img'] = '404.png'
            step['mode_info'][f'{mode}_log'] = None
            step['mode_info'][f'{mode}_layout'] = None
            step['mode_info'][f'{mode}_result'] = None
    step['is_sighted'] = is_sighted
    step['status'] = min(
        [100] + [action_post_analysis_results[ana_name]['issue_status'] for ana_name in
                 action_post_analysis_results])
    step['status_messages'] = []
    for ana_name in action_post_analysis_results:
        message = f"{ana_name}: {action_post_analysis_results[ana_name]['message']}"
        for mode, repr in mode_to_repr.items():
            message = message.replace(mode, f"{repr}")
        step['status_messages'].append(message)
    return step

@flask_app.context_processor
def inject_user():
    all_result_paths = []
    parent_path = result_path = pathlib.Path(fix_path(""))
    for result_path in parent_path.iterdir():
        if not result_path.is_dir():
            continue
        if result_path.name.endswith("_results"):
            all_result_paths.append(result_path.name)

    def static_path_fixer(path: Union[str, pathlib.Path], result_path: str) -> str:
        if isinstance(path, pathlib.Path):
            path = str(path)
        return path[path.find(result_path):]

    return dict(all_result_paths=all_result_paths,
                static_path_fixer=static_path_fixer,
                mode_to_repr=mode_to_repr,
                zip=zip,
                oac_names=[oac.name for oac in OAC])


@flask_app.route(f'/v2/static/<path:path>')
def send_result_static_v2(path: str):
    # TODO: Not secure at all
    show_debug = 'debug' in request.args.keys()
    path = pathlib.Path(fix_path(path))
    if not (path.exists()):
        if path.name.endswith(".png"):
            return send_from_directory(fix_path(""), "404.png")
        return "The path is incorrect!"
    if path.name.endswith('.log'):
        with open(path) as f:
            content = ""
            for line in f.readlines():
                if 'DEBUG' not in line or show_debug:
                    content += line
        html_log = Ansi2HTMLConverter().convert(content)
        return html_log
    elif path.name.endswith('.jsonl'):
        content_list = []
        with open(path) as f:
            for line in f.readlines():
                content_list.append(json.loads(line))
        return json2html.convert(content_list)
    elif path.name.endswith('.xml'):
        with open(path) as f:
            content = f.read()
            content = content.replace("&", "&amp;")

        response = make_response(content)
        response.headers['Content-Type'] = 'application/xml'
        return response

    return send_from_directory(path.parent.resolve(), path.name)


@flask_app.route("/")
def homepage():
    return render_template('homepage.html', result_path="EMPTY_results")


@flask_app.route("/v2/<result_path_str>/gh_summary")
def gh_summary(result_path_str: str):
    show_all = request.args.get('all', 'false')
    show_all = show_all == 'true'
    result_path = pathlib.Path(fix_path(result_path_str))
    if not (result_path.is_dir() and result_path.exists()):
        return "The result path is inccorrect!"
    address_books = []
    for app_path in result_path.iterdir():
        if not app_path.is_dir():
            continue
        for snapshot_path in app_path.iterdir():
            if snapshot_path.is_dir():
                address_books.append(AddressBook(snapshot_path))
    return render_template('gh_summary.html', address_books=address_books, result_path=result_path_str, show_all=show_all)


@flask_app.route("/v2/<result_path_str>/")
def report_index_v2(result_path_str: str):
    result_path = pathlib.Path(fix_path(result_path_str))
    if not (result_path.is_dir() and result_path.exists()):
        return "The result path is inccorrect!"
    apps = []
    for app_path in result_path.iterdir():
        app_info = create_app_info(app_path)
        if app_info is None:
            continue
        apps.append(app_info)
    apps.sort(key=lambda a: a['last_update'], reverse=True)
    return render_template('v2_index.html', apps=apps, result_path=result_path_str)


@flask_app.route("/v2/<result_path>/app/<app_name>")
def report_app_v2(result_path: str, app_name: str):
    result_path_str = result_path
    result_path = pathlib.Path(fix_path(result_path))
    if not (result_path.is_dir() and result_path.exists()):
        return "The result path is incorrect!"
    app_result_dir = result_path.joinpath(app_name)
    app = {'name': app_result_dir.name,
           'address_books': [AddressBook(snapshot_path)
                             for snapshot_path in app_result_dir.iterdir()
                             if snapshot_path.is_dir()]}
    return render_template('v2_app.html', app=app, result_path=result_path_str)


@flask_app.route("/v2/<result_path_str>/snapshot_search", methods=['GET', 'POST'])
def snapshot_search(result_path_str: str):
    app_name_field = request.args.get('appName', 'All')
    xml_search_mode = request.args.get('xmlSearchMode', 'ALL')
    xml_search_attrs = request.args.getlist('xmlSearchAttr[]')
    xml_search_fields = request.args.getlist('xmlSearchQuery[]')
    if len(xml_search_fields) == 0 or len(xml_search_fields) != len(xml_search_attrs):
        xml_search_fields = [None]*5
        xml_search_attrs = ['ALL']*5
    snapshot_limit_field = request.args.get('snapshot_limit_field', '10')
    if not snapshot_limit_field.isdecimal():
        snapshot_limit_field = 1000
    snapshot_limit_field = int(snapshot_limit_field)
    result_path = pathlib.Path(fix_path(result_path_str))
    if not (result_path.is_dir() and result_path.exists()):
        return "The result path is incorrect!"
    search_query = SnapshotSearchQuery().set_valid_app(app_name_field)

    search_query.contains_node(attrs=xml_search_attrs, queries=xml_search_fields)

    search_results = SnapshotSearchManager(result_path).search(search_query=search_query)
    app_names = ['All']
    for app_path in result_path.iterdir():
        if not app_path.is_dir():
            continue
        app_names.append(app_path.name)

    return render_template('snapshot_search.html',
                           result_path=result_path_str,
                           results=search_results,
                           snapshot_limit_field=snapshot_limit_field,
                           xml_search_fields=xml_search_fields,
                           xml_search_mode=xml_search_mode,
                           xml_search_attrs=xml_search_attrs,
                           app_name_field=app_name_field,
                           app_names=app_names)


@flask_app.route("/v2/<result_path_str>/search", methods=['GET', 'POST'])
def search_v2(result_path_str: str):
    tb_type = request.args.get('tbType', 'both')
    post_analysis_result = request.args.get('postAnalysisResult', 'ANY')
    one_result_per_snapshot = request.args.get('oneResultPerSnapshot', 'off')
    include_tags_field = request.args.get('includeTags', '')
    exclude_tags_field = request.args.get('excludeTags', '')
    app_name_field = request.args.get('appName', 'All')
    tb_result_field = request.args.get('tbResult', 'ALL')
    touch_result_field = request.args.get('regResult', 'ALL')
    a11y_api_result_field = request.args.get('aregResult', 'ALL')
    summary_names = request.args.getlist('summarySearchName[]')
    summary_values = request.args.getlist('summarySearchValue[]')
    if len(summary_names) == 0 or len(summary_names) != len(summary_values):
        summary_names = ['ANY']*6
        summary_values = [None]*6
    action_attr_names = request.args.getlist('actionSearchAttr[]')
    action_attr_values = request.args.getlist('actionSearchQuery[]')
    if len(action_attr_names) == 0 or len(action_attr_names) != len(action_attr_values):
        action_attr_names = ['ALL']*2
        action_attr_values = [None]*2
    xml_search_mode = request.args.get('xmlSearchMode', 'ALL')
    xml_search_attrs = request.args.getlist('xmlSearchAttr[]')
    xml_search_fields = request.args.getlist('xmlSearchQuery[]')
    if len(xml_search_fields) == 0 or len(xml_search_fields) != len(xml_search_attrs):
        xml_search_fields = [None]*2
        xml_search_attrs = ['ALL']*2
    # xml_search_field = request.args.get('xmlSearchQuery', None)
    # xml_search_attr = request.args.get('xmlSearchAttr', 'ALL')
    left_xml_fields = request.args.getlist('leftXML[]')
    op_xml_fields = request.args.getlist('opXML[]')
    right_xml_fields = request.args.getlist('rightXML[]')
    if len(left_xml_fields) == 0:
        left_xml_fields = ['None'] * 2
        op_xml_fields = ['=', '≠']
        right_xml_fields = ['None'] * 2
    left_screen_fields = request.args.getlist('leftSCREEN[]')
    op_screen_fields = request.args.getlist('opSCREEN[]')
    right_screen_fields = request.args.getlist('rightSCREEN[]')
    if len(left_screen_fields) == 0:
        left_screen_fields = ['None'] * 1
        op_screen_fields = ['=']
        right_screen_fields = ['None'] * 1
    action_limit_field = request.args.get('action_limit_field', '10')
    if not action_limit_field.isdecimal():
        action_limit_field = 10
    action_limit_field = int(action_limit_field)
    snapshot_limit_field = request.args.get('snapshot_limit_field', '1000')
    if not snapshot_limit_field.isdecimal():
        snapshot_limit_field = 1000
    snapshot_limit_field = int(snapshot_limit_field)
    limit_per_snapshot = 1 if one_result_per_snapshot == 'on' else 10000
    include_tags = include_tags_field.split(",")
    exclude_tags = exclude_tags_field.split(",")
    result_path = pathlib.Path(fix_path(result_path_str))
    if not (result_path.is_dir() and result_path.exists()):
        return "The result path is inccorrect!"
    search_query = SearchActionQuery()\
        .post_analysis(post_analysis_result=post_analysis_result)\
        .set_valid_app(app_name_field)\

    # for action_attr, value in zip(action_attr_names, action_attr_fields):
    #     if value:
    #         search_query.contains_action_attr(action_attr, value)
    #
    # for action_attr, value in zip(action_xml_attr_names, action_xml_attr_fields):
    #     if value and value != 'Any':
    #         search_query.contains_action_xml_attr(action_attr, value)

    if len(include_tags) > 0 or len(exclude_tags) > 0:
        search_query.contains_tags(include_tags=include_tags, exclude_tags=exclude_tags)
    if tb_result_field:
        search_query.executor_result('tb', tb_result_field)
    if touch_result_field:
        search_query.executor_result('touch', touch_result_field)
    if a11y_api_result_field:
        search_query.executor_result('a11y_api', a11y_api_result_field)
    if any(action_attr_values):
        search_query.contains_action_with_attrs(attr_names=action_attr_names, attr_queries=action_attr_values)
    if any(xml_search_fields):
        search_query.contains_layout_with_attrs(attr_names=xml_search_attrs, attr_queries=xml_search_fields)
    if any(summary_values):
        search_query.has_summary(summary_names=summary_names, summary_values=summary_values)
    #
    # for (left_xml_field, op_xml_field, right_xml_field) in zip(left_xml_fields, op_xml_fields, right_xml_fields):
    #     if left_xml_field != 'None' and right_xml_field != 'None':
    #         search_query.compare_xml(left_xml_field, right_xml_field, should_be_same=op_xml_field == '=')
    #
    # for (left_screen_field, op_screen_field, right_screen_field) in zip(left_screen_fields, op_screen_fields, right_screen_fields):
    #     if left_screen_field != 'None' and right_screen_field != 'None':
    #         search_query.compare_screen(left_screen_field, right_screen_field, should_be_same=op_screen_field == '=')

    search_results = get_search_manager(result_path).search(search_query=search_query,
                                                            action_limit=action_limit_field,
                                                            action_per_snapshot_limit=limit_per_snapshot)
    all_action_result_count = len(search_results)
    all_snapshots_result_count = len(set([x.address_book.snapshot_name() for x in search_results]))

    app_names = ['All']
    for app_path in result_path.iterdir():
        if not app_path.is_dir():
            continue
        app_names.append(app_path.name)

    return render_template('search.html',
                           result_path=result_path_str,
                           results=search_results,
                           all_action_result_count=all_action_result_count,
                           all_snapshots_result_count=all_snapshots_result_count,
                           action_attr_names=action_attr_names,
                           action_attr_values=action_attr_values,
                           summary_names=summary_names,
                           summary_values=summary_values,
                           # action_attrs=zip(action_attr_names, action_attr_fields),
                           # action_xml_attrs=zip(action_xml_attr_names, action_xml_attr_fields),
                           tb_type=tb_type,
                           tb_result_field=tb_result_field,
                           touch_result_field=touch_result_field,
                           a11y_api_result_field=a11y_api_result_field,
                           post_analysis_result=post_analysis_result,
                           one_result_per_snapshot=one_result_per_snapshot,
                           action_limit_field=action_limit_field,
                           snapshot_limit_field=snapshot_limit_field,
                           include_tags_field=include_tags_field,
                           exclude_tags_field=exclude_tags_field,
                           xml_fields=zip(left_xml_fields, cycle(op_xml_fields), right_xml_fields),
                           screen_fields=zip(left_screen_fields, cycle(op_screen_fields), right_screen_fields),
                           xml_search_fields=xml_search_fields,
                           xml_search_mode=xml_search_mode,
                           xml_search_attrs=xml_search_attrs,
                           app_name_field=app_name_field,
                           app_names=app_names)


@flask_app.route("/v2/<result_path>/app/<app_name>/snapshot/<snapshot_name>/action/<index>/<sighted_str>/diff/<left_mode>/<right_mode>")
def xml_diff_v2(result_path, app_name, snapshot_name, index, sighted_str, left_mode, right_mode):
    is_sighted = sighted_str == "sighted"
    result_path = pathlib.Path(fix_path(result_path))
    if not (result_path.is_dir() and result_path.exists()):
        return f"The result path is incorrect! Result Path: {result_path}"
    snapshot_path = result_path.joinpath(app_name).joinpath(snapshot_name)
    flask_app.logger.info(f"Xml Diff for Snapshot_path: {snapshot_path}, index: {index}, is_sighted: {is_sighted}")
    address_book = AddressBook(snapshot_path)
    prefix = "s_" if is_sighted else ""
    left_xml_path = address_book.get_layout_path(f'{prefix}{left_mode}', index)
    right_xml_path = address_book.get_layout_path(f'{prefix}{right_mode}', index)
    cmd = f"diff --unified {left_xml_path} {right_xml_path}"
    diff_string = subprocess.run(cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8')
    return render_template('xml_diff.html', diff_string=[diff_string])


@flask_app.route("/v2/<result_path>/app/<app_name>/post_analysis")
def post_analysis(result_path, app_name):
    result_path = pathlib.Path(fix_path(result_path)).resolve()
    snapshot_count = do_post_analysis(app_path=pathlib.Path(result_path).joinpath(app_name))
    return jsonify(result=f"{snapshot_count} snapshots of {app_name} are analyzed!")


@flask_app.route("/v2/<result_path>/app/<app_name>/snapshot/<snapshot_name>/action/<index>/tag/<tag>")
def tag_action(result_path, app_name, snapshot_name, index, tag):
    result_path = pathlib.Path(fix_path(result_path)).resolve()
    snapshot_path = result_path.joinpath(app_name).joinpath(snapshot_name)
    if not snapshot_path.is_dir():
        return jsonify(result=False)
    tags = tag.split(',')
    address_book = AddressBook(snapshot_path)
    index = int(index)
    address_book.whelper.add_tag(index, tags)
    return jsonify(result=True)


@flask_app.route("/v2/<result_path>/app/<app_name>/snapshot/<snapshot_name>/note", methods=['POST'])
def snapshot_note(result_path, app_name, snapshot_name):
    result_path = pathlib.Path(fix_path(result_path)).resolve()
    snapshot_path = result_path.joinpath(app_name).joinpath(snapshot_name)
    if not snapshot_path.is_dir():
        return jsonify(result=False)
    address_book = AddressBook(snapshot_path)
    note = request.form.get('snapshot_note', None)
    if note:
        address_book.whelper.update_note(note)
    return jsonify(result=True)


@flask_app.route("/v2/<result_path>/tags")
def tags_list(result_path):
    result_path_str = result_path
    result_path = pathlib.Path(fix_path(result_path)).resolve()
    if not result_path.is_dir():
        return jsonify(result=False)
    tags = set()
    for app_path in result_path.iterdir():
        if not app_path.is_dir():
            continue
        for snapshot_dir in app_path.iterdir():
            if not snapshot_dir.is_dir():
                continue
            address_book = AddressBook(snapshot_dir)
            if not address_book.tags_path.exists():
                continue
            with open(address_book.tags_path, 'r', encoding="utf-8") as f:
                for line in f.readlines():
                    tags.add(json.loads(line)['tag'])
    return render_template('tags.html', result_path=result_path_str, tags=tags)


@flask_app.route("/v2/<result_path>/app/<app_name>/snapshot/<snapshot_name>/report")
def report_v2(result_path, app_name, snapshot_name):
    result_path_str = result_path
    result_path = pathlib.Path(fix_path(result_path))
    if not (result_path.is_dir() and result_path.exists()):
        return "The result path is incorrect!"
    snapshot_path = result_path.joinpath(app_name).joinpath(snapshot_name)
    address_book = AddressBook(snapshot_path)
    tb_steps = []
    errors = []
    error_logs = ""
    # with open(f"{str(snapshot_path)}.log", encoding="utf-8") as f:
    #     for line in f.readlines():
    #         if line.startswith("ERROR:"):
    #             error_logs += line
    post_analysis_results = get_post_analysis(snapshot_path=snapshot_path)
    if len(post_analysis_results['unsighted']) == 0:
        errors.append("No post-analysis result is available!")

    if not address_book.action_path.exists():
        errors.append("Explore data doesn't exist!")
    else:
        explore_json = []
        with open(address_book.action_path, encoding="utf-8") as f:
            for line in f.readlines():
                explore_json.append(json.loads(line))
        for action in explore_json:
            step = create_step(address_book, result_path.parent, action,
                               post_analysis_results['unsighted'][action['index']], is_sighted=False)
            tb_steps.append(step)
    stb_steps = []
    if not address_book.s_action_path.exists():
        errors.append("Sighted TalkBack data doesn't exist!")
    else:
        explore_json = []
        with open(address_book.s_action_path, encoding="utf-8") as f:
            for line in f.readlines():
                explore_json.append(json.loads(line))
        for action in explore_json:
            step = create_step(address_book, result_path.parent, action,
                               post_analysis_results['sighted'][action['index']], is_sighted=True)
            stb_steps.append(step)
    all_steps = {'TalkBack Exploration': tb_steps, 'Sighted TalkBack Checks': stb_steps}
    return render_template('v2_report.html',
                           result_path=result_path_str,
                           app_name=app_name,
                           address_book=address_book,
                           error_logs=error_logs,
                           all_steps=all_steps,
                           name=snapshot_name,
                           errors=errors)


@flask_app.route("/v2/<result_path>/app/<app_name>/snapshot/<snapshot_name>/report_sb")
def report_sb_v2(result_path, app_name, snapshot_name):
    result_path_str = result_path
    result_path = pathlib.Path(fix_path(result_path))
    if not (result_path.is_dir() and result_path.exists()):
        return "The result path is incorrect!"
    snapshot_path = result_path.joinpath(app_name).joinpath(snapshot_name)
    address_book = AddressBook(snapshot_path)
    tb_steps = []
    return render_template('v2_sb_report.html',
                           result_path=result_path_str,
                           app_name=app_name,
                           address_book=address_book,
                           name=snapshot_name)