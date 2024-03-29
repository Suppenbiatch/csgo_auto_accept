1# csgo_auto_accept
An Auto-Accept-Script for Counter-Strike Global Offensive

To run one needs to clone the repo and have Python 3.X installed.
Once downloaded run pip install -r requirements.txt in a command-line in the repo folder

!! THIS SCRIPT NEEDS A DISCORD BOT AS A "BACKEND" !!

After that you'll need to make changes to the config_clean.ini.
- Change its name to config.ini
	- `Account 1` section
		- Add your Steam ID 64 in "Steam ID"
		- AutoBuy can be edited
			- AutoBuy will executed the appropriate script if the player has not tabbed until the BuyTime is almost over
			- `AutoBuy` is the same as `AutoBuy 0` -> will always run
			- `AutoBuy 1700T` will only execute if > 1700$ and on T-Side
			- `AutoBuy 1700CT` will only execute if > 1700$ and on CT-Side
			- `AutoBuy 2000` will only execute if > 2000$
			- AutoBuy will go through in reverse -> highest match will be executed and nothing after that
	- `csgostats.gg` section
		- `API Key`: Add a SteamWebAPI Key
		- `Auto-Retrying-Interval`: Time in seconds the thread will sleep after making a request to the Discord Bot
		- `Status Requester`: Bool, if True the script will execute a `status` command and send the result to the Discord Bot
		- `Secret`: A shared secret between the Script and the Discord Bot -> Matches are send as pickle dumps and encrypted with this secret
		- `WebServer IP`: The WebServer IP provided by the Discord Bot
		- `WebServer Port`: The WebServer Port of the WebServer provided by the Discord Bot
	- `Notifier` section
		- `Discord User ID`: A Discord User ID -> If set, enables to send afk messages via discord
	- `HotKeys` section
		- `WebHook IP`: `127.0.0.1` -> WebHooks can only be called from local device, `0.0.0.0` -> WebHooks can be called from everywhere
		- `WebHook Port`: Port to be used for the WebHook Server
	- `Script Settings`
		- `TelNet IP`: `127.0.0.1` -> no idea why this is a config param
		- `TelNet Port`: Choose a free port on your computer
		- `Interval`: Script sleeps after every loop for this amount of seconds
		- `Forbidden  Programs`: plays sound if a window title with an exact match is found, can be comma-sepearted list
		- `Match History Lenght`: Number of match outcomes shown at beginning warmup
		- `Anti-AFK Delay`: Seconds after being tabbed out until the anti-afk script starts
		- `AFK Reset Delay`: Seconds after tabbed in until the anti-afk script timer resets
		- `Copy To Clipboard`: `1` (True), copies the csgostats.gg match url to the clipboard after parsing finished
		- `AutoBuy Active`: `1` (True), activates or deactivates autobuy by default
	- `Sounds`
		- `Use Web Sounds`: `0` (False), If `True`, asks the bot for sounds and uses them instead of the default ones
		- Set any of those to `False` to always use the default sound for that category
			- `Use button_found`: `1`
			- `Use activated`: `1`
			- `Use not_all_accepted`: `1`
			- `Use ding`: `1`
			- `Use all_accepted`: `1`
			- `Use fail`: `1`
			- `Use accept_failed`: `1`
			- `Use ready`: `1`
			- `Use server_found`: `1`
		- `Excluded Sounds`: Comma sperated list of file names you want to be excluded from the sound pool
	- `FullBuy`
        - Set `Weapon` that is not equipped in inventory 
          - `deagle slot`: `revolver` or `deagle`
          - `usp slot`: `hkp2000` or `usp_silencer`
          - `fiveseven slot`: `fiveseven` or `cz75a` 
          - `mp7 slot`: `mp7` or `mp5sd`
          - `m4a4 slot`: `m4a1_silencer` or `m4a4`
          - `tec9 slot`: `tec9` or `cz75a`

- Add `-netconport [port]` to the launch options of csgo, `port` needs to be same as set in `TelNet Port`
- Add multiple accounts by creating a new section called `Account 2` until `Account X` with the same `keys` as `Account 1`

- `WebHook Endpoints`:
    - `minimize` -> minimizes and maximizes csgo via special ESC button emulation
    - `activate` -> manually activates looking for match
    - `pushbullet` -> activates afk messages send via discord
    - `upload` -> manually starts upload thread to look for new matches and requests them via the discord bot backend
    - `switch_accounts` -> if the script is already running and the user switches account use this to switch between accounts from config
    - `mute` -> uses the Windows audio mixer to mute csgo
    - `discord_toggle` -> Disables/Enables discord output if a match is parsed by the discord bot
    - `end` -> exits the script, `delay` query param ignores call if `startup - now < delay`
    - `fetch_status` -> manually invokes `status` via console and sends result to discord backend
    - `dev_mode` -> manually set `developer 1` and `sv_max_allowed_developer 1` for the script to work 
    - `console` -> accepts query parameter `ìnput` as dumped json of list of commands e.g. (/console?input="["say hello", "..."]")
      - might want to use `object/WebHookCreator.py` for easier formatting
      - eg: `py WebHookCreator.py "buy vest, buy p250, buy p90"`
    - `autobuy` -> manually trigger autobuy script even if in-game
    - `seek` -> manually seek to the end of the console log file
    - `afk` -> manually activate anti-afk script
    - `force_minimize` -> `min` or `max` as query parameter to force minimize or maximize the game, query key is ignored
    - `clear_queue` -> clears the queue of matches that are still queued to be processed by csgostats	
    - `update_sounds` -> updates the web sounds list, downloads any new sounds, and re-shuffles the current sound selection
    - `toggle_autobuy` -> switches the current autobuy status
    - `reset_match_error` -> resets the latest "error" in the match database, forces the match to be requested again
    - `fullbuy` -> `kevlar=(1|2)`, `main=(1|2)` as query params; 
      - `main=2&kevlar=1` -> buy main, buy kevlar, buy rest, buy only main if not enough money for both
      - `main=1&kevlar=2` -> buy kevlar, buy main, buy rest but only kevlar if not enough money for both
      - `kevlar=1` -> buy kevlar, buy rest at random
      - `main=1` -> buy main, buy rest at random


    - example call: `http://{WebHook IP}:{WebHook Port}/{Endpoint}` -> `http://127.0.0.1:8000/minimize`
    - example query call: `http://127.0.0.1:8000/end?delay=120`

- `WebSocket Endpoints`:
  - The Script tries to connect to a WebSocket provided by the discord bot backend
  - If the connection was not successful or was aborted it will retry every 5seconds
  - Messages retrieved with `{action: chat_message}` will execute `{message: "message"}`
  
    and answer with a `{action: 'acknowlege', success: true | false}` whether the script tried to send the command via `TelNet` to csgo
  - commands are formatted as following: ``.command.namefilter?`` where `command` can be a csgo console command or a script defined command like `fullbuy`
  	- `.slot1` would execute for everyone
    - `.slot1.f` would execute for everyone who's ingame name starts with `f`
    - `.slot1;!delay100;drop` would switch to `slot1`, `wait 100ms` and `drop` for everyone
    - `!delay[ms]` is an exception as its done by the script 
    - commands like `disconnect` and `exit` are ignored by default
    - commands that change key or similar are executed
	