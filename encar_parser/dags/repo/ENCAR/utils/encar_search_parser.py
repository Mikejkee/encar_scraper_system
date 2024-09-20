import sys
import datetime
import json
import re
import time
from os.path import dirname, realpath

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, UnexpectedAlertPresentException, \
    NoAlertPresentException
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from airflow.utils.log.logging_mixin import LoggingMixin

begin_path = dirname(dirname(dirname(dirname(dirname(realpath(__file__))))))
sys.path.append(begin_path)

from Common.Utils.simple_utils import get_car_id_from_photo, create_undetected_chrome_driver

logger = LoggingMixin().log


def open_url_with_wait_elem(driver, url_to_open, selector):
    try:
        # Открытие в новой вкладке - работает при ("--disable-popup-blocking")
        # driver.execute_script("window.open('about:blank', '_blank');")
        # driver.switch_to.window(driver.window_handles[-1])
        driver.get(url_to_open)
        try:
            driver.find_element(By.CLASS_NAME, 'neterror')
            return ""

        except NoSuchElementException:
            start_time = time.time()
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((selector['select_type'], selector['value'])))
            end_time = time.time()

            # Ждет 60 секунд - если не было больше и это главная страница
            time_diff = end_time - start_time
            print('Timediff ', time_diff)
            if time_diff < 60 and selector['value'] == 'indexSch':
                time.sleep(60 - time_diff)

            selector_text = driver.find_element(selector['select_type'], selector['value']).text
            return selector_text

    except TimeoutException:
        return ""

    except Exception as e:
        logger.info(f'-> Ошибка {e} во время поиска селектора при заходе на страницу парсера api <-')
        raise e


def request_api_result(driver, homepage_url, homepage_selector, api_url, api_selector):
    try:
        json_text = open_url_with_wait_elem(driver, api_url, api_selector)
    except UnexpectedAlertPresentException:
        alert_screenshot_path = 'alert_screenshot.png'
        driver.save_screenshot(alert_screenshot_path)
        if driver.switch_to.alert.text:
            print(driver.switch_to.alert.text)
            driver.switch_to.alert.accept()
        time.sleep(30)
        alert_screenshot_path = 'after_alert_screenshot.png'
        driver.save_screenshot(alert_screenshot_path)
        json_text = open_url_with_wait_elem(driver, api_url, api_selector)

    try:
        while len(json_text) == 0:

            homepage_return = open_url_with_wait_elem(driver, homepage_url, homepage_selector)
            if homepage_return not in ["", False]:
                time.sleep(2)
                json_text = open_url_with_wait_elem(driver, api_url, api_selector)

        return json_text
    except Exception as e:
        logger.info(f'-> Ошибка {e} во время заходов на страницы парсера api <-')
        raise e


def hotmarks_parser(hotmarks_url):
    logger.info(f'->Запускаем парсер hotmarks <-')
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
        except TypeError:
            continue

    logger.info(f'->Парсер hotmarks - успешно отработал <-')
    return hotmarks_info


def parse_car_info(api_result, search_id, search_link, hotmarks_info, search_run_id):
    try:
        result_car_info_list = list()
        for car_info in api_result['SearchResults']:

            car_id = car_info["Id"]
            request_timestamp = datetime.datetime.now()

            photo_list = [f"ci.encar.com{photo['location']}" for photo in car_info.get("Photos", [])]
            car_id_from_photo = get_car_id_from_photo(car_id, photo_list)

            if 'Inspection' in car_info['Condition']:
                perfomance_record = f'encar.com/md/sl/mdsl_regcar.do?method=inspectionViewNew&carid={car_id_from_photo}'
            else:
                perfomance_record = ''

            services_list = []
            encar_diagnosis = ''
            trust_values = car_info['Trust']
            if len(trust_values) != 0:
                encar_diagnosis = f'encar.com/dc/dc_carsearchpop.do?method=resudtl&carid={car_id_from_photo}'
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

            try:
                sort_type = re.search('(?<=sort%22%3A%22).*?(?=%22)', search_link)[0]
            except TypeError:
                sort_type = "ModifiedDate"

            result_car_info_list.append(
                {
                    'search_id': search_id,
                    'search_link': search_link,
                    'car_id': car_id,
                    'car_id_from_photo': car_id_from_photo,
                    'link': f'encar.com/dc/dc_cardetailview.do?carid={car_id}',
                    'sort_type': sort_type,
                    'brand': car_info.get("Manufacturer", ''),
                    'model': car_info.get("Model", ''),
                    'equipment': car_info.get("Badge", ''),
                    'manufacture_date': car_info.get("Year", ''),
                    'model_year': car_info.get("FormYear", ''),
                    'mileage': car_info.get("Mileage", ''),
                    'transmission': car_info.get("Transmission", ''),
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
                    'search_run': search_run_id,
                    'modified_date': car_info.get("ModifiedDate", ''),
                    'parsing_time': request_timestamp.__str__(),
                }
            )
        return result_car_info_list

    except Exception as e:
        logger.info(f'-> Ошибка во время разбор самих данных, полученных из api - {e} <-')
        raise e


def get_encar_data(search_id, search_link, search_run_id):
    """
           Открываем главную страницу сайта, как она загружается открываем апишку, если она
           отрабатывает забираем ее, далее забираемм все с помощью апи и селениума, при этом если апи не отрабатывает -
           заново открываем главную страницу
       """

    logger.info(f'->Запускаем парсер для id {search_id} <-')

    driver = create_undetected_chrome_driver()
    driver.set_page_load_timeout(65)

    # Так как выдает апишка максимум 300 значений (начиная с 0), то выгялядит конец ссылки именно так
    api_request_count = 300
    end_api_link = f'0%7C{api_request_count - 1}'

    homepage_url = 'http://www.encar.com/'
    api_selector = {'select_type': By.TAG_NAME, 'value': 'pre'}
    homepage_selector = {'select_type': By.ID, 'value': 'indexSch'}
    query = re.search('action%22%3A%22(\(.*\))', search_link)[1]
    api_format_url = f"http://api.encar.com/search/car/list/premium?count=true&q={query}&sr=%7CModifiedDate%7C"

    try:
        hotmarks_info = hotmarks_parser('http://www.encar.com/dc/dc_carsearch_v13_pp0.htm')
    except Exception as e:
        logger.info(f'-> Парсер hotmarks ошибка - {e} <-')
        driver.quit()
        return False

    try:
        logger.info(f'->Запускаем парсер api <-')

        parsing_result_card_list = list()

        api_result = request_api_result(driver, homepage_url, homepage_selector,
                                        f'{api_format_url}{end_api_link}', api_selector)

        api_result = json.loads(api_result)

        count_value = int(api_result['Count'])

        for count in range(0, int(count_value), api_request_count):
            end_api_link = f"{count}%7C{api_request_count - 1}"

            # Если не первый проход, то запрашиваем новые данные
            if count != 0:
                time.sleep(5)
                api_result = request_api_result(driver, homepage_url, homepage_selector,
                                                f'{api_format_url}{end_api_link}', api_selector)
                api_result = json.loads(api_result)

            try:
                parsing_result_card_list += parse_car_info(api_result, search_id, search_link, hotmarks_info, search_run_id)
            except Exception as e:
                logger.info(f'-> Парсинг данных api ошибка при разборе {e} <-')
                driver.quit()
                return False

    except Exception as e:
        logger.info(f'-> Основной парсер api ошибка - {e} <-')
        driver.quit()
        return False

    driver.quit()
    return parsing_result_card_list


# if __name__ == '__main__':
#     url = "http://www.encar.com/dc/dc_carsearchlist.do?carType=kor#!%7B%22action%22%3A%22(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.%ED%98%84%EB%8C%80._.(C.ModelGroup.%ED%8C%B0%EB%A6%AC%EC%84%B8%EC%9D%B4%EB%93%9C._.Model.%ED%8C%B0%EB%A6%AC%EC%84%B8%EC%9D%B4%EB%93%9C.))))%22%7D"
#     print(len(get_encar_data(12, url, 1)))
