import sys
from pathlib import Path
import argparse
import asyncio
import logging
from consts import DEVICE_NAME, ADB_HOST, ADB_PORT
from ppadb.client_async import ClientAsync as AdbClient
from results_utils import AddressBook, read_all_visited_elements_in_app
from logger_utils import ColoredFormatter
from bm_snapshotmanager import BM_SnapshotManager

logger = logging.getLogger(__name__)


def analyze_snapshot(device,
                     snapshot_path: Path,
                     is_oversight: bool,
                     directional_action_limit: int,
                     point_action_limit: int,
                     only_explore:bool,
                     only_action:bool,
                     is_instrumented: bool):
    visited_elements_in_app = read_all_visited_elements_in_app(snapshot_path.parent)
    logger.info(f"There are {len(visited_elements_in_app)} already visited elements in this app!")
    address_book = AddressBook(snapshot_path)
    snapshot = BM_SnapshotManager(snapshot_path.name, address_book,
                                  visited_elements_in_app=visited_elements_in_app,
                                  is_oversight=is_oversight,
                                  instrumented_log=is_instrumented,
                                  directional_action_limit=directional_action_limit,
                                  point_action_limit=point_action_limit,
                                  device=device)
    if only_explore:
        asyncio.run(snapshot.directed_explore())
    elif only_action:
        asyncio.run(snapshot.point_action())
        open(address_book.finished_path, "w").close()
    else:
        success_explore = asyncio.run(snapshot.directed_explore_action())
        if not success_explore:
            logger.error("Problem with explore!")
            return
        asyncio.run(snapshot.sighted_explore_action())

        open(address_book.finished_path, "w").close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=str, required=True, help='Name of the snapshot on the running AVD')
    parser.add_argument('--output-path', type=str, required=True, help='The path that outputs will be written')
    parser.add_argument('--app-name', type=str, required=True, help='Name of the app under test')
    parser.add_argument('--oversight', action='store_true', help='Evaluating Oversight')
    parser.add_argument('--only-explore', action='store_true', help='Only directionally explore, no action')
    parser.add_argument('--only-action', action='store_true', help='Only performing action, no explore')
    parser.add_argument('--dir-action-limit', type=int, default=100, help='Max number of directional reachable actions')
    parser.add_argument('--point-action-limit', type=int, default=100, help='Max number of point actions')
    parser.add_argument('--device', type=str, default=DEVICE_NAME, help='The device name')
    parser.add_argument('--adb-host', type=str, default=ADB_HOST, help='The host address of ADB')
    parser.add_argument('--adb-port', type=int, default=ADB_PORT, help='The port number of ADB')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--instrumented', action='store_true', help='Indicates the app is instrumented, will store logs')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    app_result_path = Path(args.output_path).joinpath(args.app_name)
    snapshot_result_path = app_result_path.joinpath(args.snapshot)
    if not snapshot_result_path.exists():
        snapshot_result_path.mkdir(parents=True)
    log_path_name = args.snapshot
    if args.only_explore:
        log_path_name += "_exp"
    elif args.only_action:
        log_path_name += "_act"
    log_path = app_result_path.joinpath(f"{log_path_name}.log")

    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logger_handlers = [logging.FileHandler(log_path, mode='w')]
    logger_handlers[0].setFormatter(ColoredFormatter(detailed=True, use_color=True))
    if not args.quiet:
        logger_handlers.append(logging.StreamHandler())
        logger_handlers[-1].setFormatter(ColoredFormatter(detailed=False, use_color=True))
    logging.basicConfig(handlers=logger_handlers)
    # ---------------- Start Hack -----------
    py_src_path = Path(sys.argv[0]).parent
    py_src_file_names = [p.name[:-len(".py")] for p in py_src_path.iterdir() if p.is_file() and p.name.endswith(".py")]
    for name in logging.root.manager.loggerDict:
        if name in py_src_file_names or name == "__main__":
            logging.getLogger(name).setLevel(level)
    # ----------------- End Hack ------------
    logger.info(f"Analyzing Snapshot '{args.snapshot}' in app '{args.app_name}'...")
    try:
        client = AdbClient(host=args.adb_host, port=args.adb_port)
        device = asyncio.run(client.device(args.device))
        analyze_snapshot(device,
                         snapshot_result_path,
                         directional_action_limit=args.dir_action_limit,
                         point_action_limit=args.point_action_limit,
                         is_oversight=args.oversight,
                         only_explore=args.only_explore,
                         only_action=args.only_action,
                         is_instrumented=args.instrumented)
    except Exception as e:
        logger.error("Exception happened in analyzing the snapshot", exc_info=e)
    logger.info(f"Done Analyzing Snapshot '{args.snapshot}' in app '{args.app_name}'")
