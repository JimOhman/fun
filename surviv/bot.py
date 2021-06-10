from utils import get_bullet_speed
from pynput import keyboard
import pyppeteer as pyp
import numpy as np
import threading
import asyncio
import time


class SurvivBot(threading.Thread):

  async def _async_init(self):
    connection = await pyp.connect(browserURL='http://127.0.0.1:9222')
    self.page = (await connection.pages())[-1]

    self.fire_lock_on = False
    self.mouse_lock_on = False
    self.keyboard_lock_on = False
    self.pressed = {'w': False, 'a': False, 's': False, 'd': False}
    self.needs_clear = False

    tracing_code = '''
    var screenWidth = window.displayInfo.screenWidth;
    var screenHeight = window.displayInfo.screenHeight;

    function pointToScreen(pos, me) {
      var scale = window.displayInfo.m_zoom * window.displayInfo.ppu; 
      return {'x': window.displayInfo.screenWidth*0.5 + (pos.x - me.pos.x)*scale,
              'y': window.displayInfo.screenHeight*0.5 - (pos.y - me.pos.y)*scale};
    };

    function screenToPoint(pos, me) {
      var scale = window.displayInfo.m_zoom * window.displayInfo.ppu; 
      return {'x': me.pos.x + (pos.x - window.displayInfo.screenWidth*0.5)/scale,
              'y': me.pos.y - (pos.y - window.displayInfo.screenHeight*0.5)/scale};
    };

    window.myInfo = [];
    window.targetInfo = [];
    window.bulletType = undefined;
    var traces = {};

    var closeColor = 0xff0000;
    var belowColor = 0x000000;

    function updateTraces(deltaTime) {
      var pool = window.pool.m_pool
      me = pool[0];

      window.dT = deltaTime;

      myMousePos = window.input.m_mousePos;
      myPointMousePos = screenToPoint(myMousePos, me); 
      window.myInfo = [[me.pos.x, me.pos.y],
                       [me.posOld.x, me.posOld.y],
                       [myPointMousePos.x, myPointMousePos.y]];
      window.gunType = me.weapTypeOld;
      window.targetInfo = [];

      for (let targetId in traces) {
        traces[targetId].clear()
      }

      if (!me.m_netData.m_dead) {
        for (let i = 1; i < pool.length; i++) {
          const target = pool[i];
          const targetId = target.__id;

          if (target.active && !target.m_netData.m_dead) {
            if (traces[targetId] !== undefined) {
              trace = traces[targetId]
            } else {
              var trace = new PIXI.Graphics();
              window.pixiApp.stage.addChild(trace);
              traces[targetId] = trace;
            }

            if (target.layer === me.layer) {
              var lineColor = closeColor;
              window.targetInfo.push([[target.pos.x, target.pos.y],
                                      [target.posOld.x, target.posOld.y]]);
            } else {
              var lineColor = belowColor;
            }

            const myScreenPos = pointToScreen(me.pos, me);
            const targetScreenPos = pointToScreen(target.pos, me);
            trace.lineStyle(6, lineColor, 0.3);
            trace.moveTo(myScreenPos.x, myScreenPos.y);
            trace.lineTo(targetScreenPos.x, targetScreenPos.y);

          }
          else if (traces[targetId] !== undefined) {
            traces[targetId].destroy();
            delete traces[targetId];
          }
        }
      }
    };

    window.pixiApp.ticker.add(updateTraces);
    '''

    self.grab_info_code = '''
     function() {
       return [window.myInfo, window.targetInfo, window.gunType];
     }
     '''

    self.middle_of_screen = {'x': self.args.screen_width/2, 
                             'y': self.args.screen_height/2}

    n = (1/np.sqrt(2))
    self.mov_dirs = np.array([[0, 1],
                              [1, 0],
                              [0, -1],
                              [-1, 0],
                              [n, n],
                              [-n, n],
                              [n, -n],
                              [-n, -n]])
    walking_speed = 0.21667
    ak47_ratio = 8.62908
    self.bullet_scale = walking_speed * ak47_ratio
    self.target_vel = np.array([0, 0])

    await self.page.evaluate(tracing_code)
    await self.page.setViewport({'width': self.args.screen_width, 
                                 'height': self.args.screen_height})

    print("Succesfully injected!")
    self.online = True
  
  def get_target_dir(self, target_pos, my_pos, gun_type):
    target_dir = target_pos - my_pos
    bullet_speed = get_bullet_speed(gun_type)
    if bullet_speed is None:
      print("Bullet speed of {} not found!".format(gun_type))
      return target_dir
    db = target_dir
    vp = self.target_vel
    vpn = np.dot(vp, vp)
    if vpn < 1:
      vbn = (self.bullet_scale * bullet_speed/100)**2
      dbn = np.dot(db, db)
      bp = np.dot(db, vp)
      de = (vpn - vbn)
      scale = (-2*bp - np.sqrt(bp**2 - 4*de*dbn)) / (2*de) 
      target_dir = db + scale * vp * 0.65
    return target_dir

  def get_target(self, my_info, target_info, gun_type):
    my_pos, my_old_pos, my_mouse_pos = np.array(my_info)
    targets = np.array(target_info)

    target_dists = ((targets[:, 0, :] - my_mouse_pos)**2).sum(axis=1)
    target_pos, target_old_pos = targets[target_dists.argmin()]

    if (target_pos != target_old_pos).any():
      self.target_vel = target_pos - target_old_pos

    target_dir = self.get_target_dir(target_pos, 
                                     my_pos,
                                     gun_type)
    return target_dir

  async def mouse_lock(self):
    game_info = await self.page.evaluate(self.grab_info_code)
    my_info, target_info, gun_type = game_info

    if target_info:
      target = self.get_target(my_info, target_info, gun_type)

      if target is not None:
        x = (self.middle_of_screen['x'] + target[0])
        y = (self.middle_of_screen['y'] - target[1])

        if self.fire_lock_on:
          await self.page.mouse.click(x, y, options={'delay': 10})
        else:
          await self.page.mouse.move(x, y);

        if self.keyboard_lock_on:
          await self.keyboard_lock(target)
        elif self.needs_clear:
          await self.clear_keys()

    elif self.needs_clear:
      await self.clear_keys()
      self.target_vel = np.array([0, 0])
    else:
      self.target_vel = np.array([0, 0])

  async def press_keys(self, keys, anti_keys):
    for anti_key in anti_keys:
      if self.pressed[anti_key]:
        await self.page.keyboard.up(anti_key)
        self.pressed[anti_key] = False
    for key in keys:
      if not self.pressed[key]:
        await self.page.keyboard.down(key)
        self.pressed[key] = True
        self.needs_clear = True

  async def keyboard_lock(self, target_dir):
    diff = target_dir - 0.25*self.mov_dirs
    choice = (diff**2).sum(axis=1).argmin()
    if choice == 0:
      await self.press_keys(['w'], ['s', 'a', 'd'])
    elif choice == 1:
      await self.press_keys(['d'], ['a', 'w', 's'])
    elif choice == 2:
      await self.press_keys(['s'], ['w', 'a', 'd'])
    elif choice == 3:
      await self.press_keys(['a'], ['d', 'w', 's'])
    elif choice == 4:
      await self.press_keys(['w', 'd'], ['a', 's'])
    elif choice == 5:
      await self.press_keys(['w', 'a'], ['s', 'd'])
    elif choice == 6:
      await self.press_keys(['s', 'd'], ['w', 'a'])
    elif choice == 7:
      await self.press_keys(['s', 'a'], ['w', 'd'])
      
  async def clear_keys(self):
    for key, value in self.pressed.items(): 
      if value:
        await self.page.keyboard.up(key)
        self.pressed[key] = False
    self.needs_clear = False

  def run(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(self._async_init())
    while self.online:
      time.sleep(0.1)
      while self.mouse_lock_on:
        loop.run_until_complete(self.mouse_lock())
    loop.stop()


def main(args):
    bot = SurvivBot()
    bot.args = args
    bot.start()

    if args.aim_lock_key == 'shift':
      aim_lock_key = keyboard.Key.shift
    else:
      aim_lock_key = keyboard.KeyCode(char=args.aim_lock_key)
    flurry_lock_key = keyboard.KeyCode(char=args.flurry_lock_key)
    fire_lock_key = keyboard.KeyCode(char=args.fire_lock_key)
    stop_key = keyboard.KeyCode(char=args.stop_key)

    def release_callback(key):
      if key == aim_lock_key:
        bot.mouse_lock_on = False
      elif key == flurry_lock_key:
        bot.mouse_lock_on = False
        bot.keyboard_lock_on = False
        bot.fire_lock_on = False

    def press_callback(key):
      if key == aim_lock_key:
        bot.mouse_lock_on = True
      elif key == flurry_lock_key:
        bot.mouse_lock_on = True
        bot.keyboard_lock_on = True
        bot.fire_lock_on = True
      elif key == fire_lock_key:
        bot.fire_lock_on = not bot.fire_lock_on
      elif key == stop_key:
        print("Shutting down")
        bot.online = False
        bot.mouse_lock_on = False
        bot.keyboard_lock_on = False
        bot.fire_lock_on = False
        listener.stop()

    with keyboard.Listener(on_press=press_callback, 
                           on_release=release_callback) as listener:
        listener.join()


if __name__ == '__main__':
    from argparse import RawTextHelpFormatter
    import argparse

    description = '''
    Surviv hack using the Chrome debugger!

    How to activate:
    1. Open up Chrome with the (--remote-debugging-port=9222) flag.
    2. Go to surviv.io and open up the debugger.
    3. Prettify the code in sources at surviv.io/js/app.
    4. Place a breakpoint at line 75020 and join a game.
    3. When the breakpoint is hit, enter the following into the console:

    windw.pool = _0x5d6daa.m_playerPool;
    window.pixiApp = _0x41b8c9.game.pixi;
    window.input = _0x3e3b49.input;
    window.displayInfo = _0x401da4;o

    4. Close the debugger and run (python bot.py) in your terminal.
    5. Play!
    '''

    parser = argparse.ArgumentParser(description=description, 
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--aim_lock_key', type=str, default="shift",
                         help='hold key to lock aim onto a target')
    parser.add_argument('--flurry_lock_key', type=str, default="q",
                         help='hold key to flurry attack a target')
    parser.add_argument('--fire_lock_key', type=str, default="f",
                         help='key to activate automatic firing')
    parser.add_argument('--stop_key', type=str, default="L",
                         help='key to stop the program')
    parser.add_argument('--screen_width', type=int, default=2560,
                         help='width of your screen')
    parser.add_argument('--screen_height', type=int, default=1330,
                         help='height of your screen')
    args = parser.parse_args()

    main(args)







