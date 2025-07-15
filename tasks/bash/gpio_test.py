import subprocess
import time

def blink_gpio133():
    while True:
        # Bật GPIO133
        subprocess.run(["gpioset", "gpiochip4", "5=1"])
        time.sleep(0.3)
        # Tắt GPIO133
        subprocess.run(["gpioset", "gpiochip4", "5=0"])
        time.sleep(1.0)

if __name__ == "__main__":
    blink_gpio133()