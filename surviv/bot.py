from utils import get_bullet_speed
from pynput import keyboard
import pyppeteer as pyp
import numpy as np
import threading
import asyncio
import time


class SurvivBot(threading.Thread):

  async def _async_init(self):
    self.connection = await pyp.connect(browserURL='http://127.0.0.1:9222')
    self.page = (await self.connection.pages())[-1]

    self.fire_on = False
    self.mouse_lock_on = False
    self.keyboard_lock_on = False
    self.flurry_on = False
    self.needs_key_clear = False
    self.switch_to_flurry = False
    self.activate_flurry = False
    self.mov_keys = ['w', 'a', 's', 'd']
    self.still_ticker = 0

    n = (1/np.sqrt(2))
    self.mov_dirs = np.array([[0, 1],
                              [1, 0],
                              [0, -1],
                              [-1, 0],
                              [n, n],
                              [-n, n],
                              [n, -n],
                              [-n, -n]])
    walking_speed = 0.39662
    ak47_ratio = 8.62908
    self.bullet_scale = walking_speed * ak47_ratio
    self.bullet_scale *= self.args.aim_fine_tune
    self.target_vel = np.array([0, 0])

    self.double_fire_on = False
    self.use_switch_delay = False
    self.free_switch_time = time.time()
    self.prev_time = time.time()
    self.delay = 0.

    self.middle_of_screen = {'x': self.args.screen_width/2, 
                             'y': self.args.screen_height/2}
    
    tracing_code = '''
    window.gunInfo = {};
    window['webpackJsonp'][1][1]['ad1c4e70'](window.gunInfo);

    function pointToScreen(pos, me) {
      var scale = window.displayInfo.m_zoom * window.displayInfo.ppu; 
      window.scale = scale;
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
    var traces = {};

    var closeColor = 0xff0000;
    var belowColor = 0x000000;

    var players = window.pool.m_pool;
    var teamInfo = window.teamInfo;
    for (i = 0; i < players.length; i++) {
      player = players[i];
      if (player.m_localData.m_zoom) {
        window.me = player;
        for (let [key, team] of Object.entries(teamInfo)) {
          if (team.playerIds.includes(window.me.__id)) {
            window.teamId = parseInt(key);
          };
        };
      };
    };

    function updateTraces(deltaTime) {
      var pool = window.pool.m_pool;
      var me = window.me;

      myMousePos = window.input.m_mousePos;
      myPointMousePos = screenToPoint(myMousePos, me); 
      window.myInfo = [[me.pos.x, me.pos.y],
                       [me.posOld.x, me.posOld.y],
                       [myPointMousePos.x, myPointMousePos.y]];
      window.gunType = me.m_netData.m_curWeapType;
      window.curWeapInfo = window.gunInfo['exports'][window.gunType];

      if (window.curWeapInfo !== undefined) {
        window.fireDelay = window.curWeapInfo.fireDelay;
        window.switchDelay = window.curWeapInfo.switchDelay;
        window.gunLength = window.curWeapInfo.barrelLength;
      } else {
        window.fireDelay = 0;
        window.switchDelay = 0;
        window.gunLength = 0;
      };
      
      window.targetInfo = [];

      for (let targetId in traces) {
        traces[targetId].clear()
      }

      if (!me.m_netData.m_dead) {
        for (let i = 0; i < pool.length; i++) {
          const target = pool[i];
          const targetId = target.__id;

          if (targetId !== me.__id) {
            var active_player = (target.active && !target.m_netData.m_dead);
            var is_enemy = window.playerInfo[targetId].teamId !== window.teamId;
            if (active_player && is_enemy) {
              if (traces[targetId] !== undefined) {
                trace = traces[targetId]
              } else {
                var trace = new PIXI.Graphics();
                window.pixiApp.stage.addChild(trace);
                traces[targetId] = trace;
              }

              if (target.layer === me.layer) {
                var lineColor = closeColor;
              } else {
                var lineColor = belowColor;
              }

              const myScreenPos = pointToScreen(me.pos, me);
              const targetScreenPos = pointToScreen(target.pos, me);
              trace.lineStyle(6, lineColor, 0.3);
              trace.moveTo(myScreenPos.x, myScreenPos.y);
              trace.lineTo(targetScreenPos.x, targetScreenPos.y);

              window.targetInfo.push([[target.pos.x, target.pos.y],
                                      [target.posOld.x, target.posOld.y],
                                      [target.dir.x , target.dir.y]]);

            }
            else if (target.m_netData.m_dead && traces[targetId] !== undefined) {
              traces[targetId].destroy();
              delete traces[targetId];
            }
          }
        }
      } else {
          for (let key in traces) {
            traces[key].destroy();
          };
      };
    };

    window.pixiApp.ticker.add(updateTraces);
    '''

    self.grab_info_code = '''
    function() {
      return [window.myInfo, 
              window.targetInfo, 
              window.gunType,
              window.gunLength,
              window.switchDelay,
              window.fireDelay,
              window.scale];
     }
     '''

    await self.page.evaluate(tracing_code)
    await self.page.setViewport({'width': self.args.screen_width, 
                                 'height': self.args.screen_height})

    print("Succesfully injected!")
    self.online = True

  def point_to_screen(self, point, scale):
    x = self.middle_of_screen['x'] + point[0]*scale
    y = self.middle_of_screen['y'] - point[1]*scale
    return (x, y)
  
  def get_pred_target(self, target_pos, my_pos, gun_type, gun_length):
    dist_vec = target_pos - my_pos
    target_pred = dist_vec
    bullet_speed = get_bullet_speed(gun_type)
    if bullet_speed is None:
      if np.linalg.norm(dist_vec) < 3.1:
        self.activate_flurry = True
      return target_pred, dist_vec
    vp = self.target_vel
    vpn = np.dot(vp, vp)
    if 0 < vpn < 1:
      bl = gun_length
      db = target_pred
      dbn = np.dot(db, db)
      vb = self.bullet_scale * (bullet_speed/100)
      vbn = vb**2
      bp = np.dot(db, vp)
      de = (vbn - vpn)
      diff = (bp - bl*vb) / de
      time = (diff + np.sqrt(diff**2 + (dbn-bl**2)/de))
      if time < 0:
        self.activate_flurry = True
        self.switch_to_flurry = True
        return target_pred, dist_vec
      target_pred = db + time * vp
    return target_pred, dist_vec

  def get_target(self, my_info, target_info, gun_type, gun_length):
    my_pos, my_old_pos, my_mouse_pos = np.array(my_info)
    targets = np.array(target_info)
    
    target_dists = ((targets[:, 0, :] - my_mouse_pos)**2).sum(axis=1)
    target_pos, target_old_pos, target_dir = targets[target_dists.argmin()]

    if (target_pos != target_old_pos).any():
      self.target_vel = target_pos - target_old_pos
      self.still_ticker = 0
    else:
      self.still_ticker += 1

    if self.still_ticker > 10:
      self.target_vel = np.array([0, 0])

    target_pred_pos, dist_vec = self.get_pred_target(target_pos, 
                                                     my_pos,
                                                     gun_type,
                                                     gun_length)
    return target_pred_pos, target_dir, dist_vec

  async def mouse_lock(self):
    game_info = await self.page.evaluate(self.grab_info_code)
    my_info, target_info, gun_type, gun_length, switch_delay, fire_delay, scale = game_info

    if target_info:
      target = self.get_target(my_info, target_info, gun_type, gun_length)
      target_pred_pos, target_dir, dist_vec = target

      scale = 0.6 * scale
      x, y = self.point_to_screen(target_pred_pos, scale)

      if self.activate_flurry:
        if self.switch_to_flurry:
          await self.page.keyboard.press(args.switch_key, options={'delay': 50})
          self.switch_to_flurry = False
        self.keyboard_lock_on = True
        self.fire_on = True
        self.flurry_on = True
        self.activate_flurry = False

      if self.fire_on:

        if self.use_switch_delay:
          self.delay = switch_delay

        if self.flurry_on:
          await self.keyboard_lock(target_pred_pos, 
                                   target_dir,
                                   dist_vec)
          await self.page.mouse.click(x, y, options={'delay': 50})

        elif (time.time() - self.prev_time) > self.delay:
          await self.page.mouse.click(x, y, options={'delay': 50})
          self.delay = fire_delay

          if self.double_fire_on:
            await self.page.mouse.click(x, y, options={'button': 'right',
                                                       'delay': 50})
            if (time.time() - self.free_switch_time) > 1:
              self.free_switch_time = time.time()
              self.use_switch_delay = False
              self.delay = 0.25
            else:
              self.use_switch_delay = True

            self.prev_time = time.time()

        else:
          await self.page.mouse.move(x, y);

      else:
        await self.page.mouse.move(x, y);

  async def press_keys(self, keys, anti_keys):
    [await self.page.keyboard.up(anti_key) for anti_key in anti_keys]
    [await self.page.keyboard.down(key) for key in keys]
    self.needs_key_clear = True

  async def keyboard_lock(self, target_pos, target_dir, dist_vec):
    dist = np.linalg.norm(dist_vec)

    if (np.dot(dist_vec, target_dir)) <= 0:
      mov_pos = target_pos + 0.1*(dist_vec/dist)
    else:
      mov_pos = target_pos - 0.1*(dist_vec/dist)

    diff = mov_pos - 0.25*self.mov_dirs
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

  async def clear(self):
    if self.needs_key_clear:
      [await self.page.keyboard.up(key) for key in self.mov_keys]
      self.needs_key_clear = False
    self.target_vel = np.array([0, 0])

  def run(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(self._async_init())
    while self.online:
      time.sleep(0.01)
      while self.mouse_lock_on:
        loop.run_until_complete(self.mouse_lock())
      loop.run_until_complete(self.clear())
    loop.stop()
    loop.close()


def main(args):
    bot = SurvivBot()
    bot.args = args
    bot.start()

    if args.aim_lock_key == 'shift':
      aim_lock_key = keyboard.Key.shift
    else:
      aim_lock_key = keyboard.KeyCode(char=args.aim_lock_key)
    fire_key = keyboard.KeyCode(char=args.fire_key)
    double_fire_key = keyboard.KeyCode(char=args.double_fire_key)
    stop_key = keyboard.KeyCode(char=args.stop_key)

    def release_callback(key):
      if key == aim_lock_key:
        bot.mouse_lock_on = False
        if bot.flurry_on:
          bot.keyboard_lock_on = False
          bot.fire_on = False
          bot.flurry_on = False

    def press_callback(key):
      if key == aim_lock_key:
        bot.mouse_lock_on = True
      elif key == fire_key:
        bot.fire_on = not bot.fire_on
        if bot.fire_on:
          print("Automatic firing activated!")
        else:
          print("Automatic firing deactivated!")
      elif key == double_fire_key:
        bot.double_fire_on = not bot.double_fire_on
        if bot.double_fire_on:
          print("Automatic double firing activated!")
          bot.fire_on = True
        else:
          print("Automatic double firing deactivated!")
          bot.fire_on = False
      elif key == stop_key:
        print("Shutting down")
        bot.online = False
        bot.mouse_lock_on = False
        bot.keyboard_lock_on = False
        bot.fire_on = False
        listener.stop()

    with keyboard.Listener(on_press=press_callback, 
                           on_release=release_callback) as listener:
        listener.join()


if __name__ == '__main__':
    from argparse import RawTextHelpFormatter
    import argparse

    description = '''Surviv hack for the Chrome debugger!'''

    parser = argparse.ArgumentParser(description=description, 
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--aim_lock_key', type=str, default="shift",
                         help='hold key to lock aim onto a target')
    parser.add_argument('--fire_key', type=str, default="q",
                         help='key to activate automatic firing')
    parser.add_argument('--double_fire_key', type=str, default="e",
                         help='key to activate automatic double firing')
    parser.add_argument('--switch_key', type=str, default="f",
                         help='set the same as stow weapons key on surviv')
    parser.add_argument('--stop_key', type=str, default="L",
                         help='key to stop the program')
    parser.add_argument('--aim_fine_tune', type=float, default=1.,
                         help='fine tune the amount of aim prediction')
    parser.add_argument('--screen_width', type=int, default=1920,
                         help='width of your screen')
    parser.add_argument('--screen_height', type=int, default=970,
                         help='height of your screen')
    args = parser.parse_args()

    main(args)







