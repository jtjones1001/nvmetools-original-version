# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
import argparse

import nvmetools.suites as suites
import nvmetools.support.console as console


def main():

    try:
        parser = argparse.ArgumentParser(
            description="Check NVMe Health",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "-n",
            "--nvme",
            required=True,
            type=int,
            default=0,
            help="NVMe drive number (e.g. 0)",
            metavar="#",
        )
        parser.add_argument("-l", "--loglevel", type=int, default=1, help="volume to test")
        parser.add_argument("-i", "--run_id", help="ID to use for directory name")
        args = vars(parser.parse_args())

        suites.health(args)

    except Exception as e:
        console.exit_on_exception(e)


if __name__ == "__main__":
    main()
