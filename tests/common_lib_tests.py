from ..libs import common_lib as cl


def test_round_down():
    print("------------------")
    print("STARTING TESTS: test_round_down")

    # run function
    output1 = cl.round_down(9.000000001)
    output2 = cl.round_down(9.00000001)
    output3 = cl.round_down(9.0000001)

    # check output
    assert str(output1) == "9.0", "Failed to truncate number with too many digits"
    assert str(output2) == "9.00000001", "Failed to properly round digits at 8 decimal places"
    assert str(output3) == "9.00000009", "Failed to properly round digits at 7 decimal places"
 
    print("ALL TESTS COMPLETED SUCCESSFULLY")


def test_get_available_twd_balance():
    print("------------------")
    print("STARTING TESTS: test_get_available_twd_balance")

    # run function
    output = cl.get_available_twd_balance()

    # check output
    assert output >= 0.0, "Failed to get available balance"
 
    print("ALL TESTS COMPLETED SUCCESSFULLY")


def run_all_tests():
    print("---------------------------")
    print("------------------")
    print("STARTING COMMON LIBRARY TESTS")
    print("------------------")
    print("---------------------------")

    test_round_down()
    test_get_available_twd_balance()

    print("---------------------------")
    print("------------------")
    print("ALL COMMON LIBRARY TESTS COMPLETED")
    print("------------------")
    print("---------------------------")
