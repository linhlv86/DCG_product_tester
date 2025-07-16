import subprocess
import time
import os
import signal

# Kill các tiến trình gpio_test.py cũ (trừ chính mình)
def kill_old_gpio_test():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "gpio_test.py"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split('\n')
        for pid in pids:
            if pid and int(pid) != os.getpid():
                os.kill(int(pid), signal.SIGKILL)
    except Exception as e:
        print(f"Error killing old gpio_test.py: {e}")

kill_old_gpio_test()

GP_IOSET = "/usr/bin/gpioset"

# Mapping các GPIO cần điều khiển
gpio_119 = ("gpiochip3", "23")  # GPIO119
other_gpios = [
    ("gpiochip4", "5"),   # GPIO133
    ("gpiochip4", "4"),   # GPIO132
    ("gpiochip4", "6"),   # GPIO134
    ("gpiochip3", "29"),  # GPIO125 (cần xác nhận lại line nếu chưa đúng)
]

def blink_gpios():
    idx = 0
    gpio119_state = 0

    while True:
        # Toggle GPIO119
        gpio119_state = 1 - gpio119_state
        subprocess.run([GP_IOSET, gpio_119[0], f"{gpio_119[1]}={gpio119_state}"])

        # Chỉ bật 1 GPIO trong list, các GPIO còn lại tắt
        for i, gpio in enumerate(other_gpios):
            state = 1 if i == idx % len(other_gpios) else 0
            subprocess.run([GP_IOSET, gpio[0], f"{gpio[1]}={state}"])

        time.sleep(0.5)
        idx += 1

if __name__ == "__main__":
    blink_gpios()