import time
import threading
from pynput.mouse import Button, Controller
from pynput.keyboard import Listener, KeyCode
from pynput import keyboard


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser(description='Auto-Quickfire')
  parser.add_argument('--fire_key', type=str, default='f')
  parser.add_argument('--stop_key', type=str, default='P')
  parser.add_argument('--delay', type=float, default=0.05) 
  args = parser.parse_args()

  fire_key = KeyCode(char=args.fire_key)
  stop_key = KeyCode(char=args.stop_key)
  mouse = Controller()

  def on_press(key):
    if key == fire_key:
      mouse.press(Button.left)
      time.sleep(args.delay)
      mouse.release(Button.left)
      time.sleep(args.delay)
      mouse.press(Button.right)
      time.sleep(args.delay)
      mouse.release(Button.right)
      time.sleep(args.delay)
      mouse.press(Button.right)
      time.sleep(args.delay)
      mouse.release(Button.right)
    elif key == stop_key:
      listener.stop()
  
  with Listener(on_press=on_press) as listener:
    listener.join()

  listener = keyboard.Listener(on_press=on_press)
  listener.start()

