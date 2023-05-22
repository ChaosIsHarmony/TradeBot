from . import common_lib_tests as clt
from . import parser_lib_tests as plt
from ..libs import common_lib as cl

TESTS = [
        plt,
        clt
        ]

if __name__ == "__main__":
    cl.LOG_TO_CONSOLE = False
    for test in TESTS:
        print()
        test.run_all_tests()
