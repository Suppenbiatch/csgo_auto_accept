# csgo_auto_accept
An Auto-Accept-Script for Counter-Strike Global Offensive

To run one need to clone the repo and have Python 3.X installed.
Once downloaded run pip install -r requirements.txt in a command-line in the repo folder

After that you'll need to make changes to the config_clean.ini.
- The "Account 1" section
	- Change its name to config.ini
	- Add your Steam ID 64 in "Steam ID"

To use csgostats.gg you'll need to add one of your "Match Token" which will be "CSGO-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX" without '"'
The Authentication Code is used to make a request to the Steam API which will return the next sharecode. Authentication Code will be something like "XXXX-XXXX-XXXX"
Both can be found at https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid=730&issueid=128
- under
	- Access to Your Match History
	- Your most recently completed match token:
- And
	- Authentication Code:

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
	- Stop Warmup OCR in the example is "0x70-0x70" which would be all keys from F1 to F1 (0x70-0x75 would be all keys from F1 to F6)
	
- The Screenshot section:
	- Interval is the Interval a screenshot is taken in seconds
	- Timeout Time isnt used currently
	- Log Color is the color the damage log is shown in the top right of csgo (Standart here is lime green)
	- FreezeTime Auto On is whether or not the sound should be played or not when the game is minimized and a freezetime is starting
	- Debug Path currently stores a mirrored console.log
	
- The Warmup section:
	- Tessract can be found https://github.com/UB-Mannheim/tesseract/wiki
	- Direct download link here: https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.0.0-alpha.20200328.exe
	- Tesseract Path is the full path to the executable without '"'
	- Test Interval is the interval in seconds that the script tries to read the text on the screenshot
	- Push Interval is the time in seconds that needs to be left for the Script to push a message
	- No Text Limit is the number of retries the Script has before it dosent will no longer retry
	
	- Warmup Detection will only be activated if Pushing is not 0.
		- Pushing 1: Pushing when accpet has been pressed and when Warmup is over
		- Pushing 2: Pushing all gamerelated messages, and at every Push Interval
		- Pushing 3: Pushing all gamerelated messages, as well as csgostats.gg completed matches
