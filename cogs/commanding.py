from code import interact
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.app_commands import checks, MissingPermissions
from datetime import timedelta, datetime
from typing import List
from discord_webhook import AsyncDiscordWebhook

import aiomysql
from aiomysql.cursors import DictCursor

import time
import functools
import os, sys, traceback
from io import BytesIO
from PIL import Image
import asyncio

from pyvirtualdisplay import Display
# The selenium module
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import random

def ceil_date(date, **kwargs):
    secs = timedelta(**kwargs).total_seconds()
    return datetime.fromtimestamp(date.timestamp() + secs - date.timestamp() % secs)

def floor_date(date, **kwargs):
    secs = timedelta(**kwargs).total_seconds()
    return datetime.fromtimestamp(date.timestamp() - date.timestamp() % secs)

def get_coin360(display_id: str, static_coin360_path, selenium_setting, coin360, url: str, bg_task: bool=False):
    return_to = None
    floor_t = floor_date(datetime.now(), minutes=5) #round down 5 minutes
    if bg_task is True:
        floor_t = ceil_date(datetime.now(), minutes=5) #round down 5 minutes

    file_name = "coin360_image_{}.png".format(floor_t.strftime("%Y-%m-%d-%H-%M"))  #
    file_path = static_coin360_path + file_name
    if os.path.exists(file_path):
        return file_name

    timeout = 20
    try:
        os.environ['DISPLAY'] = display_id
        display = Display(visible=0, size=(1366, 768))
        display.start()

        options = webdriver.ChromeOptions()
        options = Options()
        options.add_argument('--no-sandbox')  # Bypass OS security model
        options.add_argument('--disable-gpu')  # applicable to windows os only
        options.add_argument('start-maximized')  #
        options.add_argument('disable-infobars')
        options.add_argument("--disable-extensions")
        userAgent = selenium_setting['user_agent']
        options.add_argument(f"user-agent={userAgent}")
        options.add_argument("--user-data-dir=chrome-data")
        options.headless = True

        driver = webdriver.Chrome(options=options)
        driver.set_window_position(0, 0)
        driver.set_window_size(selenium_setting['win_w'], selenium_setting['win_h'])

        driver.get(url)
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "SHA256")))
        WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.ID, "EtHash")))
        time.sleep(3.0)

        element = driver.find_element(By.ID, coin360['id_crop'])  # find part of the page you want image of
        location = element.location
        size = element.size
        png = driver.get_screenshot_as_png()  # saves screenshot of entire page

        im = Image.open(BytesIO(png))  # uses PIL library to open image in memory
        left = location['x']
        top = location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']
        im = im.crop((left, top, right, bottom))  # defines crop points

        im.save(file_path)  # saves new cropped image
        driver.close()  # closes the driver
        return_to = file_name
    except Exception:
        traceback.print_exc(file=sys.stdout)
    finally:
        display.stop()
    return return_to

async def log_to_channel(content: str, webhook: str) -> None:
    # log_type: withdraw, other: general
    try:
        webhook = AsyncDiscordWebhook(
            url=webhook,
            content=content[:1000]
        )
        await webhook.execute()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)

# Cog class
class Commanding(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.pool = None
        self.display_list = [f":{str(i)}" for i in range(301, 320)]

    async def open_connection(self):
        try:
            if self.pool is None:
                self.pool = await aiomysql.create_pool(
                    host=self.bot.config['mysql']['host'], port=3306, minsize=1, maxsize=2,
                    user=self.bot.config['mysql']['user'], password=self.bot.config['mysql']['password'],
                    db=self.bot.config['mysql']['db'], cursorclass=DictCursor, autocommit=True
                )
        except Exception:
            traceback.print_exc(file=sys.stdout)

    async def add_guild(self, guild_id: str, channel_id: str, by_id: str):
        try:
            await self.open_connection()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = """
                    INSERT INTO `guild_list` (`guild_id`, `channel_id`, `assigned_date`, `assigned_by_id`)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY 
                    UPDATE
                      `channel_id`=VALUES(`channel_id`),
                      `assigned_date`=VALUES(`assigned_date`),
                      `assigned_by_id`=VALUES(`assigned_by_id`)
                    """
                    await cur.execute(sql, (
                        guild_id, channel_id, int(time.time()), by_id
                    ))
                    await conn.commit()
                    return True
        except Exception:
            traceback.print_exc(file=sys.stdout)
        return False

    async def delete_guild(self, guild_id: str):
        try:
            await self.open_connection()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = """
                    DELETE FROM `guild_list` WHERE `guild_id`=%s LIMIT 1;
                    """
                    await cur.execute(sql, guild_id)
                    await conn.commit()
                    return True
        except Exception:
            traceback.print_exc(file=sys.stdout)
        return False

    async def get_guild_list(self):
        try:
            await self.open_connection()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = """
                    SELECT * FROM `guild_list`
                    """
                    await cur.execute(sql,)
                    result = await cur.fetchall()
                    if result:
                        return result
        except Exception:
            traceback.print_exc(file=sys.stdout)
        return []

    @app_commands.command(
        name='coin360channel',
        description="Set where coin360 publish to."
    )
    async def slash_set_coinmap_channel(
        self, interaction: discord.Interaction,
        channel: discord.TextChannel
    ) -> None:
        """ /coin360channel <text channel> """
        try:
            # needs member presence
            await interaction.response.send_message(f"{interaction.user.mention}, loading /coin360channel ...")
            get_user = interaction.guild.get_member(interaction.user.id)
            check_perm = dict(get_user.guild_permissions)
            if check_perm and check_perm['manage_channels'] is True:
                adding = await self.add_guild(
                    str(interaction.guild.id), str(channel.id), str(interaction.user.id)
                )
                if adding is True:
                    await interaction.edit_original_response(content=f"{interaction.user.mention}, successfully assigned {channel.mention} for coin360!")
                    await log_to_channel(
                        f"User {interaction.user.mention} successfully assigned {channel.mention} for coin360 in guild "\
                        f"{interaction.guild.name} / {interaction.guild.id}!",
                        self.bot.config['discord']['webhook']
                    )
                else:
                    await interaction.edit_original_response(content=f"{interaction.user.mention}, internal error. Please report!")    
            else:
                await interaction.edit_original_response(content=f"{interaction.user.mention}, you don't have permission. At least `manage_channels`.")
                await log_to_channel(
                    f"User {interaction.user.mention} failed to assign {channel.mention} for coin360 in guild "\
                    f"{interaction.guild.name} / {interaction.guild.id}. No permission!",
                    self.bot.config['discord']['webhook']
                )
        except Exception:
            traceback.print_exc(file=sys.stdout)

    @app_commands.command(
        name='viewcoin360',
        description="View coin360."
    )
    async def slash_view_coin360(
        self, interaction: discord.Interaction
    ) -> None:
        """ /viewcoin360 """
        await interaction.response.send_message(f"{interaction.user.mention}, loading /viewcoin360 ...")
        try:
            display_id = random.choice(self.display_list)
            self.display_list.remove(display_id)
            fetch_coin360 = functools.partial(
                get_coin360, display_id, self.bot.config['coin360']['static_coin360_path'],
                self.bot.config['selenium_setting'], self.bot.config['coin360'], self.bot.config['coin360']['url'], bg_task=False
            )
            map_image = await self.bot.loop.run_in_executor(None, fetch_coin360)
            self.display_list.append(display_id)
            if map_image:
                await interaction.edit_original_response(content=self.bot.config['coin360']['static_coin360_link'] + map_image)
            else:
                await interaction.edit_original_response(
                    content=f"{interaction.user.mention}, internal error during fetch image."
                )
            return
        except Exception:
            traceback.print_exc(file=sys.stdout)
            return

    @tasks.loop(minutes=2)
    async def update_channel_bg(self):
        try:
            await self.bot.wait_until_ready()
            guilds = await self.get_guild_list()
            display_id = random.choice(self.display_list)
            self.display_list.remove(display_id)
            fetch_coin360 = functools.partial(
                get_coin360, display_id, self.bot.config['coin360']['static_coin360_path'],
                self.bot.config['selenium_setting'], self.bot.config['coin360'], self.bot.config['coin360']['url'], bg_task=False
            )
            map_image = await self.bot.loop.run_in_executor(None, fetch_coin360)
            self.display_list.append(display_id)
            if map_image is None:
                return
            image_link = self.bot.config['coin360']['static_coin360_link'] + map_image
            if len(guilds) > 0:
                for i in guilds:
                    get_guild = self.bot.get_guild(int(i['guild_id']))
                    if get_guild is None:
                        print("🔴 {} could not find guild id: {}".format(
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), i['guild_id'],
                            self.bot.config['discord']['webhook']
                        ))
                        await log_to_channel(
                            f"🔴 [Guild] could not find guild {i['guild_id']}!",
                            self.bot.config['discord']['webhook']
                        )
                        continue
                    else:
                        channel = get_guild.get_channel(int(i['channel_id']))
                        if channel is None:
                            print("{} could not find channel id {} in guild {} / id: {}".format(
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), i['channel_id'], get_guild.name, i['guild_id']
                            ))
                            await log_to_channel(
                                f"🔴 [CHANNEL] could not find channel id {i['channel_id']} in guild {get_guild.name} / {i['guild_id']}!",
                                self.bot.config['discord']['webhook']
                            )
                            continue
                        else:
                            try:
                                try:
                                    async for message in channel.history(limit=100):
                                        if message.author.id == self.bot.user.id:
                                            try:
                                                await message.delete()
                                            except Exception as e:
                                                traceback.print_exc(file=sys.stdout)
                                except Exception as e:
                                    traceback.print_exc(file=sys.stdout)
                                # send a new message
                                await channel.send("{}".format(image_link))
                            except discord.errors.Forbidden:
                                await log_to_channel(
                                    f"🔴🔴 [PERM] no permission to send to channel id {i['channel_id']} in guild "\
                                    f"{get_guild.name} / {i['guild_id']}. Unassigned channel!",
                                    self.bot.config['discord']['webhook']
                                )
                                await self.delete_guild(i['guild_id'])
                                if get_guild is not None and get_guild.owner is not None:
                                    await get_guild.owner.send(
                                        f"I unassigned /coin360channel channel in your guild {get_guild.name} "\
                                        "because I have no permission. You can set it again anytime and "\
                                        "make sure I have permission to send message, attachment and embed!"
                                    )
                            except Exception as e:
                                traceback.print_exc(file=sys.stdout)
            else:
                print("{} there's no guild to update coin360 image...".format(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        except Exception:
            traceback.print_exc(file=sys.stdout)

    @tasks.loop(minutes=2)
    async def fetch_coin360_bg(self):
        try:
            display_id = random.choice(self.display_list)
            self.display_list.remove(display_id)
            fetch_coin360 = functools.partial(
                get_coin360, display_id, self.bot.config['coin360']['static_coin360_path'],
                self.bot.config['selenium_setting'], self.bot.config['coin360'], self.bot.config['coin360']['url'], bg_task=True
            )
            map_image = await self.bot.loop.run_in_executor(None, fetch_coin360)
            # print("{} fetching bg coin360 completed and saved {}.".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), map_image))
            self.display_list.append(display_id)
        except Exception:
            traceback.print_exc(file=sys.stdout)

    @tasks.loop(minutes=2)
    async def fetch_coin360_others(self):
        # volume_1d
        try:
            display_id = random.choice(self.display_list)
            self.display_list.remove(display_id)
            fetch_coin360 = functools.partial(
                get_coin360, display_id, self.bot.config['other_image_storage']['volume_1d'],
                self.bot.config['selenium_setting'], self.bot.config['coin360'], self.bot.config['other_coin360_link']['volume_1d'], bg_task=True
            )
            volume_1d = await self.bot.loop.run_in_executor(None, fetch_coin360)
            self.display_list.append(display_id)
        except Exception:
            traceback.print_exc(file=sys.stdout)
        await asyncio.sleep(2.0)
        # volume_1h
        try:
            display_id = random.choice(self.display_list)
            self.display_list.remove(display_id)
            fetch_coin360 = functools.partial(
                get_coin360, display_id, self.bot.config['other_image_storage']['volume_1h'],
                self.bot.config['selenium_setting'], self.bot.config['coin360'], self.bot.config['other_coin360_link']['volume_1h'], bg_task=True
            )
            volume_1h = await self.bot.loop.run_in_executor(None, fetch_coin360)
            self.display_list.append(display_id)
        except Exception:
            traceback.print_exc(file=sys.stdout)
        await asyncio.sleep(2.0)
        # mcap_1h
        try:
            display_id = random.choice(self.display_list)
            self.display_list.remove(display_id)
            fetch_coin360 = functools.partial(
                get_coin360, display_id, self.bot.config['other_image_storage']['mcap_1h'],
                self.bot.config['selenium_setting'], self.bot.config['coin360'], self.bot.config['other_coin360_link']['mcap_1h'], bg_task=True
            )
            mcap_1h = await self.bot.loop.run_in_executor(None, fetch_coin360)
            self.display_list.append(display_id)
        except Exception:
            traceback.print_exc(file=sys.stdout)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.fetch_coin360_bg.is_running():
            self.fetch_coin360_bg.start()
        if not self.update_channel_bg.is_running():
            self.update_channel_bg.start()
        if not self.fetch_coin360_others.is_running():
            self.fetch_coin360_others.start()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await log_to_channel(
            f"Bot joined a new guild {guild.name} / {str(guild.id)}.",
            self.bot.config['discord']['webhook']
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await log_to_channel(
            f"Bot removed a new guild {guild.name} / {str(guild.id)}.",
            self.bot.config['discord']['webhook']
        )

    async def cog_load(self) -> None:
        if not self.fetch_coin360_bg.is_running():
            self.fetch_coin360_bg.start()
        if not self.update_channel_bg.is_running():
            self.update_channel_bg.start()
        if not self.fetch_coin360_others.is_running():
            self.fetch_coin360_others.start()

    async def cog_unload(self) -> None:
        self.fetch_coin360_bg.cancel()
        self.update_channel_bg.cancel()
        self.fetch_coin360_others.cancel()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Commanding(bot))
