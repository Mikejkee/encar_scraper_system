import datetime
import json
import re
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC


def open_url_with_wait_elem(driver, url_to_open, selector):
    try:
        driver.execute_script(f"window.open('{url_to_open}')")
        driver.switch_to.window(driver.window_handles[-1])
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((selector['select_type'], selector['value'])))
        return driver.find_element(selector['select_type'], selector['value']).text
    except TimeoutException:
        return None
    except Exception as e:
        print(e)


def request_api_result(driver, homepage_url,  homepage_selector, api_url, api_selector):
    json_text = open_url_with_wait_elem(driver, api_url, api_selector)
    while len(json_text) == 0:
        try:
            if open_url_with_wait_elem(driver, homepage_url, homepage_selector) is not None:
                time.sleep(2)
                json_text = open_url_with_wait_elem(driver, api_url, api_selector)
        except Exception as e:
            print(e)
    return json_text


def hotmarks_parser(hotmarks_url):
    html = requests.get(hotmarks_url).content
    soup = BeautifulSoup(html, 'html.parser')

    hotmarks_info = {}
    for tag in soup.find_all('li'):
        try:
            img = tag.find('img')
            index = re.search(r'(\d+)(?=.gif)', img['src']).group(1)
            text = tag.find('span').text
            if len(text) == 0:
                text = tag.find('img')['alt']
            hotmarks_info[index] = text
        except Exception as e:
            print('hotmarks_parser: ', e)
            continue
    return hotmarks_info


def parse_car_info(api_result, search_id, search_link, hotmarks_info):
    result_car_info_list = list()
    try:
        for car_info in api_result['SearchResults']:
            car_id = car_info["Id"]
            request_timestamp = datetime.datetime.now()

            photo_list = [f"ci.encar.com{photo['location']}" for photo in car_info.get("Photos", [])]

            if 'Inspection' in car_info['Condition']:
                perfomance_record = f'encar.com/md/sl/mdsl_regcar.do?method=inspectionViewNew&carid='
            else:
                perfomance_record = ''

            services_list = []
            encar_diagnosis = ''
            trust_values = car_info['Trust']
            if len(trust_values) != 0:
                encar_diagnosis = f'encar.com/dc/dc_carsearchpop.do?method=resudtl&carid={car_id}'
                if "HomeService" in trust_values:
                    services_list.append('엔카홈서비스')
                if "ExtendWarranty" in trust_values:
                    services_list.append('엔카보증')
                if "PreDelivery" in trust_values:
                    services_list.append('미리배송')
                try:
                    if car_info['ServiceCopyCar'] == 'DUPLICATION' and car_info["HomeServiceVerification"] == "Y":
                        services_list.append('즉시출고')
                except KeyError:
                    pass

            hotmarks_str = car_info.get("Hotmark", "")
            hotmarks_list = ""
            if hotmarks_str != "":
                hotmarks_list = [hotmarks_info[str(hotmark)] for hotmark in hotmarks_str.split(';')]

            price_notes = {}
            car_keys = car_info.keys()
            for key in ['LeaseType', 'SalesStatus', 'MonthLeasePrice', 'Deposit']:
                if key in car_keys:
                    price_notes[key] = car_info[key]

            result_car_info_list.append(
                {
                    'search_id': search_id,
                    'search_link': search_link,
                    'car_id': car_id,
                    'link': f'encar.com/dc/dc_cardetailview.do?carid={car_id}',
                    'sort_type': re.search('(?<=sort%22%3A%22).*?(?=%22)', search_link)[0],
                    'brand': car_info.get("Manufacturer", ''),
                    'model': car_info.get("Model", ''),
                    'equipment': car_info.get("Badge", ''),
                    'manufacture_date': car_info.get("Year", ''),
                    'model_year': car_info.get("FormYear", ''),
                    'mileage': car_info.get("Mileage", ''),
                    'fuel': car_info.get("FuelType", ''),
                    'location': car_info.get("OfficeCityState", ''),
                    'marketing_description': car_info.get("Powerpack", car_info.get("AdWords", '')),
                    'hotmarks': json.dumps(hotmarks_list, ensure_ascii=False),
                    'price': car_info.get("Price", ''),
                    'price_notes': json.dumps(price_notes, ensure_ascii=False),
                    'services': json.dumps(services_list, ensure_ascii=False),
                    'photo_urls': json.dumps(photo_list),
                    'perfomance_record_url': perfomance_record,
                    'encar_diagnosis_url': encar_diagnosis,
                    'parsing_time': request_timestamp.__str__()
                }
            )
    except Exception as e:
        print(e)

    return result_car_info_list


def get_encar_data(search_id, search_link):
    """
           Открываем главную страницу сайта, как она загружается открываем апишку, если она
           отрабатывает забираем ее, далее забираемм все с помощью апи и селениума, при этом если апи не отрабатывает -
           заново открываем главную страницу
       """

    # Установка заголовков и куков
    ua = UserAgent()

    options = webdriver.FirefoxOptions()
    options.add_argument("-profile")
    options.add_argument(r"C:\Users\Mike\AppData\Local\Mozilla\Firefox\Profiles\ng7nos3t.default-release")
    options.set_preference("general.useragent.override", ua.firefox)
    options.set_preference("media.navigator.enabled", True)
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("geo.enabled", True)
    options.set_preference("disable-blink-features", 'AutomationControlled')
    options.set_preference("excludeSwitches", "enable-automation")
    options.set_preference('useAutomationExtension', False)
    options.set_preference('devtools.jsonview.enabled', False)
    options.set_preference("dom.disable_open_during_load", False)
    options.set_preference('marionette', False)

    driver = webdriver.Firefox(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.maximize_window()
    driver.set_page_load_timeout(30)
    # driver = uc.Chrome()

    # Так как выдает апишка максимум 300 значений (начиная с 0), то выгялядит конец ссылки именно так
    api_request_count = 300
    end_api_link = f'0%7C{api_request_count - 1}'

    homepage_url = 'http://www.encar.com/'
    api_selector = {'select_type': By.TAG_NAME, 'value': 'pre'}
    homepage_selector = {'select_type': By.ID, 'value': 'indexSch'}
    query = re.search('action%22%3A%22(\(.*\))', search_link)[1]
    api_format_url = f"http://api.encar.com/search/car/list/premium?count=true&q={query}&sr=%7CModifiedDate%7C"

    hotmarks_info = hotmarks_parser('http://www.encar.com/dc/dc_carsearch_v13_pp0.htm')
    parsing_result_card_list = list()
    try:
        api_result = json.loads(request_api_result(driver, homepage_url, homepage_selector,
                                                   f'{api_format_url}{end_api_link}', api_selector))
        count_value = int(api_result['Count'])

        for count in range(0, int(count_value), api_request_count):
            end_api_link = f"{count}%7C{api_request_count-1}"

            # Если не первый проход, то запрашиваем новые данные
            if count != 0:
                api_result = json.loads(request_api_result(driver, homepage_url, homepage_selector,
                                                           f'{api_format_url}{end_api_link}', api_selector))

            parsing_result_card_list += parse_car_info(api_result, search_id, search_link, hotmarks_info)

    except Exception as e:
        print(e)

    driver.quit()
    return parsing_result_card_list


if __name__ == '__main__':
    url = "http://www.encar.com/dc/dc_carsearchlist.do?carType=kor#!%7B%22action%22%3A%22(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.%EA%B8%B0%EC%95%84._.(C.ModelGroup.%EC%B9%B4%EB%8B%88%EB%B0%9C._.Model.%EC%B9%B4%EB%8B%88%EB%B0%9C%204%EC%84%B8%EB%8C%80.))))%22%2C%22toggle%22%3A%7B%7D%2C%22layer%22%3A%22%22%2C%22sort%22%3A%22ModifiedDate%22%2C%22page%22%3A10%2C%22limit%22%3A20%2C%22searchKey%22%3A%22%22%2C%22loginCheck%22%3Afalse%7D"
    print(len(get_encar_data(12, url)))
