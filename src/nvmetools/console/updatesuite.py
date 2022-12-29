# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
import argparse

from nvmetools.support.console import exit_on_exception
from nvmetools.support.framework import update_suite_files


def main() -> None:

    try:
        parser = argparse.ArgumentParser(
            description="Update NVMe Test Suite",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("-d", "--directory", help="Test suite directory", default=".")

        args = parser.parse_args()

        update_suite_files(args.directory)

    except Exception as e:
        exit_on_exception(e)


if __name__ == "__main__":
    main()
