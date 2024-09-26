import sys
import re
import json
import datetime
import time
from os.path import dirname, realpath


from bs4 import BeautifulSoup
from airflow.utils.log.logging_mixin import LoggingMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

begin_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.append(begin_path)

from Common.Utils.simple_utils import cleaned_text, create_undetected_chrome_driver, get_car_id_from_photo


logger = LoggingMixin().log


def get_car_data(car_id_list):
    driver = create_undetected_chrome_driver()
    driver.set_page_load_timeout(35)

    card_info = []
    max_parser_id = len(car_id_list)
    for parser_id in range(max_parser_id):
        car_id = car_id_list[parser_id]
        url = f"http://www.encar.com/dc/dc_cardetailview.do?type=detailPrint&carid={car_id}"
        logger.info(f'->Запускаем парсер карточки для id {car_id} {parser_id}/{max_parser_id}<-')

        try:
            driver.get(url)
            time.sleep(2)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'section_detail')))
            html_page = driver.page_source

            soup = BeautifulSoup(html_page, 'html.parser')
            request_timestamp = datetime.datetime.now()

            try:
                price = cleaned_text(soup.find('em', class_='emph_price').text)
                mileage = cleaned_text(soup.find('th', string="주행거리").find_next('td').text)
                manufacture_date = cleaned_text(soup.find('th', string="연식").find_next('td').text)

                mode_year_match = re.search(r'\((.*?)\)', manufacture_date)
                model_year = mode_year_match.group(1) if mode_year_match else ""

                fuel = cleaned_text(soup.find('th', string="연료").find_next('td').text)
                body_type = cleaned_text(soup.find('th', string="차종").find_next('td').text)
                engine_capacity = cleaned_text(soup.find('th', string="배기량").find_next('td').text)
                transmission = cleaned_text(soup.find('th', string="변속기").find_next('td').text)
                color = cleaned_text(soup.find('th', string="색상").find_next('td').text)
                registration_number = cleaned_text(soup.find('th', string="차량번호").find_next('td').text)

                view_count_text = cleaned_text(soup.find('span', class_="hit").text)
                view_count = re.sub(r'\D', '', view_count_text)

                bookmarks_text = cleaned_text(soup.find('span', class_="hot").text)
                bookmarks = re.sub(r'\D', '', bookmarks_text)

                card_create_date_text = cleaned_text(soup.find('span', class_="date").text)
                card_create_date_match = re.search(r'최초등록(.+)', card_create_date_text)
                card_create_date = card_create_date_match.group(1) if card_create_date_match else ""

                photo_list = []
                photo_index = 1
                for img in soup.find('div', class_='section_image').findAll('img'):
                    photo_src = str(img['src'])
                    if photo_src != '/images/cardetail/no_photo.png':
                        photo_src = str(img['src'])
                        photo_list.append({
                            'position': photo_index,
                            'url': photo_src.split('?')[0]
                        })
                        photo_index += 1

                car_id_from_photo = get_car_id_from_photo(car_id, photo_list)
                perfomance_check = ""
                if soup.find('h3', string="성능점검기록부"):
                    perfomance_check = f'encar.com/md/sl/mdsl_regcar.do?method=inspectionViewNew&carid={car_id_from_photo}'

                insurance_report = ""
                if not soup.find('p', string="보험처리 이력이 등록되지 않았습니다."):
                    insurance_report = f'encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id_from_photo}'

                option_list = []
                options_cluster_tags = soup.findAll('dl', class_='list_options fst')
                for option_cluster in options_cluster_tags:
                    for option in option_cluster.findAllNext('dd'):
                        option_description_match = re.search(r'(\(X\)|\(0\))(.*)', option.text)
                        option_description = option_description_match.group(2)
                        option_mode = option_description_match.group(1).replace('(', "").replace(')', "") == '0'
                        option_list.append({
                            'option': option_description,
                            'enabled': option_mode,
                        })

                packet_list = []
                packet_cluster_tags = soup.findAll('dl', class_='list_options add_option')
                for packet_cluster in packet_cluster_tags:
                    for packet in packet_cluster.findAllNext('dd'):
                        packet_description_cleaned = re.sub(r"\(X\)|\(0\)", "", packet.text)
                        packet_description_match = re.search(r'(.*) (\S+원)$', packet_description_cleaned)
                        if packet_description_match:
                            packet_description = packet_description_match.group(1)
                            packet_price = packet_description_match.group(2)
                        else:
                            packet_description = packet_description_cleaned
                            packet_price = " "

                        packet_list.append({
                            'option': re.sub(r'\s+', ' ', packet_description).strip(),
                            'price': re.sub(r'\s+', ' ', packet_price).strip(),
                        })

                seller_name = cleaned_text(soup.find('th', string="이름").find_next('td').text)
                seller_region = cleaned_text(soup.find('th', string="주소").find_next('td').text)

                try:
                    seller_comment = soup.find('pre', class_="inner_desc").text
                except AttributeError:
                    seller_comment = ""

                card_info.append({
                    'car_id': car_id,
                    'car_id_from_photo': car_id_from_photo,
                    'price': price,
                    'mileage': mileage,
                    'manufacture_date': manufacture_date,
                    'model_year': model_year,
                    'fuel': fuel,
                    'body_type': body_type,
                    'engine_capacity': engine_capacity,
                    'transmission': transmission,
                    'color': color,
                    'registration_number': registration_number,
                    'view_count': view_count,
                    'bookmarks': bookmarks,
                    'card_create_date': card_create_date,
                    'photo_list': json.dumps(photo_list, ensure_ascii=False),
                    'perfomance_check': perfomance_check,
                    'insurance_report': insurance_report,
                    'option_list': json.dumps(option_list, ensure_ascii=False),
                    'packet_list': json.dumps(packet_list, ensure_ascii=False),
                    'seller_name': seller_name,
                    'seller_region': seller_region,
                    'seller_comment': seller_comment,
                    'parsing_time': request_timestamp.__str__(),
                })

            except Exception as e:
                logger.info(f'-> Ошибка {e} во время парсера карточки для id {car_id} <-')
                continue

        except TimeoutException:
            driver.quit()
            driver = create_undetected_chrome_driver()
            driver.set_page_load_timeout(35)
            parser_id -= 1
            pass

        except Exception as e:
            logger.info(f'-> Ошибка {e} во время захода на карточку для id {car_id} <-')
            continue

    driver.quit()
    logger.info(f'->Парсер карточек машин - успешно отработал <-')

    return card_info

# import pandas as pd, os
# from Common.Utils.sql_processor import SQLProcessor
# from Common.Utils.simple_utils import get_data_of_db_psql_or_mysql, update_data_in_db, load_data_in_db
# from sqlalchemy import Table, MetaData, Column, Integer, String, BigInteger, JSON, TEXT, TIMESTAMP
#
# config = SQLProcessor.config('Common', 'config_airflow_lc.ini')
# result_df = pd.read_excel('./../result.xlsx')
#
# sql_processor = SQLProcessor()


# get_car_data([36947833, ])