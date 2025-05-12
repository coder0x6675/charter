
# Charter

> A service that notifies subscribing users on new TV-show releases.

This program will send notifications to users via email once new TV-episodes are released. Each user has their own list of subscribed shows.

## Project status

This project was archived 2023 and is not under active development. It is only kept as a demo and proof of concept.

## Installation (Unix)

**OBS!** Charter uses the `msmtp` program to send the email notifications, and thus assumes that a pre-configured version is installed.

Assure you have the required privileges, feel free to change anything you deem necessary. The following commands will install the program in the user HOME directory.

``` bash
cd
git clone 'https://github.com/coder0x6675/charter.git'
cd charter
python -m venv venv
venv/bin/pip install -r requirements.txt
```

## Usage

Perform the following steps to get up and running:

``` bash
mkdir subscribers
$EDITOR subscribers/USER@EMAIL.com
```

Replace the email with the email for that particular subscriber. The contents should list the tv-shows the user wants to subscribe to, one episode per line. Empty lines or lines starting with '#' are ignored. Any dots in the title should be replaced with a space. Multiple users can be added.

Then, start the service:

``` bash
chmod +x charter.py
./charter.py
```

A systemd service file is included for convenience. It assumes the program is installed to `~/charter`. Feel free to modify it according to your needs.

``` bash
sudo cp systemd/charter.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable --now charter.service
```

