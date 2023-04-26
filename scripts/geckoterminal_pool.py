import time
import functools
import os, sys, traceback
import os.path
from io import BytesIO
from PIL import Image
from datetime import timedelta, datetime

from pyvirtualdisplay import Display
# The selenium module
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--network', dest='network', type=str, help='Set network (Example: bsc)')
parser.add_argument('--dex', dest='dex', type=str, help='Set DEX (Example: PCS)')
parser.add_argument('--pairs', dest='pairs', type=str, help='Set pairs (Example: BTIPZ-BUSD)')
parser.add_argument('--pool', dest='pool', type=str, help='Set pool contract (Example: 0x843afdc56e0c57dc8736b7380b4fc6dd4be6a570)')

args = parser.parse_args()

if not args.network:
    print("Please set --network!")
    sys.exit()

if not args.dex:
    print("Please set --dex!")
    sys.exit()

if not args.pairs:
    print("Please set --pairs!")
    sys.exit()

if not args.pool:
    print("Please set --pool!")
    sys.exit()

def ceil_date(date, **kwargs):
    secs = timedelta(**kwargs).total_seconds()
    return datetime.fromtimestamp(date.timestamp() + secs - date.timestamp() % secs)

def floor_date(date, **kwargs):
    secs = timedelta(**kwargs).total_seconds()
    return datetime.fromtimestamp(date.timestamp() - date.timestamp() % secs)

def geckoterminal_pool_screen(display_id: str, saved_path, url: str, pairs: str, dex: str, bg_task: bool=False):
    return_to = None
    floor_t = floor_date(datetime.now(), minutes=5) #round down 5 minutes
    if bg_task is True:
        floor_t = ceil_date(datetime.now(), minutes=5) #round down 5 minutes

    if not os.path.exists(saved_path):
        os.makedirs(saved_path)

    file_name = "{}_{}_{}.png".format(dex.upper(), pairs, floor_t.strftime("%Y-%m-%d-%H-%M"))  #
    file_path = saved_path + file_name
    if os.path.exists(file_path):
        return False

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
        userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        options.add_argument(f"user-agent={userAgent}")
        options.add_argument("--user-data-dir=chrome-data")
        options.add_argument("--headless")

        driver = webdriver.Chrome(options=options)
        driver.set_window_position(0, 0)
        driver.set_window_size(2048, 1080)

        driver.get(url)
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.TAG_NAME, "main")))
        time.sleep(3.0)

        element = driver.find_element(By.TAG_NAME, "main")  # find part of the page you want image of
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

while True:
    start = int(time.time())
    try:
        display_id = str(99)
        pool_contract = args.pool # "0x843afdc56e0c57dc8736b7380b4fc6dd4be6a570" # btipz-busd
        pairs = args.pairs.upper() # "BTIPZ-BUSD"
        dex = args.dex.upper() # "PCS"
        network = args.network.lower() # "bsc"
        check = geckoterminal_pool_screen(
            display_id,
            "./img_{}_{}_{}/".format(network, dex.lower(), pairs.lower()),
            "https://www.geckoterminal.com/" + network + "/pools/" + pool_contract,
            pairs,
            dex,
            bg_task=False
        )
        if check is not False:
            print("{} completed {} / {} - {}: time {}.".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), network.upper(), dex.upper(), pairs.upper(), int(time.time()) - start))
    except Exception:
        traceback.print_exc(file=sys.stdout)
    time.sleep(20.0)
