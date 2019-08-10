#! /root/copartbot/env/bin/python2.7

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as bs
from telebot.types import InputMediaPhoto, InputMediaVideo
from pastebin_python import PastebinPython
from github import Github
from github.InputFileContent import InputFileContent
import requests, re, time, json, numpy as np, pandas as pd, os, glob, sys, urllib, telebot


# pastebin api Car_info
pbin_token = ""
pbin = PastebinPython(api_dev_key=pbin_token)

# github python api
git_key = ''
g = Github(git_key)

# bot info
telebot_token = ""
bot = telebot.TeleBot(telebot_token)
chat_id = ""

#chromeDriver_path = "./chromedriver"
#chromeApp_path = "/usr/bin/chromium-browser"
chromeDriver_path = "C:\\Users\\Administrator\\Documents\\copartbot\\chromedriver_win.exe"
chromeApp_path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
window_size = "1920, 1080"
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument("--window-size=%s" % window_size)
chrome_options.binary_location = chromeApp_path
browser = webdriver.Chrome(executable_path=chromeDriver_path, chrome_options=chrome_options)

def restart_browser():
    global browser
    browser.quit()
    browser = webdriver.Chrome(executable_path=chromeDriver_path, chrome_options=chrome_options)

def get_yard_urls():
    yard_urls = []
    url = "https://www.copart.com/salesListResult/"
    locations = ["NC - Raleigh", "NC - Mebane", "NC - Mocksville", "NC - China Grove"]
    try:
        browser.get(url)
    except:
        restart_browser()
        browser.get(url)
    time.sleep(5)
    html = browser.page_source
    soup = bs(html, 'html.parser')
    tr = str(soup.find_all('tr'))
    try:
        loc1 = re.findall(r'/saleListResult/.{,20}location=%s.{60,100}54"' % locations[0], tr)[0][:-1]
    except:
        loc1 = None
    try:
        loc2 = re.findall(r'/saleListResult/.{,20}location=%s.{60,100}154"' % locations[1], tr)[0][:-1]
    except:
        loc2 = None
    try:
        loc3 = re.findall(r'/saleListResult/.{,20}location=%s.{60,100}196"' % locations[2], tr)[0][:-1]
    except:
        loc3 = None
    try:
        loc4 = re.findall(r'/saleListResult/.{,20}location=%s.{60,100}41"' % locations[3], tr)[0][:-1]
    except:
            loc4 = None
    for loc in [loc1, loc2, loc3, loc4]:
        if loc != None:
            yard_urls.append("https://www.copart.com" + str(loc))
        else:
            yard_urls.append(None)
    return(yard_urls)

def set_100_results_per_page(browser):
    ele = browser.find_element(By.XPATH, "//div[@id='serverSideDataTable_length']/label/select[@name='serverSideDataTable_length']")
    ele.click()
    ele.send_keys(u'\ue015')
    ele.send_keys(u'\ue015')
    ele.send_keys(u'\ue007')

def list_query_pages(search_url):
    while True:
        try:
            browser.get(search_url)
            time.sleep(2)
            set_100_results_per_page(browser)
            time.sleep(2)
            break
        except:
            restart_browser()
            time.sleep(2)
            continue
    html = browser.page_source
    soup = bs(html, 'html.parser')
    pages = str(soup.find_all('li'))
    page_nums = re.findall(r'tabindex="0">\d{,5}<', pages)
    page_list = []
    [page_list.append(re.findall(r'>.+<', i)[0][1:-1]) for i in page_nums]
    page_list = list(dict.fromkeys(page_list))
    last_page = np.max(np.array(page_list).astype(np.int))
    page_array = np.arange(1, last_page+1)
    return(page_array)

def get_lot_year_make_model(search_url, page_array):
    lymm = []
    for page in page_array:
        while True:
            try:
                browser.get(search_url + "&page=%s" % page)
                time.sleep(3)
                break
            except:
                print('DEBUG: selenium browser failure. restarting and trying again...')
                restart_browser()
                continue
        soup = bs(browser.page_source, 'html.parser')
        tr = str(soup.find_all('tr'))
        raw_list = re.findall(r'href="./lot/\d+".{,1025}lotsearchItemnumber', tr)
        for i in raw_list:
            try:
                lot_number = re.findall(r'./lot/\d+"', i)[0][6:-1]
                year = re.findall(r'lotsearchLotcenturyyear">\d+<', i)[0][25:-1]
                make = re.findall(r'lotsearchLotmake">[a-z, A-Z, \d, \S]{,15}</span', i)[0][18:-6]
                # get first word of model section b/c includes both bodel and variant
                model = re.findall(r'lotsearchLotmodel">[a-z, A-Z, \d, \S]{,15}</span', i)[0][19:-6]
                lymm.append((lot_number, year, make, model))
            except Exception as e:
                print('DEBUG: failed regex at index %s: \n%s' %(raw_list.index(i), e))
                lymm.append((None, None, None, None))
                pass
        print('STATUS: %s of %s pages have been parsed' %(page, len(page_array)))
    return(lymm)

def get_srUrl_vin_photos_engine_cylinders_transmission_highlights(lot_number):
    try:
        search = requests.get("https://www.salvagereseller.com/vehicles/add_to_watch_list/%s" % lot_number)
        if '<p class="alert alert-warning">Your Watchlist is empty</p>' in search.text:
            return((None, None, None, None, None, None, None))
        soup = bs(search.text, 'html.parser')
        search_links = str(soup.find_all('a'))
        car_page_url = re.findall(r'vehicle-model" href="\S+"', search_links)[0][21:-1] + "#show-vehicle-images"
        car_page_html = requests.get(car_page_url).text
        car_page_soup = bs(car_page_html, 'html.parser')
        car_page_links = str(car_page_soup.find_all('a'))
        vin = re.findall(r'VIN=\S+"' , re.findall(r'href="https://www.instavin.com/\S+"', car_page_links)[0])[0][4:-1]
        car_page_divs = str(car_page_soup.find_all('div'))
        photos = ["https://" + i for i in re.findall(r'cs.copart.com\S+JPG', re.findall(r'class="modal fade"[\s\S]{1,1380}.JPG"', car_page_divs)[0])]
        tr = str(car_page_soup.find_all('tr'))
        try:
            engine, cylinders = re.findall(r'<td>Engine:</td>[^>]+>[^<]+</td>', tr)[0].split('td')[-2][1:-2].split()
        except:
            engine, cylinders = None, None
            try:
                engine = re.findall(r'<td>Engine:</td>[^>]+>[^<]+</td>', tr)[0].split('td')[-2][1:-2].split()[0]
            except:
                pass
            try:
                cylinders = re.findall(r'<td>Cylinders:</td>[^>]+>[^<]+</td>', tr)[0].split('td')[-2][1:-2]
            except:
                pass
        try:
            transmission = re.findall(r'<td>Transmission:</td>[^>]+>[^<]+</td>', tr)[0].split('td')[-2][1:-2].lower()
        except:
            transmission = None
        try:
            highlights = re.findall(r'<td>Highlights:</td>[^>]+>[^<]+</td>', tr)[0].split('td')[-2][1:-2].lower()
        except:
            highlights = None
        return(car_page_url, vin, photos, engine, cylinders, transmission, highlights)
    except:
        return(None, None, None, None, None, None, None)

# less efficient functions for processing records not found at salvagereseller.com
def get_partialVin_vinRefImg_bodyStyle_od(lot_number):
    while True:
        try:
            browser.get("https://www.copart.com/public/data/lotdetails/solr/" + str(lot_number))
            time.sleep(3)
            break
        except:
            print('DEBUG: get_partialVin_vinRefImg_bodyStyle_od() failed. trying again...')
            restart_browser()
            continue
    specs_json = json.loads(str(re.findall(r'>{.+}<', browser.page_source))[4:-3]) # [3:-3] on windows
    #print(json.dumps(specs_json, indent=4, sort_keys=True))
    partial_vin = re.findall(r'[^*]+', specs_json['data']['lotDetails']['fv'])[0]
    vin_ref_img = specs_json['data']['lotDetails']['tims']
    try:
        body_style = specs_json['data']['lotDetails']['bstl']
    except:
        body_style = None
    try:
        od = specs_json['data']['lotDetails']['orr']
    except:
        od = 0
    return(str(partial_vin), str(vin_ref_img), str(body_style), od)

def get_full_vin(partial_vin, vin_ref_img):
    while True:
        try:
            request = requests.get("https://dataslvg.com/online-auto-auctions-%s?" % partial_vin)
            break
        except:
            print('DEBUG: get_full_vin failed. trying again...')
            continue
    soup = bs(request.text, 'html.parser')
    page_nums = re.findall(r'data-page="."', str(soup.find_all('li')))
    page_list = []
    [page_list.append("".join(str(i) for i in re.findall(r'\d+', i))) for i in page_nums]
    pages= []
    [pages.append(int(i) + 1) for i in list(dict.fromkeys(page_list))]
    if len(pages) == 0:
        pages.append(1)
    for page in pages:
        request = requests.get("https://dataslvg.com/online-auto-auctions-%s?page=%s" % (partial_vin, str(page)))
        if vin_ref_img in request.text:
            soup = bs(request.text, 'html.parser')
            block = re.findall(r'/online-auto-auctions/.{,75}%s.{10,150}</a>' % vin_ref_img, str(soup.find_all('a')))
            return(re.findall(r'">\S{17}</a>', block[0])[0][2:-4])
    return(None)

def get_photos_engine_cylinders_transmission_highlights(lot_number):
    while True:
        try:
            browser.get("https://www.copart.com/lot/" + str(lot_number))
            time.sleep(5)
            break
        except:
            print('DEBUG: get_photos_engine_cylinders_transmission_highlights failed. trying again...')
            restart_browser()
            continue
    soup = bs(browser.page_source, 'html.parser')
    raw_urls = re.findall(r'hd-url="http\S+JPG', str(soup.find_all('img')))
    img_urls = list(dict.fromkeys([i[8:] for i in raw_urls]))
    divs = str(soup.find_all('div'))
    try:
        engine, cylinders = re.findall(r'data-uname="lotdetailEnginetype">.{,10}</span>', divs)[0][33:-7].split()
    except:
        engine, cylinders = None, None
        try:
            engine = re.findall(r'data-uname="lotdetailEnginetype">.{,10}</span>', divs)[0][33:-7].split()[0]
        except:
            pass
        try:
            cylinders = re.findall(r'data-uname="lotdetailCylindervalue">.{,10}</span>', divs)[0][36:-7]
        except:
            pass
    try:
        transmission = re.findall(r'<label data-uname="">Transmission:</label>[^>]+>[A-Z, a-z, \s]+</span>', divs)[0].split("data-uname")[-1][4:-7].lower()
    except:
        transmission = None
    try:
        highlights = re.findall(r'data-uname="lotdetailHighlights"[\s\S]{1,300}<a', divs)[0].split('iconCodesObjArray')[-1][16:-16].lower()
    except:
        highlights = None
    return(img_urls, engine, cylinders, transmission, highlights)

def get_ymms_power(vin):
    request = requests.get("https://vpic.nhtsa.dot.gov/api/vehicles/decodevinextended/%s?format=json" % vin)
    json_object = json.loads(request.text)
    for dict in json_object['Results']:
        if dict['Variable'] == "Model Year":
            year = dict['Value']
        if dict['Variable'] == "Make":
            make = dict['Value']
        if dict['Variable'] == "Model":
            model = dict['Value']
        try:
            if dict['Variable'] == "Series":
                series = dict['Value']
        except:
            series = None
            pass
    try:
        for dict in json_object['Results']:
            if dict['Variable'] == "Engine Brake (hp)":
                hp=int(dict['Value'])
    except:
        hp=None
    return(year, make, model, series, hp)

def get_local_power(car_specs, year, make, model, hp_ratio, torque_ratio):
    # check if first word of model is in csv
    if len(re.findall(r'\d', str(model))) > 0:
        model_first_word = re.search(r'(\d)+', str(model)).group(0)
    elif '-' in model:
        model_first_word = str(model).split('-')[0].split()[0]
    else:
        model_first_word = str(model).split()[0]
    if float(year) >= 1990:
        """returns unique array of horsepower values for all variants of a model."""
        makes = car_specs[car_specs.Year == int(year)][car_specs.Make == "-".join(make.lower().split(" "))]
        filtered = makes[makes.Model.str.contains(model_first_word.lower())]
        if len(filtered) == 0:
            filtered = makes[makes.Variant.str.contains(model_first_word.lower())]
        hp = np.array(filtered.Horsepower).astype(int)
        torque = np.array(filtered.Torque).astype(int)
        unique_hp_torque = zip(np.sort(np.unique(hp)), np.sort(np.unique(torque)))
        if len(unique_hp_torque) == 0:
            return(None, None, None, None)
        weight = np.array(filtered['Curb weight']).astype(int)
        hp_weight_ratio = np.array(map(float, hp))*10/np.array(map(float, weight))
        torque_weight_ratio = np.array(map(float, torque))*10/np.array(map(float, weight))
        high_hp_ratios = [round(i, 2) for i in hp_weight_ratio[np.logical_and(np.logical_and(hp_weight_ratio > hp_ratio, hp_weight_ratio < 5), np.logical_and(torque_weight_ratio > torque_ratio, torque_weight_ratio < 5))]]
        high_torque_ratios = [round(i, 2) for i in torque_weight_ratio[np.logical_and(np.logical_and(hp_weight_ratio > hp_ratio, hp_weight_ratio < 5), np.logical_and(torque_weight_ratio > torque_ratio, torque_weight_ratio < 5))]]
        high_ratios = zip(high_hp_ratios, high_torque_ratios)
        high_ratio_variant_urls = np.array(filtered[np.logical_and(np.logical_and(hp_weight_ratio > hp_ratio, hp_weight_ratio < 5), np.logical_and(torque_weight_ratio > torque_ratio, torque_weight_ratio < 5))].URL)
        #high_ratio_variant_ids = np.array([i.rsplit('/', 1)[-1] for i in high_ratio_variant_urls])
        high_ratio_variants = np.array(filtered[np.logical_and(np.logical_and(hp_weight_ratio > hp_ratio, hp_weight_ratio < 5), np.logical_and(torque_weight_ratio > torque_ratio, torque_weight_ratio < 5))].Variant)
        return(unique_hp_torque, high_ratios, high_ratio_variant_urls, high_ratio_variants)
    else:
        return(None, None, None, None)

def check_incompleteness():
    for i in range(len(result_objects)):
        if len(result_objects[i].photos) == 0 or result_objects[i].lpm_url.split('vin=')[-1] == "None":
            return('incomplete')
    return('complete')

def completeness_report():
    report = []
    for i in range(len(result_objects)):
        if len(result_objects[i].photos) == 0:
            report.append(('no photos at %s' %result_objects[i].url, i))
        if result_objects[i].lpm_url.split('vin=')[-1] == "None":
            report.append(('vin "none" in lpm_url at %s' %result_objects[i].url, i))
    return(report)

def correct_missing():
    global result_objects
    for i in range(len(result_objects)):
        if len(result_objects[i].photos) == 0:
            lot_num = result_objects[i].url.rsplit('/', 1)[-1]
            sr_url, vin, photos, engine, cylinders, transmission = get_srUrl_vin_photos_engine_cylinders_transmission(lot_num)
            if sr_url == None:
                result_objects[i].photos = get_photos_engine_cylinders_transmission_highlights(lot_num)[0]
            else:
                result_objects[i].sr_url = sr_url
                result_objects[i].photos = photos
            print('Updated photos at result %s with:\n%s' %(i + 1, result_objects[i].photos))
        if result_objects[i].lpm_url.split('vin=')[-1] == "None":
            lot_num = result_objects[i].url.rsplit('/', 1)[-1]
            sr_url, vin, photos, engine, cylinders, transmission = get_srUrl_vin_photos_engine_cylinders_transmission(lot_num)
            if sr_url == None:
                tries = 3
                while tries > 0:
                    try:
                        partial_vin, vin_ref_img, body_style, od = get_partialVin_vinRefImg_bodyStyle_od(lot_number)
                        tries = 0
                    except:
                        time.sleep(5)
                        tries -= 1
                result_objects[i].lpm_url = "http://www.luxurypreownedmotorcars.com/templates/autocheck?vin=%s" %get_full_vin(partial_vin, vin_ref_img)
            else:
                result_objects[i].sr_url = sr_url
                result_objects[i].lpm_url = "http://www.luxurypreownedmotorcars.com/templates/autocheck?vin=%s" %vin
            print('Updated vin at result %s with:\n%s' %(i + 1, result_objects[i].lpm_url.split('vin=')[-1]))

def create_telegraph_page(ymm, high_ratio_variant_urls, high_ratios, high_ratio_variants):
    ymm = "+".join(ymm.split())
    content = ['{"tag":"p","children":["(10*hp/weight, 10*torque/weight): variant"]}']
    for ind in range(len(high_ratio_variant_urls)):
        content.append('{"tag":"a","attrs":{"href":"%s"},"children":["%s: %s"]},{"tag":"br"}' % (high_ratio_variant_urls[ind], str(high_ratios[ind]), high_ratio_variants[ind]))
    content = '[%s]' % ",".join(content)
    r = requests.get('https://api.telegra.ph/createPage?access_token=52b1e0af1fc0396342aa82e50d99c3947c42e73bd9e1cf6fe67af58d382d&title=%s&author_name=copart_bot&content=%s&return_content=true' \
    %(ymm, content))
    json_object = json.loads(r.text)
    return(str(json_object["result"]["url"]))


def search_history_log_init():
    with open("search_history.log", "w") as f:
        for i in [155853360000, 155853360000, 155853360000, 155853360000]:
            f.write(str(i) + "\n")

def search_history_log_update(auction_times):
    with open("search_history.log", "w") as f:
        for time in auction_times:
            f.write(str(time) + "\n")

def log_messageId_auctionTime(messageIds_auctionTimes):
    with open("messages.log", "w") as f:
        for i in messageIds_auctionTimes:
            f.write("%s %s\n" %(i[0], i[1]))

def log_overview_summary(overview_id, summary_id):
    with open("overview_summary_ids.log", "w") as f:
        f.write('%s %s' %(overview_id, summary_id))

def log_lots_processed(lot_nums):
    with open("lots_processed.log", "w") as f:
        for lot_num in lot_nums:
            f.write('%s\n' %lot_num)

def report_error(e):
    bot.send_message(chat_id, "An error occured in line {}".format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

# define object for storing each result
class Car_info:
    def __init__(self, auction_time=int, ymm=list, url=str, sr_url=str, lpm_url=str, od=int, unique_hp_torque=list, high_ratios=list, high_ratio_variant_urls=list, high_ratio_variants=list, photos=list, series=str, act_hp=int, engine=str, cylinders=str, transmission=str, highlights=str):
        self.auction_time = auction_time
        self.ymm = ymm
        self.url = url
        self.sr_url = sr_url
        self.lpm_url = lpm_url
        self.od = od
        self.unique_hp_torque = unique_hp_torque
        self.high_ratios = high_ratios
        self.high_ratio_variant_urls = high_ratio_variant_urls
        self.high_ratio_variants = high_ratio_variants
        self.photos = photos
        self.series = series
        self.act_hp = act_hp
        self.engine = engine
        self.cylinders = cylinders
        self.transmission = transmission
        self.highlights = highlights

#car.auction_time, car.ymm, car.url, car.sr_url, car.lpm_url, car.od, car.unique_hp_torque, car.high_ratios, car.high_ratio_variant_urls, car.high_ratio_variants, car.photos, car.series, car.act_hp, car.engine, car.cylinders, car.transmission, car.highlights

# find auctions most proximal in both distance and time of cars having hp > 250
# check for log. init if doesn't exist
try:
    auction_times_parsed = open("search_history.log").read().split("\n")[:-1]
except:
    search_history_log_init()
    auction_times_parsed = open("search_history.log").read().split("\n")[:-1]

try:
    messageId_auctionTime_log = open("messages.log").read().split("\n")[:-1]
except:
    messageId_auctionTime_log = []

messageIds_auctionTimes = [tuple(map(int, i.split(' '))) for i in messageId_auctionTime_log]

# delete overview and summary messages from previous run
try:
    prev_overview_summary_ids = open("overview_summary_ids.log").readlines()[0].split()
except:
    log_overview_summary("None", "None")
    prev_overview_summary_ids = open("overview_summary_ids.log").readlines()[0].split()
for msg_id in prev_overview_summary_ids:
    if msg_id != "None":
        bot.delete_message(chat_id, msg_id)

# establish which lots have already been analyzed
try:
    lot_nums = open("lots_processed.log").readlines()[:-1]
except:
    log_lots_processed([])
    lot_nums = open("lots_processed.log").readlines()[:-1]

# init temp dir for downloading images
if not os.path.exists('temp'):
    os.makedirs('temp')

#car_specs = pd.read_csv("C:\\Users\philip\\Documents\\Development\\Python\\copartBot\\specs.csv")
car_specs = pd.read_csv("./specs.csv")
#bodies = ['2DR SPOR', '3DR EXT', '4DR EXT', '4DR SPOR', 'ALL TERR', 'BUS', 'CARGO VA', 'CHASSIS', 'CLUB CAB', 'CLUB CHA', 'CONVENTI', 'CONVERTI', 'COUPE', 'COUPE 3D', 'CREW CHA', 'CREW PIC', 'CUTAWAY', 'DIRT', 'ENDURO', 'EXTENDED', 'FIRE TRU', 'FORWARD', 'GLIDERS', 'HATCHBAC', 'HEARSE', 'INCOMP P', 'INCOMPLE', 'LIFTBACK', 'LIMOUSIN', 'MOTO CRO', 'MOTOR SC', 'MOTORIZE', 'PICKUP', 'RACER', 'ROAD/STR', 'ROADSTER', 'SEDAN 2', 'SEDAN 4D', 'SPORT PI', 'SPORTS V', 'STATION', 'STEP VAN', 'TANDEM', 'TILT CAB', 'TRACTOR', 'UTILITY']

#bikes = ['DIRT', 'ENDURO', 'MOTO CRO', 'RACER', 'ROAD/STR', ]

#cars = ['2DR SPOR', '4DR SPOR', 'CONVERTI', 'COUPE', 'COUPE 3D', 'HATCHBAC', 'LIFTBACK', 'ROADSTER', 'SEDAN 2', 'SEDAN 4D', 'STATION', 'UTILITY']

search_bodies = ['2DR SPOR', 'CONVERTI', 'COUPE', 'COUPE 3D', 'HATCHBAC', 'LIFTBACK', 'ROADSTER', 'SEDAN 2', 'SEDAN 4D', 'STATION']
# init output array and aution times to be logged
result_objects, auction_times, evaluate = [], [], []
local_hp_not_found = []
total_processed = 0
hours_before = 155
prat_cutoff = 0.85
trat_cutoff = 0.75
od_cutoff = 150000

restart_browser()
time.sleep(2)
while True:
    try:
        yard_urls = get_yard_urls()
        break
    except:
        print("\nDEBUG: Headless browser function failed. Restarting browser and trying again...\n")
        restart_browser()
        continue

for i in yard_urls:
    if i == "None":
        auction_times.append(auction_times_parsed[yard_urls.index(i)])
    else:
        auction_times.append(int(i.rsplit('saleDate=', 1)[-1].split('&amp', 1)[0])/1000)
hours_left = [round((i - time.time())/60/60, 2) for i in auction_times]
for i in hours_left:
    if i < hours_before and i > 0 and int(auction_times[hours_left.index(i)]) != int(auction_times_parsed[hours_left.index(i)]):
        evaluate.append("*")
    else:
        evaluate.append(" ")

start_msg = """
Run Overview:
Searching auctions beginning within %s hours
Filtering cars by:
od < %sk
10*hp/weight > %s
10*torque/weight > %s

Sites marked with '*' will be analyzed
Next auctions will be in x hours:
[%s] NC - Raleigh: %s
[%s] NC - Mebane: %s
[%s] NC - Mocksville: %s
[%s] NC - China Grove: %s
""" %(hours_before, int(od_cutoff)/1000, prat_cutoff, trat_cutoff, evaluate[0], hours_left[0], evaluate[1], hours_left[1], evaluate[2], hours_left[2], evaluate[3], hours_left[3])
print(start_msg)
overview_id = bot.send_message(chat_id, start_msg).message_id

try:
    for yard_ind in range(len(yard_urls)):
        if yard_urls[yard_ind] != None:
            # only assess auction if it is in 'hours_before' or less hours. lot numbers are obtained for each auction site for all runs; only non-analyzed sites are analyzed -- allows for
            # newly posted cars to be added to bot chat
            auction_time = auction_times[yard_ind]
            if 0 < (auction_time - time.time()) <= 60*60*hours_before:
                auction_times_parsed[yard_ind] = auction_time
                while True:
                    try:
                        # get lot numbers and year, make, and model info for all cars in a particular yard
                        print("\nSTATUS: Determining number of result pages for yard %s\n" % (yard_ind + 1))
                        page_array = list_query_pages(yard_urls[yard_ind])
                        lot_year_make_model = get_lot_year_make_model(yard_urls[yard_ind], page_array)
                        total_processed += len(lot_year_make_model)
                        print('STATUS: Done parsing result pages for yard %s\n' %(yard_ind + 1))
                        break
                    except Exception as e:
                        print("\nDEBUG: Failed fetching lot numbers or ymm info with error below. Trying again..: \n%s" %e)
                        continue
                print("STATUS: Processing result pages for yard %s\n" % (yard_ind + 1))
                for ind in range(len(lot_year_make_model)):
                    # save a car's info as a Car_info object if horsepower, body_style, and od conditions are met
                    if (ind +1) % 5 == 0:
                        print("STATUS: result %s of %s is being processed/passed if previously processed" %(ind +1, len(lot_year_make_model)))
                    lot_number, year, make, model = lot_year_make_model[ind][0], lot_year_make_model[ind][1], lot_year_make_model[ind][2], lot_year_make_model[ind][3]
                    if lot_number in lot_nums:
                        continue
                    else:
                        lot_nums.append(lot_number)
                        if all(i != None for i in [lot_number, year, make, model]):
                            sr_url, vin, photos, engine, cylinders, transmission, highlights = get_srUrl_vin_photos_engine_cylinders_transmission_highlights(lot_number)
                            tries = 3
                            while tries > 0:
                                try:
                                    partial_vin, vin_ref_img, body_style, od = get_partialVin_vinRefImg_bodyStyle_od(lot_number)
                                    if vin == None or vin == "":
                                        vin = get_full_vin(partial_vin, vin_ref_img)
                                    tries = 0
                                except:
                                    time.sleep(5)
                                    tries -= 1
                            try:
                                y, mk, mod, series, act_hp = get_ymms_power(vin)
                                if all(i != None and i != "" for i in [y, mk, mod]):
                                    year, make, model = y, mk, mod
                            except:
                                pass
                            # search only vehicle types of interest
                            if body_style in search_bodies:
                                try:
                                    unique_hp_torque, high_ratios, high_ratio_variant_urls, high_ratio_variants = get_local_power(car_specs, year, make, model, hp_ratio=prat_cutoff, torque_ratio=trat_cutoff)
                                    for ind in range(len(unique_hp_torque)):
                                        if len(str(unique_hp_torque[ind][0])) > 5:
                                            unique_hp_torque[ind] = ("NA", unique_hp_torque[ind][1])
                                        elif len(str(unique_hp_torque[ind][1])) > 5:
                                            unique_hp_torque[ind] = (unique_hp_torque[ind][0], "NA")
                                except:
                                    local_hp_not_found.append([year, make, model])
                                    continue
                                if all(i != "None" and i != '[]' for i in [str(unique_hp_torque), str(high_ratios), str(high_ratio_variant_urls), str(high_ratio_variants)]):
                                    if 0 <= float(od) < od_cutoff:
                                        if not all(i != None for i in [photos, engine, cylinders, transmission, highlights]):
                                            photos, engine, cylinders, transmission, highlights = get_photos_engine_cylinders_transmission_highlights(lot_number)
                                        result_objects.append(Car_info(auction_time=auction_time, ymm=[year, make, model], url="https://www.copart.com/lot/%s" % lot_number, sr_url=sr_url, \
                                        lpm_url="http://www.luxurypreownedmotorcars.com/templates/autocheck?vin=%s" % vin, od=od, unique_hp_torque=unique_hp_torque, high_ratios=high_ratios, \
                                        high_ratio_variant_urls=high_ratio_variant_urls, high_ratio_variants=high_ratio_variants, photos=photos, series=series, act_hp=act_hp, engine=engine, cylinders=cylinders, transmission=transmission, highlights=highlights))
                                        if len(result_objects) % 5 == 0:
                                            print("\nSAVE STATUS: %s cars have been saved\n" %(len(result_objects)))
                                if str(unique_hp_torque) == "None":
                                    local_hp_not_found.append([year, make, model])
            else:
                print("STEP: Skipping yard %s. Either no auction within %s hours, or yard has already been parsed" % (yard_ind + 1, hours_before))
except Exception as e:
    report_error(e)
    raise

log_lots_processed(lot_nums)

print("\nPreliminary completeness report:", completeness_report())
# populate missing result fields
if "*" in evaluate:
    passes = 3
    while passes > 0:
        if check_incompleteness() == 'incomplete':
            try:
                print('STATUS: Fields missing for some results. Reattempting to populate')
                correct_missing()
                time.sleep(5)
                passes -= 1
            except:
                print('Attempting to populate missing result fields failed. trying again...')
                time.sleep(5)
                passes -= 1
        else:
            print('STATUS: All results are complete in their fields')
            passes = 0

if check_incompleteness() == 'incomplete':
    print('NOTE: Empty fields could not be populated for some results')
report = completeness_report()
print("\nPost-fix completeness report: \n", report)
print('Any incomplete results will be resent if > 48 hrs remain before auction, else they will be sent as is')
passed = []
for i in report:
    time_left = (time.time() - int(result_objects[i[1]].auction_time))/60/60
    if 0 < time_left < 48:
        continue
    elif time_left > 48:
        passed.append(lot_nums.pop(lot_nums.index(str(result_objects[i[1]].url).rsplit('/', 1)[-1])))
print("%s results were incomplete and not sent" %len(passed))

print("\nSUMMARY: %s cars were processed; %s were saved" %(total_processed, len(result_objects)))
browser.quit()
search_history_log_update(auction_times_parsed)
print('SUMMARY: hp not found locally for %s potential cars, which are listed below: \n' %len(local_hp_not_found))
print(local_hp_not_found)
summary_id = bot.send_message(chat_id, "SUMMARY: [%s potential cars](%s) could not be analyzed" %(len(local_hp_not_found), pbin.createPaste(api_paste_code =str(local_hp_not_found), api_paste_format ='html5', api_paste_private =0, api_paste_expire_date='1M')), parse_mode="markdown")
if len(result_objects) > 0:
    summary_id = bot.send_message(chat_id, "SUMMARY: %s cars were processed; %s were saved" %(total_processed, len(result_objects))).message_id
else:
    summary_id = "None"
log_overview_summary(overview_id, summary_id)

# blast telegram bot
if len(result_objects) > 0:
    try:
        prev_msg_send_time = time.time()
        for car in result_objects:
            if len(car.photos) == 0:
                continue
            else:
                tries = 2
                while tries > 0:
                    try:
                        filenames = [url.rsplit('/', 1)[1] for url in car.photos]
                        s = requests.Session()
                        for ind in range(len(car.photos)):
                            r = s.get(car.photos[ind])
                            with open('./temp/%s' % filenames[ind], 'wb') as f:
                                f.write(r.content)
                        ymm = [str(i) for i in car.ymm]
                        # send 'no image available' image for cars missing images, of the 10 expected
                        if len(filenames) != 10:
                            r = s.get("https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/1024px-No_image_available.svg.png")
                            with open('./temp/not_found', 'wb') as f:
                                f.write(r.content)
                            while len(filenames) < 10:
                                filenames.append("not_found")
                        markdown_variants = "[worthy variants](%s)" % create_telegraph_page(" ".join(ymm), car.high_ratio_variant_urls, car.high_ratios, car.high_ratio_variants)
                        unique_hp_torque = []
                        if car.act_hp != None:
                            for i in car.unique_hp_torque:
                                if i[0] == car.act_hp:
                                    unique_hp_torque.append("*%s*" % str(i))
                                else:
                                    unique_hp_torque.append(i)
                            unique_hp_torque = ", ".join(map(str, unique_hp_torque))
                        else:
                            unique_hp_torque = car.unique_hp_torque
                        curr_time = time.time()
                        while curr_time - prev_msg_send_time < 4:
                            time.sleep(1)
                            curr_time = time.time()
                        with open('./temp/%s' % filenames[0], 'rb') as f1, open('./temp/%s' % filenames[1], 'rb') as f2, open('./temp/%s' % filenames[2], 'rb') as f3, open('./temp/%s' % filenames[3], 'rb') as f4, open('./temp/%s' % filenames[4], 'rb') as f5, open('./temp/%s' % filenames[5], 'rb') as f6, open('./temp/%s' % filenames[6], 'rb') as f7, open('./temp/%s' % filenames[7], 'rb') as f8, open('./temp/%s' % filenames[8], 'rb') as f9, open('./temp/%s' % filenames[9], 'rb') as f10:
                            messages = bot.send_media_group(chat_id, media=[InputMediaPhoto(f1, caption="%s \nseries: %s \nengine: %s \ncylinders: %s \ntransmission: %s \nodometer: %s \nstate: %s \nhp, torque: \n%s \n[copart post](%s) \n[price history](%s) \n[vin report](%s) \n%s" %(" ".join(ymm), car.series, car.engine, car.cylinders, car.transmission, "{:,}".format(int(car.od)), car.highlights, unique_hp_torque, car.url, car.sr_url, car.lpm_url, markdown_variants), parse_mode="markdown"), InputMediaPhoto(f2), InputMediaPhoto(f3), InputMediaPhoto(f4), InputMediaPhoto(f5), InputMediaPhoto(f6), InputMediaPhoto(f7), InputMediaPhoto(f8), InputMediaPhoto(f9), InputMediaPhoto(f10)], disable_notification=True)
                            #print('Result %s of %s successfully sent as copart_alert on telegram' %(result_objects.index(car) + 1, len(result_objects)))
                            for msg in messages:
                                if (msg.message_id, car.auction_time) not in messageIds_auctionTimes:
                                    messageIds_auctionTimes.append((msg.message_id, car.auction_time))
                        tries = 0
                    except Exception as e:
                        print(car.auction_time, car.ymm, car.url, car.sr_url, car.lpm_url, car.od, car.unique_hp_torque, car.high_ratios, car.high_ratio_variant_urls, car.high_ratio_variants, car.photos, car.series, car.act_hp, car.engine, car.cylinders, car.transmission, car.highlights)
                        if "JSON" not in str(e):
                            print(e)
                            report_error(e)
                        tries -= 1
                        time.sleep(3)
                        if tries == 0:
                            print("\nDEBUG: the following exception was thrown at iteration %s of blasting telegram: \n%s " %(result_objects.index(car) + 1, e))
                            print('STATUS: Telegraph 64 kb limit likely exceded. Attempting to push variant info to gist and resend message')
                            try:
                                markdown_variants = ["[%s: %s](%s)<br/>" % (car.high_ratios[ind], car.high_ratio_variants[ind], car.high_ratio_variant_urls[ind]) for ind in range(len(car.high_ratios))]
                                markdown_variants = "(10*hp/weight, 10*torque/weight): variant<br/>" + "".join(markdown_variants)
                                gist_url = "https://gist.github.com/" + str(g.get_user().create_gist(public=True, files={"" : InputFileContent(content = markdown_variants, new_name ='%s.md' % " ".join(ymm))}, description='cp variant info')).split('"')[-2]
                                with open('./temp/%s' % filenames[0], 'rb') as f1, open('./temp/%s' % filenames[1], 'rb') as f2, open('./temp/%s' % filenames[2], 'rb') as f3, open('./temp/%s' % filenames[3], 'rb') as f4, open('./temp/%s' % filenames[4], 'rb') as f5, open('./temp/%s' % filenames[5], 'rb') as f6, open('./temp/%s' % filenames[6], 'rb') as f7, open('./temp/%s' % filenames[7], 'rb') as f8, open('./temp/%s' % filenames[8], 'rb') as f9, open('./temp/%s' % filenames[9], 'rb') as f10:
                                    messages = bot.send_media_group(chat_id, media=[InputMediaPhoto(f1, caption="%s \nseries: %s \nengine: %s \ncylinders: %s \ntransmission: %s \nodometer: %s \nstate: %s \nhp, torque: \n%s \n[copart post](%s) \n[price history](%s) \n[vin report](%s) \n[worthy variants](%s)" %(" ".join(ymm), car.series, car.engine, car.cylinders, car.transmission, "{:,}".format(int(car.od)), car.highlights, unique_hp_torque, car.url, car.sr_url, car.lpm_url, gist_url), parse_mode="markdown"), InputMediaPhoto(f2), InputMediaPhoto(f3), InputMediaPhoto(f4), InputMediaPhoto(f5), InputMediaPhoto(f6), InputMediaPhoto(f7), InputMediaPhoto(f8), InputMediaPhoto(f9), InputMediaPhoto(f10)], disable_notification=True)
                            except Exception as x:
                                print('DEBUG: Failed at gist step for the following reason: \n%s' %x)
                                report_error(x)
                                print('DEBUG: the gist url was: \n%s' %gist_url)
                    finally:
                        prev_msg_send_time = time.time()
                        temp_files = glob.glob("./temp/*")
                        for f in temp_files:
                            os.remove(f)
    except Exception as e:
        report_error(e)

# clean up bot chat
# try:
#     for message in messageIds_auctionTimes:
#         if time.time() + 100000000000 > message[1]:
#             bot.delete_message(chat_id, message[0])
#             time.sleep(4)
#             messageIds_auctionTimes.pop(messageIds_auctionTimes.index(message))
#     log_messageId_auctionTime(messageIds_auctionTimes)
# except Exception as e:
#     print('DEBUG: Deleting outdated messages failed for the following reason: \n%s' %e)
#     report_error(e)
