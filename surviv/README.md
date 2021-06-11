# Surviv bot for Chrome

A script that talks to the Chrome browser using [pyppeteer](https://github.com/pyppeteer/pyppeteer) and grabs info about the game.
This info is then used to create an aimbot and wallhack, as well as punch chasing.

---
## Installation:
```bash
git clone https://github.com/JimOhman/fun.git
cd fun/surviv/
pip install -r requirements.txt
```

---
## Usage:

Currently, it is a bit annoying to start but its not too bad once you get used to it. Takes about 15 seconds per game.
```
1. Open up Chrome with the --remote-debugging-port=9222 flag.
2. Go to surviv.io and open up the debugger (Ctrl+Shift+I).
3. In the Sources tab, open surviv.io/js/app.js and prettify the code.
4. Place a breakpoint at line 75045 and join a game.
3. When the breakpoint is hit, enter the following into the console:

     windw.pool = _0x5d6daa.m_playerPool;
     window.pixiApp = _0x41b8c9.game.pixi;
     window.input = _0x3e3b49.input;
     window.displayInfo = _0x401da4;

4. Close the debugger and run python bot.py.
5. Play!
```
To play a new game you have to close everything, use (Shift+L) for the bot, and repeat the steps.

---
You will likely need to change the width and height of the browser window, due to a weirdness of pyppeteer.

The right values could be found in the debugger by opening surviv.io without the bot active and entering:

* window.innerHeight * window.devicePixelRatio
* window.innerWidth * window.devicePixelRatio

Then you can provide the integer values of these as arguments when you run python bot.py.

|Required Arguments | Description|
|:-------------|:-------------|
| `--screen_width`          |The width of your browser window (default: 2560)|
| `--screen_height`         |The height of your browser window (default: 1330)|

|Optional Arguments | Description|
|:-------------|:-------------|
| `--aim_lock_key`          |Hold this key to lock the aim onto a target close to your cursor. (default: Shift)|
| `--flurry_lock_key`       |Hold this key to chase a target and punch quickly. (default: q)|
| `--fire_lock_key`         |Activate automatic firing on aim locked targets. (default: f)|

