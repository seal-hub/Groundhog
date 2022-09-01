# Groundhog
This is the artifact repository of the paper

Navid Salehnamadi\*, Forough Mehralian\*, and Sam Malek, "**Groundhog: An Automated Accessibility Crawler for Mobile Apps**" in 2022 37th IEEE/ACM International Conference on Automated Software Engineering (ASE), 2022

## Abstract

Accessibility is a critical software quality affecting more than 15% of the world’s population with some form of disabilities. Modern mobile platforms, i.e., iOS and Android, provide guidelines and testing tools for developers to assess the accessibility of their apps. The main focus of the testing tools is on examining a particular screen's compliance with some predefined rules derived from accessibility guidelines. Unfortunately, these tools cannot detect accessibility issues that manifest themselves in interactions with apps using assistive services, e.g., screen readers. A few recent studies have proposed assistive-service driven testing; however, they require manually constructed inputs from developers to evaluate a specific screen or presume availability of UI test cases. In this work, we propose an automated accessibility crawler for mobile apps, Groundhog, that explores an app with the purpose of finding accessibility issues without any manual effort from developers. Groundhog assesses the functionality of UI elements in an app with and without assistive services and pinpoints accessibility issues with an intuitive video of how to replicate them. Our experiments show Groundhog is highly effective in detecting accessibility barriers that existing techniques cannot discover. Powered by Groundhog, we conducted an empirical study on a large set of real-world apps and found new classes of critical accessibility issues that should be the focus of future work in this area.

## Setup
This repository is tested on Mac OSX; however, it should work on any Unix system For Windows systems, you need to either use bash or modify the scripts in `scripts` directory.

- (For OS X) Install coreutils "brew install coreutils"
- Use Java8, if there are multiple Java versions use [jenv](https://www.jenv.be/)
- Set `ANDROID_HOME` environment varilable (usually `export ANDROID_HOME=~/Library/Android/sdk`)
- Add emulator and platform tools to `PATH` (if it's not already added). `export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:${PATH}"`
- Setup Stoat from [this repository](https://github.com/fmehralian/Stoat/tree/navid).
- (Optional) create a virtual environment in `.env` (`python3 -m venv .env`)
- Run `source env`
- Install python packages `pip install -r requirements.txt`
- Initialize an Android Virtual Device (AVD) with SDK +28
- (Optional) To prevent any interrupt on the process of validating the apps, like random notifications during the analysis of an app, you can follow these steps.
	- Disable soft main keys and virtual keyboard by adding `hw.mainKeys=yes` and `hw.kayboard=yes`  to `~/.android/avd/testAVD_1.avd/config.ini`
		- If virtual device is not disabled, please follow this [link](https://support.honeywellaidc.com/s/article/CN51-Android-How-to-prevent-virtual-keyboard-from-popping-up)
	- Enable "Do not disturb" in the emulator to avoid notifications during testing (it can be found at the top menu)
- Install TalkBack, the version 12 can be found in `Setup/X86/TB_12_*.apk` (`adb install-multiple Setup/X86/TB_12_*.apk`)
- Build Groundhog Service APK by running `./build_groundhog.sh`, then install it (`adb install -r -g Setup/groundhog.apk`) or install from Android Studio
	- To check if the installation is correct, first run the emulator and then execute `./scripts/enable-talkback.sh` (by clicking on a GUI element it should be highlighted).
	- Also, execute `./scripts/send-command.sh log` and check Android logs to see if Latte prints the AccessibilityNodeInfos of GUI element on the screen (`adb logcat | grep "LATTE_SERVICE"`)
-  Save the base snapshot by `./scripts/save_snapshot.sh BASE`


## Groundhog CLI
You can interact with Latte by sending commands to its Broadcast Receiver or receive generated information from Latte by reading files from the local storage. First, you need to enable Latte by running `./scritps/enable-service.sh`, then you can send command by running `./scripts/send-command.sh <COMMAND> <EXTRA>`. If you want to work with TalkBack, first you need to enable it by running `./scritps/enable-talkback.sh`. If any command has an output written in a file, you can use `./scripts/wait_for_file.sh <FILE_NAME>` which prints the content of the file and removes it. It's encouraged to watch the logs in a separate terminal `adb logcat | grep "LATTE_SERVICE"`. Here is the list of all commands:
- **General**
	- `log`: Prints the current layout's xpaths in Android logs.
	- `is_live`: Given a string as the extra, creates a file `is_live_<extra>.txt`. It can be used to determine Latte is alive.
	- `invisible_nodes`: Make Latte does (not) consider invisible nodes. Extra can be 'true' or 'false'
	- `capture_layout`: Dumps the XML file of the current layout. Output's file name: `a11y_layout.xml`
	- `report_a11y_issues`: Prints the accessibility issues (reported by Accessibility Testing Framework) in Android logs.
	- `sequence`: Execute a sequence of commands which is given in input as a JSON string. Example: [{'command': 'log', 'extra': 'NONE'}]

- **Controller**
  - `controller_set`: Selects a controller among "touch", "tb_touch", "tb_api", "a11y_api" (extra is the name of the controller)
  - `controller_execute`: Performs a single step where the step is provided in extra. The result will be written in "controller_result.txt"
	- `controller_interrupt`: Interrupts the current step execution
	- `controller_reset`: Stops the current step execution and remove the result

- **TalkBack Navigation**
	- `nav_next`: Navigates the focused element to the next element. Output's file name: `finish_nav_action.txt`
	- `nav_select`: Selects the focused element (equivalent to Tap). Output's file name: `finish_nav_action.txt`
	- `nav_interrupt`: Interrupt the current navigation action
	- `nav_clear_history`: In case the last navigation result is not removed.
- **TalkBack Information**
	- `nav_current_focus`: Report the current focused node in TalkBack. Output's file name: `finish_nav_action.txt`

## Running Groundhog
To analyze a snapshot, first load the BASE snapshot `./scripts/load_snapshot.sh BASE`, then install the app under test, and go to the screen that you want to analyze. Next, creates a new snapshot by `./scripts/save_snapshot.sh <SNAPSHOT>`. Now you can run the BlindMonkey on this snapshot by running
```
python pt_src/main.py --app-name <APP_NAME> --output-path <RESLUT_PATH> --snapshot <SNAPSHOT> --debug --device "emulator-5554"
```

