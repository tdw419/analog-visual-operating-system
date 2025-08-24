# demo_raw.py — you edit this; screen updates instantly in --live mode

# pixels
for x in range(40, 300, 2):
    y = 80 + int(20 * __import__("math").sin(x * 0.1))
    set_pixel(x, y, 0, 255, 0)

# rect + text
rect(10, 120, 80, 20, 20, 120, 240)
text(14, 124, "hello analog")

# optional tiny anim loop (press Space to step or modify live)
import time
for i in range(60):
    rect(200+i, 160, 2, 12, 255, 200-(i%200), 0)
    commit()
    time.sleep(0.01)
