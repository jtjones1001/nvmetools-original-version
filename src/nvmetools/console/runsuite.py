# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
import argparse

import nvmetools.suites as suites
import nvmetools.support.console as console


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Run NVMe Test Suite",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("suite", help="test suite")

        parser.add_argument(
            "-n", "--nvme", required=True, type=int, default=0, help="NVMe drive number (e.g. 0)", metavar="#"
        )
        parser.add_argument("-v", "--volume", required=True, help="volume to test")
        parser.add_argument("-l", "--loglevel", type=int, default=1, help="volume to test")

        parser.add_argument("-i", "--run_id", help="ID to use for directory name")
        parser.add_argument("-p", "--pdf", dest="pdf", help="Display the pdf report", action="store_true")
        parser.add_argument("-V", "--verbose", help="Verbose log mode", action="store_true")
        parser.add_argument("-D", "--debug", help="Debug mode", action="store_true")

        args = vars(parser.parse_args())

        try:
            getattr(suites, args["suite"])(args)
        except AttributeError as e:
            print(f"FATAL ERROR: {args['suite']} not found")
            print(e)

    except Exception as e:
        console.exit_on_exception(e)


if __name__ == "__main__":
    main()
