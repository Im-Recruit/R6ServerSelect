🎮 R6 Server Select GUI
A user-friendly Python application built with customtkinter to easily view real-time latency (ping) to various Rainbow Six Siege data centers and permanently set your preferred server in the GameSettings.ini file.

✨ Features
Real-time Ping Display: Uses ICMP pinging (ping3) to show live latency to each major R6 data center.

Latency Color-Coding: Quickly identify the best servers with color-coded pings:

Green: $\le 50$ ms

Yellow: $\le 100$ ms

Red: $> 100$ ms or Timeout

Auto-Sort: Automatically reorders the server list based on the lowest current latency. This feature can be toggled on/off in the settings.

Auto-Selection: The "Auto (Default)" option dynamically displays the fastest available server in real-time.

INI File Integration: Directly reads and writes the DataCenterHint in your GameSettings.ini file.

Simple GUI: Built using customtkinter for a modern, dark-themed interface.

🛠️ Prerequisites

This application requires Python 3.x and the following libraries:

customtkinter

ping3

⬇️ Installation

1. Download the script
   
Download the R6ServerSelect.py file to your computer.

2. Install Dependencies
   
Open your command prompt or terminal and run the following command to install the required Python packages:

pip install customtkinter ping3


🚀 How to Use

Run the application:

python R6ServerSelect.py

Select your GameSettings.ini File:

Click the "Browse / Change File" button.

The application will try to open the default R6 directory (~\Documents\My Games\Rainbow Six - Siege).

Navigate into the folder named with your unique profile ID (a long string of numbers and letters) and select the GameSettings.ini file.

The "Current Profile" label will update to show the profile ID.

View and Select Server:

The server list will immediately begin fetching real-time pings.

The list will sort itself by latency (if the "Auto-Sort" checkbox is enabled).

Click on any server name to select it. The selected server will be highlighted in green.

Save Your Choice:

Click the "Save to INI" button.

This writes the corresponding DataCenterHint (e.g., playfab/westeurope) into your GameSettings.ini file under the [ONLINE] section.

A confirmation message box will appear.

Start Game:

Launch Rainbow Six Siege. The game will now connect to the server you selected.
