# csgo_auto_accept
An Auto-Accept-Script for Counter-Strike Global Offensive

To run one needs to clone the repo and have Python 3.X installed.
Once downloaded run pip install -r requirements.txt in a command-line in the repo folder

After that you'll need to make changes to the config_clean.ini.
- Change its name to config.ini
- The "Account 1" section
	- Add your Steam ID 64 in "Steam ID"

To use csgostats.gg you'll need to add one of your "Match Token" which will be "CSGO-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX" without '"'
The Authentication Code is used to make a request to the Steam API which will return the next sharecode. Authentication Code will be something like "XXXX-XXXX-XXXX"
Both can be found at https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid=730&issueid=128
The Script will throw an errror if the API-Key is not set as it will try to get the Username associated with the Steam ID from the API.
Also be cause of recent changes to csgostats.gg the automatic match additon isn't working anymore :(
The script will now print the sharecode and copy it into the clipboard
- Under "Access to Your Match History"
	- "Create Authentication Code" or
	- "Authentication Code:"	
- And
	- "Your most recently completed match token:"

- "Account 2" can be used to add more then one account
- As many accounts as needed can be added ("Account 3" and so on)

- The csgostats.gg section:
	- A Steam API Key must be added here
	- Auto Retrying for queue position below: Where the game in the queue can be to still be rechecked
	- Auto Retrying Interval: How many seconds after a retry on a queued match is performed
	
- The Pushbullet section:
	- Not need, can be used to get notifications on your cellphone when a game has started or csgostats.gg is done with your match
	- API Key: Pushbullet API can be found https://www.pushbullet.com/#settings/account
	- Device Name: Must be your Device Name as its stated on the pusbullet website. It can be found here https://www.pushbullet.com/#settings/devices

- The HotKeys section:
	- KeyCodes from https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes can be used
	
- The Screenshot section:
	- Interval is the Interval a screenshot is taken in seconds
	- Log Color is the color the damage log is shown in the top right of csgo (Standart here is lime green)
		- some output is needed here as the script will set developer 1 in the csgo-config
		- if no specifed filter is specifed then the console output will be mirrored
		- con_filter could probably be set to some string so it would never output anything but we dicided the damage log is ok
	- Debug Path currently stores a mirrored console.log
	
