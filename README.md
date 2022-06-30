# csgo_auto_accept
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
		- `TelNet IP`: "127.0.0.1" -> no idea why this is a config param
		- `TelNet Port`: Choose a free port on your computer
		- `Interval`: Script sleeps after every loop for this amount of seconds
		- `Forbidden  Programs`: plays sound if a window title with an exact match is found, can be comma-sepearted list
		- `Match History Lenght`: Number of match outcomes shown at beginning warmup
		- `Anti-AFK Delay`: Seconds after being tabbed out until the anti-afk script starts
		- `AFK Reset Delay`: Seconds after tabbed in until the anti-afk script timer resets
- Add `-netconport [port]` to the launch options of csgo, `port` needs to be same as set in `TelNet Port`
- Add multiple accounts by creating a new section called `Account 2` until `Account X` with the same `keys` as `Account 1`

- `WebHook Endpoints`:
	- `minimize` -> minimizes and maximizes csgo via special ESC button emulation
	- `activate` -> manually activates looking for match
	- `pushbullet` -> activates afk messages send via discord
	- `upload` -> manually starts upload thread to look for new matches and requests them via the discord bot backend
	- `switch_accounts` -> if the script is already running and the user switches account use this to switch between accounts from config
	- `mute` -> uses the windows audio mixer to mute csgo
	- `discord_toggle` -> Disables/Enables discord output if a match is parsed by the discord bot
	- `end` -> exits the script
	- `fetch_status` -> manually invokes `status` via console and sends result to discord backend
	- `dev_mode` -> manually set `developer 1` and `sv_max_allowed_developer 1` for the script to work 
	- `console` -> accepts query parameter `ìnput` as dumped json of list of commands e.g. (/console?input="["say hello", "..."]")
	- `autobuy` -> manually trigger autobuy script even if in-game
	- `seek` -> manually seek to the end of the console log file
	- `afk` -> manually activate anti-afk script
	
	- example call: `http://{WebHook IP}:{WebHook Port}/{Endpoint}` -> `http://127.0.0.1:8000/minimize`
