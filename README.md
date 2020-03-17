# mastodon-bot

A bot for Mastodon to post image toots with optional text comment.

Features:
* simple login procedure: one just has to specify `client_secret` and `access_token` in secrets.yaml
* images are sourced from a local directory
* pick images randomly or sequentially
* remember the list of already processed images so that each is posted only once
* append text tags like #gif or #video depending on media type
* read the Info-DB for extra data like description and source
* custom text and tags to add with every image
* generate tags from the names of subdirectories. E.g. if path to image is a/b/image.jpg then append extra tags: #a #b
* mark posts as sensitive
* skip files it does not recognize
* downscale too large images to 2048 pixels
* retry on server failures


## Quick Start

0. Install prerequisites:
```
$ cd mastodon_imgbot
$ pip3 install -r requirements.txt
```

1.  Copy `default.config.yaml` to `config.yaml` and edit accordingly.
    The script expects `config.yaml` to be in the current directory.
2.  Generate client secret and access token for your application by visiting
    `https://your_mastodon_instance/settings/applications` and clicking "New app".
3.  Copy `default.secrets.yaml` to the location specified in `config.yaml`
    (default: `secrets.yaml`) and substitute the placeholder text with
    the secret tokens you received on previous step.

Invocation is as simple as:
```
$ python bot.py
```
This will post the next image and return immediately.


## Info-DB
Info-DB is an optional feature. The image does not need to have an entry in the Info-DB to be posted.
It is a json file with list of items as follows
```json
{
    // item 1
    "relative/path/to/file.jpg": {
        "id": 1,
        "desc": "Description",
        "source": [
            "Source String 1",
            "Source String 2",
            "http://source/url/1",
            "http://source/url/2"
        ]
    },
    // item 2
    "relative/path/to/other/file.jpg": {
        ...
    },
    ...
}
```
All fields in an item are optional. `source` may contain arbitrary number of strings. Multiple source entries are concatenated with '|'.
Path must be relative to `image_dir` from `config.yaml`


## Running automatically

To post at regular intervals it can be made into a systemd service.
Copy-paste into `/etc/systemd/system/mastodon_imgbot.service`
Edit `User`, `WorkingDirectory` and path to script in `ExecStart` appropriately.
```
[Unit]
Description=Mastodon Image Bot
Requires=network.target
After=network.target

[Service]
Type=oneshot
User=bot
WorkingDirectory=/home/bot
ExecStart=/usr/bin/python /opt/mastodon_imgbot/bot.py
```

Copy-paste into `/etc/systemd/system/mastodon_imgbot.timer`
```
[Unit]
Description=Timer for Mastodon Image Bot

[Timer]
OnBootSec=15min
OnUnitActiveSec=4h

[Install]
WantedBy=timers.target
```

To install:
```
# systemctl enable mastodon_imgbot.timer
# systemctl start mastodon_imgbot.timer
```

## Related projects
* https://github.com/err4nt/mastodon_imgbot - a very basic mastodon image bot
* https://git.drycat.fr/Dryusdan/masto-image-bot  - a sophisticated mastodon bot with multiple modes of operation