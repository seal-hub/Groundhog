import argparse
import asyncio
import contextlib
import logging
import json
import pathlib
import sys
from collections import defaultdict, Counter, namedtuple
from typing import Dict

from ppadb.client_async import ClientAsync as AdbClient
from padb_utils import ParallelADBLogger, save_screenshot
from latte_utils import is_latte_live
from latte_executor_utils import talkback_nav_command, talkback_tree_nodes, latte_capture_layout, \
    FINAL_ACITON_FILE, report_atf_issues, execute_command
from GUI_utils import get_actions_from_layout, get_nodes, NodesFactory
from results_utils import OAC, AddressBook
from utils import annotate_elements
from adb_utils import read_local_android_file
from a11y_service import A11yServiceManager
from consts import TB_NAVIGATE_TIMEOUT, DEVICE_NAME, ADB_HOST, ADB_PORT, BLIND_MONKEY_EVENTS_TAG, BLIND_MONKEY_TAG

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def smart__write_open(filename=None):
    if filename and filename != '-':
        fh = open(filename, 'w')
    else:
        fh = sys.stdout

    try:
        yield fh
    finally:
        if fh is not sys.stdout:
            fh.close()

big_gh_data_set = """1_Popular	Instagram	com.instagram.android	298419767	255.0.0.8.119	1000000000	4.1	Social
1_Popular	FacebookLite	com.facebook.lite	298079508	192.0.0.35.123	1000000000	4.1	Social
1_Popular	Wish	com.contextlogic.wish	1682	4.48.3	500000000	4.6	Shopping
1_Popular	Zoom	us.zoom.videomeetings	650907	5.9.6.4756	500000000	4.4	Business
1_Popular	Tubi	com.tubitv	578	4.13.0	100000000	4.8	Entertainment
1_Popular	Shein	com.zzkko	418	7.6.2	100000000	4.8	Shopping
1_Popular	MicrosoftTeams	com.microsoft.teams	2021063722	1416/1.0.0.2021063702	100000000	4.7	Business
3_Latte	Soundcloud	com.soundcloud.android	29090	2020.07.06-release	100000000	4.7	Music
1_Popular	Booking	com.booking	17473	30.9.1	100000000	4.6	Travel
1_Popular	FileMaster	com.root.clean.boost.explorer.filemanager	129	1.2.9	100000000	4.5	Tools
1_Popular	Life360	com.life360.android.safetymapd	241870	21.5.0	100000000	4.5	Lifestyle
2_AndroZoo	YONO	com.sbi.lotusintouch	12350	1.23.50	100000000	4.1	Finance
1_Popular	MovetoiOS	com.apple.movetoios	3011	3.1.2	100000000	2.9	Tools
1_Popular	Bible	kjv.bible.kingjamesbible	315	2.66.1	50000000	4.9	Books
1_Popular	ToonMe	com.vicman.toonmeapp	365	0.6.0	50000000	4.6	Photography
3_Latte	Astro	com.metago.astro	2018041115	6.3.1	50000000	4.4	Tools
1_Popular	OfferUp	com.offerup	140124472	4.8.0	50000000	4.3	Shopping
1_Popular	ESPN	com.espn.score_center	8879	6.46.1	50000000	4	Sports
3_Latte	Yelp	com.yelp.android	21020803	10.21.1-21020803	50000000	4	Food
3_Latte	GeekShopping	com.contextlogic.geek	352	2.3.7	10000000	4.6	Shopping
3_Latte	Dictionary	com.dictionary	297	7.5.36	10000000	4.6	Books
3_Latte	FatSecret	com.fatsecret.android	495	8.7.2.0	10000000	4.6	Health
3_Latte	Cookpad	com.mufumbo.android.recipe.search	30216420	2.164.2.0-android	10000000	4.6	Food
1_Popular	Nike	com.nike.omega	1810041428	2.34.0	10000000	4.5	Shopping
1_Popular	Roku	com.roku.remote	125	7.8.0.644430	10000000	4.4	Entertainment
3_Latte	SchoolPlanner	daldev.android.gradehelper	198	3.15.1	10000000	4.4	Education
1_Popular	NortonVPN	com.symantec.securewifi	12368	3.5.3.12368.ad83ac2	10000000	4.3	Tools
1_Popular	Venmo	com.venmo	3069	9.15.0	10000000	4.2	Finance
3_Latte	Checkout51	com.c51	531	5.3.1	10000000	4.2	Shopping
1_Popular	DigitalClock	com.andronicus.ledclock	89	10.4	10000000	4.1	Tools
3_Latte	Vimeo	com.vimeo.android.videoapp	3390001	3.39.0	10000000	4	Entertainment
1_Popular	Lyft	me.lyft.android	1623222642	6.88.3.1623222642	10000000	3.8	Navigation
1_Popular	Expedia	com.expedia.bookings	21230001	21.23.0	10000000	3.5	Travel
3_Latte	TripIt	com.tripit	2007301330	9.7.0	5000000	4.8	Tavel
3_Latte	ZipRecruiter	com.ziprecruiter.android.release	81	3.0.0	5000000	4.8	Business
2_AndroZoo	To-Do-List	todolist.scheduleplanner.dailyplanner.todo.reminders	1000114	1.01.75.0110	5000000	4.7	Productivity
3_Latte	Feedly	com.devhd.feedly	669	38.0.0	5000000	4.3	News
2_AndroZoo	HTTP-Injector	com.evozi.injector.lite	14220	5.3.0	1000000	4.5	Tools
3_Latte	Fuelio	com.kajda.fuelio	1259	7.6.29	1000000	4.5	Vehicles
3_Latte	BudgetPlanner	com.colpit.diamondcoming.isavemoney	230	6.6.0	1000000	4.4	Finance
3_Latte	TheClock	hdesign.theclock	159	5.2.0	1000000	4.4	Productivity
2_AndroZoo	Estapar	br.com.estapar.sp	707	0.7.6	1000000	4.3	Vehicles
2_AndroZoo	net.inverline.bancosabadell.officelocator.android	net.inverline.bancosabadell.officelocator.android	127399051	22.1.0	1000000	3.6	Finance
3_Latte	BillReminder	com.aa3.easybillsreminder	80	7.8	100000	4.5	Finance
2_AndroZoo	com.abinbev.android.tapwiser.beesMexico	com.abinbev.android.tapwiser.beesMexico	16474	14.5	100000	3.4	Business
2_AndroZoo	com.masterlock.enterprise.vaultenterprise	com.masterlock.enterprise.vaultenterprise	2100007	2.10.0.7	50000	4.2	Lifestyle
2_AndroZoo	com.spinearnpk.pk	com.spinearnpk.pk	95	1.9.5	50000	3.8	Finance
2_AndroZoo	MyCentsys	com.CenturionSystems.MyCentsysPro	126	1.5.0.19	10000	-	House
2_AndroZoo	HManager	com.chsappz.hmanager	69	2.1.3	10000	4.2	Productivity
2_AndroZoo	Greysheet	com.cdn.greysheet	23	5.1	10000	4	Lifestyle
2_AndroZoo	com.cegid.cashmanager	com.cegid.cashmanager	34	1.8.3	5000	-	Business
2_AndroZoo	MGFlasher	com.mgflasher.app	572	320	5000	4.2	Vehicles
2_AndroZoo	com.cryptzone.appgate.xdp	com.cryptzone.appgate.xdp	55325407	5.5.3-25407-release	5000	3.5	Business
2_AndroZoo	Newcatsle	au.gov.nsw.newcastle.app.android	1387	1.8.6	1000	-	Lifestyle
2_AndroZoo	com.freemanhealth.EmployeePortal	com.freemanhealth.EmployeePortal	59	2.11.5	1000	4.2	Tools
2_AndroZoo	io.cordova.myapp6baa2d	io.cordova.myapp6baa2d	10507	1.5.7	100	-	Health
2_AndroZoo	AuditManager	com.focusinformatica.AuditManagerAzimutBenetti	20	2.1.1	50	-	Productivity
2_AndroZoo	com.murder.eyez	com.murder.eyez	32	1.0.2	50	-	Entertainment
2_AndroZoo	com.alphasoft.burn	com.alphasoft.burn	2	1.1	1	-	-"""

gh_data_set = """1_Popular	Instagram	com.instagram.android	298419767	255.0.0.8.119	1000000000	4.1	Social
1_Popular	FacebookLite	com.facebook.lite	298079508	192.0.0.35.123	1000000000	4.1	Social
1_Popular	Shein	com.zzkko	418	7.6.2	100000000	4.8	Shopping
1_Popular	MicrosoftTeams	com.microsoft.teams	2021063722	1416/1.0.0.2021063702	100000000	4.7	Business
2_AndroZoo	YONO	com.sbi.lotusintouch	12350	1.23.50	100000000	4.1	Finance
1_Popular	MovetoiOS	com.apple.movetoios	3011	3.1.2	100000000	2.9	Tools
1_Popular	Bible	kjv.bible.kingjamesbible	315	2.66.1	50000000	4.9	Books
3_Latte	Yelp	com.yelp.android	21020803	10.21.1-21020803	50000000	4	Food
3_Latte	GeekShopping	com.contextlogic.geek	352	2.3.7	10000000	4.6	Shopping
3_Latte	Dictionary	com.dictionary	297	7.5.36	10000000	4.6	Books
3_Latte	FatSecret	com.fatsecret.android	495	8.7.2.0	10000000	4.6	Health
1_Popular	Roku	com.roku.remote	125	7.8.0.644430	10000000	4.4	Entertainment
3_Latte	SchoolPlanner	daldev.android.gradehelper	198	3.15.1	10000000	4.4	Education
1_Popular	NortonVPN	com.symantec.securewifi	12368	3.5.3.12368.ad83ac2	10000000	4.3	Tools
3_Latte	Checkout51	com.c51	531	5.3.1	10000000	4.2	Shopping
1_Popular	DigitalClock	com.andronicus.ledclock	89	10.4	10000000	4.1	Tools
1_Popular	Expedia	com.expedia.bookings	21230001	21.23.0	10000000	3.5	Travel
3_Latte	TripIt	com.tripit	2007301330	9.7.0	5000000	4.8	Tavel
3_Latte	ZipRecruiter	com.ziprecruiter.android.release	81	3.0.0	5000000	4.8	Business
2_AndroZoo	To-Do-List	todolist.scheduleplanner.dailyplanner.todo.reminders	1000114	1.01.75.0110	5000000	4.7	Productivity
3_Latte	Feedly	com.devhd.feedly	669	38.0.0	5000000	4.3	News
2_AndroZoo	HTTP-Injector	com.evozi.injector.lite	14220	5.3.0	1000000	4.5	Tools
3_Latte	BudgetPlanner	com.colpit.diamondcoming.isavemoney	230	6.6.0	1000000	4.4	Finance
2_AndroZoo	Estapar	br.com.estapar.sp	707	0.7.6	1000000	4.3	Vehicles
2_AndroZoo	MyCentsys	com.CenturionSystems.MyCentsysPro	126	1.5.0.19	10000	-	House
2_AndroZoo	HManager	com.chsappz.hmanager	69	2.1.3	10000	4.2	Productivity
2_AndroZoo	Greysheet	com.cdn.greysheet	23	5.1	10000	4	Lifestyle
2_AndroZoo	MGFlasher	com.mgflasher.app	572	320	5000	4.2	Vehicles
2_AndroZoo	Newcatsle	au.gov.nsw.newcastle.app.android	1387	1.8.6	1000	-	Lifestyle
2_AndroZoo	AuditManager	com.focusinformatica.AuditManagerAzimutBenetti	20	2.1.1	50	-	Productivity"""


def convert_installs(i):
    x = Counter(i)
    if '0' not in x:
        return "<10K"
    elif x['0'] == 9:
        return ">1B"
    elif x['0'] >= 6:
        return f">{i[0]}{(x['0']-6)*'0'}M"
    elif x['0'] >= 4:
        return f">{i[0]}{(x['0']-3)*'0'}K"
    else:
        return "<10K"

AppInfo = namedtuple('AppInfo', ['type', 'name', 'pkg_name', 'pkg_str', 'version_code', 'installs', 'installs_str', 'rate', 'category'])
def get_data_set_info() -> Dict[str,AppInfo]:
    apps = {}
    t_counter = defaultdict(int)
    for i, line in enumerate(big_gh_data_set.split("\n")):
        parts = line.split()
        t_type = parts[0].split('_')[1][0]
        t_counter[t_type] += 1
        t_type = f"{t_type}{t_counter[t_type]}"
        name = parts[1]
        pkg_name = parts[2]
        pkg_str = f"\\texttt{{{parts[2][:20]}}}" + ("" if len(parts[2]) <= 20 else "...")
        code = parts[3]
        installs = int(parts[5])
        installs_str = convert_installs(parts[5])
        rate = parts[6]
        category = parts[7]
        apps[pkg_name] = AppInfo(t_type, name, pkg_name, pkg_str, code, installs, installs_str, rate, category)
    return apps


async def execute_latte_command(device, command: str, extra: str):
    padb_logger = ParallelADBLogger(device)
    if command == "tb_a11y_tree":
        windows_info, bm_logs = await talkback_tree_nodes(padb_logger, verbose=True)
        logger.info(f"Windows Info: {json.dumps(windows_info, indent=4)}")
        logger.info(f"Latte Logs: {bm_logs}")
    if command == "capture_layout":
        _, layout = await padb_logger.execute_async_with_log(latte_capture_layout())
        with smart__write_open(extra) as f:
            print(layout, file=f)
    if command == "is_live":
        logger.info(f"Is Latte live? {await is_latte_live()}")
    if command == 'report_atf_issues':
        issues = await report_atf_issues()
        logger.info(f"Reported Issues: {len(issues)}")
        for issue in issues:
            logger.info(f"\tType: {issue['ATFSeverity']} - {issue['ATFType']} - {issue['resourceId']} - {issue['bounds']}")
    if command == "get_actions":  # The extra is the output path
        await save_screenshot(device, extra)
        log_map, layout = await padb_logger.execute_async_with_log(latte_capture_layout())
        if "Problem with XML" in layout:
            logger.error(layout)
            logger.error("Logs: " + log_map)
            return
        actions = get_actions_from_layout(layout)
        annotate_elements(extra, extra, actions, outline=(255, 0, 255), width=15, scale=5)
    if command == "list_CI_elements":
        log_map, layout = await padb_logger.execute_async_with_log(latte_capture_layout())
        if "Problem with XML" in layout:
            logger.error(layout)
            logger.error("Logs: " + log_map)
            return
        ci_elements = get_nodes(layout,
                                filter_query=lambda x: not x.visible)
                                # (x.clickable or '16' in x.a11y_actions) and not x.visible)

        logger.info(f"#CI Elements: {len(ci_elements)}")
        for index, element in enumerate(ci_elements):
            logger.info(f"\tCI Elements {index}: {element}")
    if command == "click_CI_element":
        log_map, layout = await padb_logger.execute_async_with_log(latte_capture_layout())
        if "Problem with XML" in layout:
            logger.error(layout)
            logger.error("Logs: " + log_map)
            return
        ci_elements = get_nodes(layout,
                                filter_query=lambda x: not x.visible)
                                # (x.clickable or '16' in x.a11y_actions) and not x.visible)
        index = int(extra)
        logger.info(f"Target CI Elements #{index}: {ci_elements[index]}")
        tags = [BLIND_MONKEY_TAG, BLIND_MONKEY_EVENTS_TAG]
        log_message_map, result = await padb_logger.execute_async_with_log(
            execute_command(json.dumps(ci_elements[index]), executor_name='areg'), tags=tags)
        logger.info(f"Result: {result}")
        for tag, value in log_message_map.items():
            logger.info(f"Log --- {tag} --------")
            logger.info(value)

    if command.startswith("nav_"):
        await A11yServiceManager.setup_latte_a11y_services(tb=True)
        await talkback_nav_command(command[len("nav_"):])
        next_command_json = await read_local_android_file(FINAL_ACITON_FILE, wait_time=TB_NAVIGATE_TIMEOUT)
        logger.info(f"Nav Result: '{next_command_json}'")
    if command.startswith("write_nodes"):
        layout_path = extra
        nodes = NodesFactory() \
            .with_layout_path(layout_path) \
            .with_xpath_pass() \
            .with_ad_detection() \
            .with_covered_pass() \
            .build()
        for node in nodes:
            if node.covered:
                logger.info(f"Covered Node: {node.covered}  {node.is_ad}")


    if command == "gh_latex_main":
        result_path = pathlib.Path(extra)
        if not result_path.is_dir():
            logger.error("The result path doesn't exist")
            return
        issue_names = ["loc_issue", "tb_act_issue", "api_act_issue", "total_issue"]
        all_results = defaultdict(int)
        app_infos = get_data_set_info()
        COLORED_CELL = "\\cellcolor{LightCyan}"
        for pkg_name, app_info in app_infos.items():
            app_path = result_path.joinpath(pkg_name)
            if not app_path.exists() or not app_path.is_dir():
                continue
            if "au.gov.nsw." in app_path.name:
                continue
            if "com.zzkk" in app_path.name:
                continue
            if "com.life360.android.safetymapd" in app_path.name:
                continue
            if "com.roku.remote" in app_path.name:
                continue
            if "com.evozi.injector.lite" in app_path.name:
                continue
            # app_row = "\\texttt{" + app_path.name[:15] + "}" + ("..." if len(app_path.name) > 15 else "")
            all_results["app_count"] += 1
            # app_row = f"{app_info.type} & {app_info.name}  & {app_info.version_code} & {app_info.category} & {app_info.installs_str}"
            app_row = f"{app_info.type} & {app_info.name}   & {app_info.category} & {app_info.installs_str}"
            result = defaultdict(int)
            atf_count = 0
            for s_index, snapshot_path in enumerate(app_path.iterdir()):
                if not snapshot_path.is_dir():
                    continue
                address_book = AddressBook(snapshot_path)
                if address_book.whelper.is_snapshot_ignored():
                    continue

                result["snapshot_count"] += 1
                result["total_actions"] += address_book.whelper.get_action_count()
                result["gh_actions"] += address_book.whelper.get_actual_action_count()
                snapshot_summary = address_book.whelper.oracle()
                all_results['total_time'] += snapshot_summary["total_time"] if ("us.zoom" not in app_path.name) else 3000
                all_results['actions_time'] += snapshot_summary["actions_time"] if ("us.zoom" not in app_path.name) else 3000 - snapshot_summary["explore_time"]
                all_results['explore_time'] += snapshot_summary["explore_time"]
                all_results['direct_time'] += snapshot_summary["direct_time"]
                result["sa_verified_issues"] += snapshot_summary["sa_verified_issues"]
                for issue in issue_names:
                    result[issue] += snapshot_summary[issue]
                    result[f"tp_{issue}"] += snapshot_summary[f"tp_{issue}"]
                atf_count += address_book.whelper.get_atf_count()
            if result["snapshot_count"] != 5:
                logger.warning(f"App {pkg_name} has {result['snapshot_count']} snapshots!")
            app_row += f"& {result['total_actions']} "  # Total Actions
            app_row += f"& {result['gh_actions']} "  # Total Actions
            all_results['atf'] += atf_count
            for val in ["snapshot_count", "sa_verified_issues", "total_actions", "gh_actions"]:
                all_results[val] += result[val]
            for issue in issue_names:
                all_results[issue] += result[issue]
                all_results[f"tp_{issue}"] += result[f"tp_{issue}"]
                app_row += f"& {result[issue]} " # Issues
                if result['tp_'+issue] > 0:
                    app_row += f"& {COLORED_CELL}\\textbf{{{result['tp_'+issue]}}} "  # TP
                else:
                    app_row += f"& {result['tp_'+issue]} "  # TP
                if issue == 'api_act_issue':
                    app_row += f"& {result['sa_verified_issues']} "  # SA_Verified
            app_row += f"& {atf_count} "  # ATF
            app_row += "\\\\ \n"
            app_row += "\hline \n"
            print(app_row)
        last_row = "\\multicolumn{4}{|c|}{Total} "
        last_row += f"& {all_results['total_actions']} & {all_results['gh_actions']}"  # ATF
        for issue in issue_names:
            last_row += f"& {all_results[issue]} & {all_results['tp_'+issue]}"
            if issue == 'api_act_issue':
                last_row += f"& {all_results['sa_verified_issues']}"
        last_row += f"& {all_results['atf']} "  # ATF
        last_row += "\\\\\n"
        last_row += "\\hline\n"
        print(last_row)
        last_row = "\\multicolumn{6}{|c|}{Precision} "
        for issue in issue_names:
            last_row += "& \\multicolumn{2}{c|}{"+f"{(all_results['tp_'+issue]/all_results[issue]):.2f}" +"}"
            if issue == 'api_act_issue':
                last_row += "& "
        last_row += "&\\\\\n"
        print(last_row)
        for val in ["total_actions", "snapshot_count", "app_count"]:
            logger.info(f"{val}: #{all_results[val]} Average: {all_results['total_time']/all_results[val]:.2f}")
            logger.info(f"{val}: Explore Opt: {all_results['explore_time']/all_results[val]:.2f}  Reg: {all_results['direct_time']/all_results[val]:.2f}")
            logger.info(f"{val}: Action {all_results['actions_time']/all_results[val]:.2f}")

    if command == "gh_atf":
        result_path = pathlib.Path(extra)
        if not result_path.is_dir():
            logger.error("The result path doesn't exist")
            return
        atf_types = defaultdict(set)
        atf_types_to_snapshot = defaultdict(set)
        for app_path in result_path.iterdir():
            if not app_path.is_dir():
                continue
            for snapshot_path in app_path.iterdir():
                if not snapshot_path.is_dir():
                    continue
                address_book = AddressBook(snapshot_path)
                if address_book.perform_actions_atf_issues_path.exists():
                    with open(address_book.perform_actions_atf_issues_path) as f:
                        for line in f.readlines():
                            part = json.loads(line)
                            t = part['ATFType']
                            atf_types[t].add(app_path.name)
                            atf_types_to_snapshot[t].add(snapshot_path.name)
        for tt, names in atf_types.items():
            print(f"{tt}: {len(names)}")
            if len(names) < 3:
                for name in atf_types_to_snapshot[tt]:
                    print("\t", name)




    if command == "os_empirical":
        result_path = pathlib.Path(extra)
        if not result_path.is_dir():
            logger.error("The result path doesn't exist")
            return
        oac_names = []
        for w in ['A', 'P']:
            oac_names.extend([oac.name for oac in OAC if oac.name.startswith(w)])
        oac_count = defaultdict(int)
        total_nodes = 0
        total_oaes = 0
        total_screen_with_oaes = 0
        total_app_with_oaes = 0
        for app_path in result_path.iterdir():
            if not app_path.is_dir():
                continue
            app_oae = 0
            for snapshot_path in app_path.iterdir():
                if not snapshot_path.is_dir():
                    continue
                address_book = AddressBook(snapshot_path)
                with open(address_book.get_layout_path(AddressBook.BASE_MODE, AddressBook.INITIAL)) as f:
                    total_nodes += f.read().count("</node>")
                has_oac = 0
                for oac in oac_names:
                    oacs = address_book.get_oacs(oac=oac)
                    if len(oacs) > 0:
                        has_oac += 1
                        oac_count[oac] += 1
                oacs = len(address_book.get_oacs())
                app_oae += oacs
                if oacs > 0:
                    total_screen_with_oaes += 1
                total_oaes += oacs
            if app_oae > 0:
                total_app_with_oaes += 1


        for k, v in oac_count.items():
            print(f"{k}: {v}")
        print(f"Nodes: {total_nodes}, OAEs: {total_oaes}, ScreenWithOAEs: {total_screen_with_oaes}, AppsWithOAEs: {total_app_with_oaes}")




    if command == "os_n2_rq1":
        result_path = pathlib.Path(extra)
        if not result_path.is_dir():
            logger.error("The result path doesn't exist")
            return
        locker_pkgs = [".".join(x.strip().split(".")[:-1]) for x in """
        com.netqin.ps.apk
        com.domobile.applockwatcher.apk
        com.alpha.applock.apk
        com.sp.protector.free.apk
        com.thinkyeah.smartlockfree.apk
        com.litetools.applockpro.apk
        com.gamemalt.applocker.apk
        com.ammy.applock.apk
        com.gsmobile.applock.apk
        me.ibrahimsn.applock.apk
        MISSING.apk
        com.saeed.applock.apk
        com.applocklite.fingerprint.apk
        com.mms.applock.apphidder.apk
        app.lock.hidedata.cleaner.filetransfer.apk
        """.split("\n") if len(x) > 0]
        latte_pkgs = [".".join(x.strip().split(".")[:-1]) for x in """
        com.c51.apk
        com.fatsecret.android.apk
        com.colpit.diamondcoming.isavemoney.apk
        com.tripit.apk
        com.contextlogic.geek.apk
        com.yelp.android.apk
        com.devhd.feedly.apk
        com.ziprecruiter.android.release.apk
        com.dictionary.apk
        daldev.android.gradehelper.apk
        """.split("\n") if len(x) > 0]
        other_pkgs = [".".join(x.strip().split(".")[:-1]) for x in """
        """.split("\n") if len(x) > 0]
        oac_names = {}
        for w in ['A', 'P']:
            oac_names[w] = {oac.name: oac for oac in OAC if oac.name.startswith(w)}
        header = "App & Snapshot & \#Nodes & \#P Smell & \#A Smell & Smell Reduction & Smell Precision & \#P TBR & \#P APIR &  \#A TBA & \#A APIA & OAE Reduction & OAE Precision \\\\" \
                 +"\hline" \
                 + "\n"
        print(header)
        csv_data = [("App", "Snapshot", "Nodes", "PSmell", "ASmell", "PTBR", "ATBA", "AAPIA")]
        for app_names in [locker_pkgs, latte_pkgs, other_pkgs]:
            for app_name in app_names:
                if not app_name:
                    continue
                app_path = result_path.joinpath(app_name)
                if not app_path.exists() or not app_path.is_dir():
                    app_row = "\multirow{1}{*}{\\texttt{" + app_path.name[:15] + "}" + ("..." if len(app_path.name) > 15 else "") + "} "
                    app_row += "& - & - & - & - & - & - & - & - & - & - & - & - \\\\ \n"
                    app_row += "\hline \n"
                    print(app_row)
                    continue
                snapshot_paths = []
                for s_index, snapshot_path in enumerate(app_path.iterdir()):
                    if not snapshot_path.is_dir():
                        continue
                    snapshot_paths.append(snapshot_path)
                snapshot_count = len(snapshot_paths)
                if snapshot_count == 0:
                    app_row = "\multirow{1}{*}{\\texttt{" + app_path.name[:15] + "}" + ("..." if len(app_path.name) > 15 else "") + "} "
                    app_row += "& - & - & - & - & - & - & - & - & - & - & - & - \\\\ \n"
                    app_row += "\hline \n"
                    print(app_row)
                    continue
                app_row = "\multirow{" + str(snapshot_count) + "}{*}{\\texttt{" + app_path.name[:15] + "}" + ("..." if len(app_path.name) > 15 else "") + "} "
                s_index = 0
                for snapshot_path in sorted(snapshot_paths, key=lambda x: x.name):
                    s_index += 1
                    app_row += f"& {s_index} "  # Scenario
                    address_book = AddressBook(snapshot_path)
                    with open(address_book.get_layout_path("exp", "INITIAL")) as f:
                        number_of_nodes = f.read().count("</node>")
                    app_row += f"& {number_of_nodes} "  # Nodes
                    smells = {'P': [], 'A': []}
                    all_smells = set()
                    all_ope = set()
                    for w in ['A', 'P']:
                        for oac in oac_names[w]:
                            for oac_node, info in address_book.get_oacs_with_info(oac).items():
                                smells[w].append((oac_node, info))
                                all_smells.add(oac_node.xpath)
                                if info['tbr'] or info['tba'] or info['apia']:
                                    all_ope.add(oac_node.xpath)
                    app_row += f"& {len(smells['P'])} "  # P Smell
                    app_row += f"& {len(smells['A'])} "  # A Smell
                    if number_of_nodes == 0:
                        number_of_nodes = 1
                    app_row += f"& {(len(all_smells) / number_of_nodes):.2f} "  # Smell Reduction
                    app_row += "& - "  # Smell Precision
                    oae_tbr = len([s for s in smells['P'] if s[1]['tbr'] is not None])
                    app_row += f"& {len(smells['P'])} "  # P APIR
                    oae_tba = len([s for s in smells['A'] if s[1]['tba'] is not None])
                    oae_apia = len([s for s in smells['A'] if s[1]['apia'] is not None])
                    app_row += f"& {oae_tbr} & {oae_tba} & {oae_apia} "  # TBR TBA APIA
                    app_row += f"& {(len(all_ope) / number_of_nodes):.2f} "  # OAE Reduction
                    app_row += "& - "  # OAE Precision
                    app_row += "\\\\ \n"
                    csv_data.append((app_path.name,
                                     s_index,
                                     number_of_nodes,
                                     len(smells['P']),
                                     len(smells['A']),
                                     oae_tbr,
                                     oae_tba,
                                     oae_apia
                                     ))
                app_row += "\hline \n"
                print(app_row)
            print("\hline \n")
        logger.info("\n".join([",".join([str(x) for x in row]) for row in csv_data]))


    if command == "os_new_rq1":
        result_path = pathlib.Path(extra)
        if not result_path.is_dir():
            logger.error("The result path doesn't exist")
            return

        p_oac_names = {oac.name: oac for oac in OAC if oac.name.startswith("P")}
        a_oac_names = {oac.name: oac for oac in OAC if oac.name.startswith("A")}
        header = "\multirow{2}{*}{App} & \multirow{2}{*}{\\rrot{Snap}} & \multirow{2}{*}{\\rrot{\#Node}} " \
                 + " ".join(f"& \multicolumn{{2}}{{c|}}{{\#{oac_name[:2]}}}" for oac_name in p_oac_names) \
                 + " ".join(f"& \multicolumn{{3}}{{c|}}{{\#{oac_name[:2]}}}" for oac_name in a_oac_names) \
                 + "& \multicolumn{2}{c|}{$P_P$} & \multicolumn{2}{c|}{$P_P$} \\\\" \
                 + "\n" \
                 + f"\cline{{4-{4+len(p_oac_names)*2+len(a_oac_names)*3+2*2-1}}}" \
                 + "\n" \
                 + "& & " \
                 + "& \\rrot{All\\,} & \\rrot{TB\\,} " * len(p_oac_names) \
                 + "& \\rrot{All\\,} & \\rrot{TB\\,} & \\rrot{API\\,}" * len(a_oac_names) \
                 + "& \\rrot{TB\\,} & \\rrot{API\\,} " * 2 \
                 + "\\\\" \
                 + "\n" \
                 +"\hline" \
                 + "\n"
        print(header)
        for app_path in result_path.iterdir():
            if not app_path.is_dir():
                continue

            snapshot_paths = []
            for s_index, snapshot_path in enumerate(app_path.iterdir()):
                if not snapshot_path.is_dir():
                    continue
                snapshot_paths.append(snapshot_path)
            snapshot_count = len(snapshot_paths)
            app_row = "\multirow{" + str(snapshot_count) + "}{*}{" + app_path.name.split('.')[1][:3] + "} "
            s_index = 0
            for snapshot_path in sorted(snapshot_paths, key=lambda x: x.name):
                s_index += 1
                app_row += f"& {s_index} "  # Scenario
                address_book = AddressBook(snapshot_path)
                with open(address_book.get_layout_path("exp", "INITIAL")) as f:
                    number_of_nodes = f.read().count("</node>")
                app_row += f"& {number_of_nodes} "  # Nodes
                for oac in p_oac_names:
                    oac_with_info = address_book.get_oacs_with_info(oac)
                    number_of_oacs = len(oac_with_info)
                    tbr = len([_ for _,info in oac_with_info.items() if info['tbr'] is not None])
                    app_row += f"& {number_of_oacs} & {tbr} "
                for oac in a_oac_names:
                    oac_with_info = address_book.get_oacs_with_info(oac)
                    number_of_oacs = len(oac_with_info)
                    tba = len([_ for _,info in oac_with_info.items() if info['tba'] is not None])
                    apia = len([_ for _,info in oac_with_info.items() if info['apia'] is not None])
                    app_row += f"& {number_of_oacs} & {tba} & {apia} "
                app_row += "& - & - " * 2  # Snapshot Precision
                # if s_index == 1:
                #     app_row += "\multirow{" + str(snapshot_count) + "}{*}{-} "
                app_row += "\\\\ \n"
            app_row += "\hline \n"
            print(app_row)

    if command == "os_rq1":
        result_path = pathlib.Path(extra)
        if not result_path.is_dir():
            logger.error("The result path doesn't exist")
            return

        oac_names = [oac.name for oac in OAC if oac != oac.O_AD]
        oac_count = len(oac_names)
        header = "\multirow{2}{*}{App} & \multirow{2}{*}{Scenario} & \multirow{2}{*}{\#Nodes} " \
                 + " ".join(f"& \multicolumn{{2}}{{c|}}{{\#{oac_name[:3]}}}" for oac_name in ['All'] + oac_names) \
                 + "& \multicolumn{2}{c|}{Precision} \\\\" \
                 + "\n" \
                 + f"\cline{{4-{4+(oac_count+2)*2-1}}}" \
                 + "\n" \
                 + "& & {} & Scenario & App \\\\".format("& All & TP " * (oac_count+1)) \
                 + "\n" \
                 +"\hline" \
                 + "\n"
        print(header)
        for app_path in result_path.iterdir():
            if not app_path.is_dir():
                continue

            snapshot_paths = []
            for s_index, snapshot_path in enumerate(app_path.iterdir()):
                if not snapshot_path.is_dir():
                    continue
                snapshot_paths.append(snapshot_path)
            snapshot_count = len(snapshot_paths)
            app_row = "\multirow{" + str(snapshot_count) + "}{*}{" + app_path.name.split('.')[1] + "} "
            s_index = 0
            for snapshot_path in sorted(snapshot_paths, key=lambda x: x.name):
                s_index += 1
                app_row += f"& {s_index} "  # Scenario
                address_book = AddressBook(snapshot_path)
                with open(address_book.get_layout_path("exp", "INITIAL")) as f:
                    number_of_nodes = f.read().count("</node>")
                app_row += f"& {number_of_nodes} "  # Nodes
                for oac in ['oacs'] + oac_names:
                    number_of_oacs = len(address_book.get_oacs(oac))
                    app_row += f"& {number_of_oacs} & - "
                app_row += "& - &"  # Snapshot Precision
                if s_index == 1:
                    app_row += "\multirow{" + str(snapshot_count) + "}{*}{-} "
                app_row += "\\\\ \n"
            app_row += "\hline \n"
            print(app_row)

    if command == "os_rq2":
        result_path = pathlib.Path(extra)
        if not result_path.is_dir():
            logger.error("The result path doesn't exist")
            return
        header = "App & Scenario & \#Nodes & \#TB Reachable & \#All OA & \#OA TB Reachable & \#TB Actionable & \#API Actionable \\\\ \n"
        header += "\hline \n"
        print(header)
        for app_path in result_path.iterdir():
            if not app_path.is_dir():
                continue

            snapshot_paths = []
            for s_index, snapshot_path in enumerate(app_path.iterdir()):
                if not snapshot_path.is_dir():
                    continue
                snapshot_paths.append(snapshot_path)
            snapshot_count = len(snapshot_paths)
            app_row = "\multirow{" + str(snapshot_count) + "}{*}{" + app_path.name.split('.')[1] + "} "
            s_index = 0
            for snapshot_path in sorted(snapshot_paths, key=lambda x: x.name):
                s_index += 1
                app_row += f"& {s_index} "  # Scenario
                address_book = AddressBook(snapshot_path)
                with open(address_book.get_layout_path("exp", "INITIAL")) as f:
                    number_of_nodes = f.read().count("</node>")
                app_row += f"& {number_of_nodes} "  # Nodes
                tb_reachable_xpaths = set()
                with open(address_book.visited_elements_path) as f:
                    for res in f.readlines():
                        element = json.loads(res)['element']
                        tb_reachable_xpaths.add(element['xpath'])
                app_row += f"& {len(tb_reachable_xpaths)} "  # TB Reachable
                oac_xpaths = set()
                for node in address_book.get_oacs():
                    oac_xpaths.add(node.xpath)
                app_row += f"& {len(oac_xpaths)} "  # OACs
                app_row += f"& {len(oac_xpaths.intersection(tb_reachable_xpaths))} "  # OAC TB Reachable
                tb_actions_xpaths = set()
                api_actions_xpaths = set()
                with open(address_book.action_path) as f:
                    for res in f.readlines():
                        res = json.loads(res)
                        with open(address_book.get_log_path('tb', res['index'], extension=BLIND_MONKEY_EVENTS_TAG)) as f2:
                            if "TYPE_VIEW_CLICKED" in f2.read():
                                tb_actions_xpaths.add(res['element']['xpath'])
                        with open(address_book.get_log_path('areg', res['index'], extension=BLIND_MONKEY_EVENTS_TAG)) as f2:
                            if "TYPE_VIEW_CLICKED" in f2.read():
                                api_actions_xpaths.add(res['element']['xpath'])
                app_row += f"& {len(tb_actions_xpaths)} "  # TB Actions
                app_row += f"& {len(api_actions_xpaths)} "  # API Actions
                app_row += "\\\\ \n"
            app_row += "\hline \n"
            print(app_row)



if __name__ == "__main__":
    run_local = False
    device = None
    if run_local:
        command = "os_n2_rq1"
        extra = "../dev_results"
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('--command', type=str, help='The command sending to Latte')
        parser.add_argument('--extra', type=str, default="", help='The extra information sent to Latte')
        parser.add_argument('--device', type=str, default=DEVICE_NAME, help='The device name')
        parser.add_argument('--adb-host', type=str, default=ADB_HOST, help='The host address of ADB')
        parser.add_argument('--adb-port', type=int, default=ADB_PORT, help='The port number of ADB')
        args = parser.parse_args()
        command = args.command
        extra = args.extra
        logging.basicConfig(level=logging.DEBUG)
        try:
            client = AdbClient(host=args.adb_host, port=args.adb_port)
            device = asyncio.run(client.device(args.device))
            logger.debug(f"Device {device.serial} is connected!")
        except Exception as e:
            logger.error(f"The device is not connected to {args.device}")
            device = None

    if command:
        asyncio.run(execute_latte_command(device, command, extra))
