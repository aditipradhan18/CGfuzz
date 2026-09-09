import time

def process(data):
    if data == b"HANG":
        time.sleep(10)
    return "OK"

target = process
