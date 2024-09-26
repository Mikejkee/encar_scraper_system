import re
import json
from datetime import datetime
import time

import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from airflow.utils.log.logging_mixin import LoggingMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from Common.Utils.simple_utils import cleaned_text, create_undetected_chrome_driver
from Common.Utils.simple_utils import load_data_from_bd, convert_columns_to_json


logger = LoggingMixin().log


def div_tag_on_img_alt(soup, img_alt, table_class):
    img_tag = soup.find('img', alt=img_alt)
    table_tag = img_tag.find_parent("div", class_=table_class)
    return table_tag


def parse_table_data(soup, img_alt, table_class, car_id):
    data = []
    try:
        table_tag = div_tag_on_img_alt(soup, img_alt, table_class)
        for table_string in table_tag.find_all('tr'):
            options_fields = table_string.find_all('th')
            values_field = table_string.find_all('td')

            for key in range(len(options_fields)):
                option = cleaned_text(str(options_fields[key].text))
                value = cleaned_text(str(values_field[key].text))
                data.append({
                    option: value
                })

    except Exception as e:
        logger.info(f'-> Ошибка {e} во время парсинга {img_alt} страховки для id {car_id} <-')
    return data


def extract_damage_tables(soup, tag_alt, tag_class):
    tables = []
    try:
        img_tag = soup.find('img', alt=tag_alt)
        tag_tables = img_tag.find_parent("div", class_=tag_class).find_all('table')
        header_tags = img_tag.find_parent("div", class_=tag_class).find_all('p', class_='his')

        for key in range(len(tag_tables)):
            header_tag_text = cleaned_text(header_tags[key].text)
            header_tag_text_match = re.search('사고일자\s*:(.*?)수리비용\s*:\s*(.*)', header_tag_text, re.DOTALL)
            incident_date = ""
            total_cost = ""
            if header_tag_text_match:
                incident_date = header_tag_text_match.group(1)
                total_cost = header_tag_text_match.group(2)

            info_tags_from_table = tag_tables[key].find_all_next('td')
            parts = cleaned_text(info_tags_from_table[0].text)
            wages = cleaned_text(info_tags_from_table[1].text)
            paints = cleaned_text(info_tags_from_table[2].text)

            tables.append({
                "incident_date": incident_date,
                "total_cost": total_cost,
                "parts": parts,
                "wages": wages,
                "paints": paints,
            })

    except Exception as e:
        logger.info(f'-> Ошибка {e} во время парсинга таблицы страховки <-')
    return tables


def get_insurance_data(car_ids_list, config, base_dir, insurance_data_bd_df: pd.DataFrame = pd.DataFrame):
    driver = create_undetected_chrome_driver()
    driver.set_page_load_timeout(20)

    insurance_info = []
    max_parser_id = len(car_ids_list)
    for parser_id in range(max_parser_id):
        car_id_from_photo = car_ids_list[parser_id][0]
        car_id = car_ids_list[parser_id][1]
        logger.info(f'->Запускаем парсер страховки карточки для id {car_id} {parser_id}/{max_parser_id}<-')

        url = f"http://encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id_from_photo}"

        try:
            # Делаем запрос в бд был ли такой id
            insurance_data = load_data_from_bd(logger, config, 'select_insurance_data_for_id_max_parser_time.sql',
                                               base_dir, 'encar', 'parsing_result_insurance_card',
                                               params_values={'car_id': car_id_from_photo}, expanding=False)
        except Exception as e:
            logger.error(f'->Ошибка {e} при выгрузке данных из таблицы - encar.parsing_result_insurance_card<-')
            continue

        if not insurance_data.empty and insurance_data_bd_df.empty:
            try:
                existed_insurance_data_dict = insurance_data.to_dict(orient='records')[0]
                columns_to_convert = ['car_specification_table', 'usage_history_table', 'owner_changes_table',
                                      'total_loss_table', 'damage_my_car_tables', 'damage_another_car_tables']
                columns_to_drop = ['id', 'create_date', 'create_user', 'change_date', 'search_run', 'parser_run']
                existed_insurance_data = {key: value for key, value in existed_insurance_data_dict.items() if key
                                          not in columns_to_drop}
                existed_insurance_data = convert_columns_to_json(existed_insurance_data, columns_to_convert)
                insurance_info.append(existed_insurance_data)
                continue
            except Exception as e:
                logger.error(f'->Ошибка {e} при вставке уже распаршенных данных из таблицы - encar.parsing_result_insurance_card<-')
                pass

        try:
            driver.get(url)
            time.sleep(2)
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//strong[text()='조회불가차량']")))
                continue
            except TimeoutException:
                pass
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'historydata')))
            html_page = driver.page_source

            soup = BeautifulSoup(html_page, 'html.parser')
            request_timestamp = datetime.now()

            try:
                actual_date = cleaned_text(soup.find('dl', class_="cdate").find_next('dd').text)
                actual_date = datetime.strptime(actual_date, "%Y/%m/%d")

                if not insurance_data_bd_df.empty:
                    try:
                        parsing_date = insurance_data_bd_df.loc[insurance_data_bd_df['car_id'] == car_id, 'parsing_time'].values[0]
                        if parsing_date > datetime.timestamp(actual_date):
                            continue
                    except IndexError:
                        pass
                    except Exception as e:
                        logger.info(f'->Во время поиска страховки карточки для id {car_id} ошибка {e}<-')
                        pass

                car_info_table = soup.find('div', class_="smlist").find_all('tr')
                car_specification = cleaned_text(car_info_table[0].text)
                usage_history = cleaned_text(car_info_table[1].text)
                owner_changes = cleaned_text(car_info_table[2].text)
                total_loss = cleaned_text(car_info_table[3].text)
                damage_my_car = cleaned_text(car_info_table[4].text)
                damage_another_car = cleaned_text(car_info_table[5].text)

                car_specification_table = parse_table_data(soup, '자동차 일반 사양 정보', 'historydata', car_id)
                usage_history_table = parse_table_data(soup, '자동차 용도 이력 정보', 'historydata', car_id)

                owner_changes_table = []
                try:
                    owner_changes_table_tag = div_tag_on_img_alt(soup, '자동차 번호 소유자 변경이력 정보', "historydata")
                    for table_string in owner_changes_table_tag.find_all('tr'):
                        date_fields = cleaned_text(str(table_string.find('th').text))
                        values_field = table_string.find_all('td')

                        owner_changes_table.append({
                            'date': date_fields,
                            'change_type': cleaned_text(str(values_field[0].text)),
                            'license_plate': cleaned_text(str(values_field[1].text)),
                            'purpose': cleaned_text(str(values_field[2].text)),
                        })

                except Exception as e:
                    logger.info(
                        f'-> Ошибка {e} во время парсинга owner_changes_table страховки для id {car_id} <-')
                    pass

                total_loss_table = {}
                try:
                    total_loss_table_tag = div_tag_on_img_alt(soup, '자동차보험 특수 사고이력 정보', "historydata")
                    total_loss_tag_str = total_loss_table_tag.find_all('tr')

                    total_lose = cleaned_text(total_loss_tag_str[0].find_next('td').text)
                    flood = cleaned_text(total_loss_tag_str[1].find_next('td').text)
                    theft = cleaned_text(total_loss_tag_str[2].find_next('td').text)

                    total_loss_table['total_loss'] = total_lose
                    total_loss_table['flood'] = flood
                    total_loss_table['theft'] = theft

                except Exception as e:
                    logger.info(f'-> Ошибка {e} во время парсинга total_loss_table страховки для id {car_id} <-')
                    pass

                damage_my_car_tables = extract_damage_tables(soup, '보험사고이력 정보 : 내차 피해', 'accidentdata')
                damage_another_car_tables = extract_damage_tables(soup, '보험사고이력 정보 : 타차 가해', 'accidentdata')

                insurance_info.append({
                    'car_id': car_id,
                    'actual_date': actual_date.date().__str__(),
                    'car_specification': car_specification,
                    'usage_history': usage_history,
                    'owner_changes': owner_changes,
                    'total_loss': total_loss,
                    'damage_my_car': damage_my_car,
                    'damage_another_car': damage_another_car,
                    'car_specification_table':  json.dumps(car_specification_table, ensure_ascii=False),
                    'usage_history_table':  json.dumps(usage_history_table, ensure_ascii=False),
                    'owner_changes_table': json.dumps(owner_changes_table, ensure_ascii=False),
                    'total_loss_table': json.dumps(total_loss_table, ensure_ascii=False),
                    'damage_my_car_tables':  json.dumps(damage_my_car_tables, ensure_ascii=False),
                    'damage_another_car_tables': json.dumps(damage_another_car_tables, ensure_ascii=False),
                    'parsing_time': request_timestamp.__str__(),
                })

            except Exception as e:
                logger.info(f'-> Ошибка {e} во время парсера страховки для id {car_id} <-')
                continue

        except TimeoutException:
            driver.quit()
            driver = create_undetected_chrome_driver()
            driver.set_page_load_timeout(35)
            parser_id -= 1
            pass

        except Exception as e:
            logger.info(f'-> Ошибка {e} во время захода на страховку для id {car_id} <-')
            continue

    driver.quit()
    logger.info(f'->Парсер страховки машин - успешно отработал <-')

    return insurance_info


# import pandas as pd
# from Common.Utils.sql_processor import SQLProcessor
# from Common.Utils.simple_utils import get_data_of_db_psql_or_mysql, update_data_in_db, load_data_in_db
# from sqlalchemy import Table, MetaData, Column, Integer, String, BigInteger, JSON, TEXT, TIMESTAMP
#
# config = SQLProcessor.config('Common', 'config_airflow_lc.ini')
# result_df = pd.read_excel('./../result_not_exist_2024-01-131.xlsx')
#
# sql_processor = SQLProcessor()
#
# load_data_in_db(result_df, config, 'parsing_result_insurance_card', 'encar')
# from Common.Utils.simple_utils import load_data_from_bd
# from os.path import dirname, abspath
#
# config = SQLProcessor.config('Common', 'config_airflow_lc.ini')
# base_dir = dirname(abspath(__file__))
# insurance_data_bd_df = load_data_from_bd(logger, config, 'select_insurance_data.sql', '../', 'encar',
#                                          'parsing_result_insurance_card')
#
# get_insurance_data([[36986385, 36986385], ], config, '../')
