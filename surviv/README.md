# A transparent Surviv bot for Chrome

This is built on a script that talks to the Chrome browser using [pyppeteer](https://github.com/pyppeteer/pyppeteer) and grabs info about the game.
This info is then used to create a predictive aimbot and wallhack, as well as automatic punch chasing.

The code is completely transparent, approx 400 lines of code. In other words, it is clear that there is no shady business going on.
The trade-off is that starting the bot is a tiny bit more annoying than pressing a button.

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
4. Place a breakpoint at line 75072 and join a game.
5. When the breakpoint is hit, enter the following into the console:

     window.pool = _0x4f4f10.m_playerPool;
     window.teamInfo = _0x4f4f10.teamInfo;
     window.playerInfo = _0x4f4f10.m_playerInfo;
     window.pixiApp = _0x3aef18.game.pixi;
     window.input = _0x1bbb85.input
     window.displayInfo = _0x2d1004;

6. Close the debugger and run python bot.py.
7. Play!
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
| `--aim_lock_key`          |Hold this key to lock the aim onto a target close to your cursor (default: shift)|
| `--fire_key`          |Key to activate automatic firing when aim locked (default: shift)|
| `--double_fire_key`          |Key to activate automatic fire-switch-fire-switch when aim locked (default: shift)|
| `--switch_key`       |This key should be the (stow weapons) key on surviv (default: f)|
| `--aim_fine_tune`         |Fine tune the aim prediction, value should be close to default (default: 0.92)|
| `--stop_key`         |This key stops the bot (default: L)|

