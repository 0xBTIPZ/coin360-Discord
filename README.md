<p align="center">
  <img width="180" src="./BTIPZ.png" alt="Coin360 Bot">
  <h1 align="center">Unofficial Coin360 Scrape Bot</h1>
</p>

<!-- Table of Contents -->

<summary><h2 style="display: inline-block">Table of Contents</h2></summary>
<ul>
    <li><a href="#intro">Intro</a></li>
    <li><a href="#our-discord">Our Discord</a></li>
    <li><a href="#setup">Setup</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#credit-and-thanks-to">Credit and thanks to</a></li>
</ul>

### Intro

The Bot will screenshot from <http://coin360.com/> and keep posting to designated channel. There are only two commands `/viewcoin360` and `/coin360channel` (for Discord guild moderator).

* Invite link <https://discord.com/oauth2/authorize?client_id=1099642526501183528&scope=bot+applications.commands&permissions=2147534848>

![Screenshot](https://github.com/0xBTIPZ/coin360-Discord/blob/main/screenshot.jpg?raw=true)

### Our Discord

* BTIPZ: <http://join.btipz.com>

## Setup

You need to create a Bot through [Discord Application](https://discord.com/developers/applications). You need to run with either python3.8 or python3.10 with virtualenv.

* Copy `config.toml.sample` to `config.toml` and edit as necessary
* Create database in MariaDB / MySQL and import `database.sql`

```
# You need this package
sudo apt-get install xvfb -y
# Python requirement
virtualenv -p /usr/bin/python3.10 ./
source bin/activate
pip3 install -r requirements.txt
python3 Coin360Bot.py
```

If you run with pm2 (process monitor):

```
pm2 start `pwd`/Coin360Bot.py --name "COIN360-DISCORD" --interpreter=python3.10
```

Feel free to join [our Discord](http://join.btipz.com) if you need to run your own and has any issue.

## Contributing

Please feel free to open an issue for any suggestions.

### Credit and thanks to:

* <https://www.coin360.com/> Coin360.