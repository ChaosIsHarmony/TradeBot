import threading
import time

TIMES = 20


def func_1() -> None:
    global TIMES

    while TIMES > 0:
        print("func_1")
        TIMES -= 1
        time.sleep(5)

def func_2() -> None:
    global TIMES

    while TIMES > 0:
        print("func_2")
        TIMES -= 1
        time.sleep(1)

t1 = threading.Thread(target=func_1)
t2 = threading.Thread(target=func_2)

t1.start()
t2.start()

t1.join()
t2.join()

print("finished")
