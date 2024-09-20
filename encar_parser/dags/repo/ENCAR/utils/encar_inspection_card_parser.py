import time
import json
from datetime import datetime
from itertools import product

from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from airflow.utils.log.logging_mixin import LoggingMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from Common.Utils.simple_utils import cleaned_text, create_undetected_chrome_driver

logger = LoggingMixin().log


def parse_value_on_active(column_tag):
    value_on = column_tag.find('span', class_='on')
    value_active = column_tag.find('span', class_='active')
    value = cleaned_text(value_on.text) if value_on else (cleaned_text(value_active.text) if value_active else None)
    return value


def parse_overall_condition_parameters(row_tag):
    value_tags = row_tag.find_all_next('td')

    situation = parse_value_on_active(value_tags[0])
    applicable = cleaned_text(value_tags[1].text) if len(value_tags[1].text) != 0 else None
    price = cleaned_text(value_tags[2].text) if len(value_tags[2].text) != 0 else None
    remarks = cleaned_text(value_tags[3].text) if len(value_tags[3].text) != 0 else None

    parameter_value_dict = {
        'situation': situation,
        'applicable': applicable,
        'price': price,
        'remarks': remarks,
    }

    return parameter_value_dict


def parse_damage_rank(tag_rank):
    damage_class_list = {
        'i1': 'X',
        'i2': 'W',
        'i3': 'C',
        'i4': 'A',
        'i5': 'U',
        'i6': 'T',
    }

    damage_rank_value = {}

    for damage_tag in tag_rank.find_all('li'):
        if 'class' not in damage_tag.attrs.keys():
            damage_value = cleaned_text(damage_tag.find_next('strong').text)

            damage_class = damage_tag.find_next('span').attrs['class'][0]
            damage_class_value = damage_class_list[damage_class]
            if damage_class_value not in damage_rank_value.keys():
                damage_rank_value[damage_class_value] = []

            damage_rank_value[damage_class_value].append(damage_value)
        else:
            damage_rank_value = None

    return damage_rank_value


def parse_rowspan_colspan_table(table_tag):
    rowspans = []
    rows = table_tag.find_all('tr')

    colcount = 0
    for r, row in enumerate(rows):
        cells = row.find_all(['td', 'th'], recursive=False)
        colcount = max(
            colcount,
            sum(int(c.get('colspan', 1)) or 1 for c in cells[:-1]) + len(cells[-1:]) + len(rowspans))

        rowspans += [int(c.get('rowspan', 1)) or len(rows) - r for c in cells]
        rowspans = [s - 1 for s in rowspans if s > 1]

    table = [[None] * colcount for row in rows]

    rowspans = {}
    for row, row_elem in enumerate(rows):
        span_offset = 0
        for col, cell in enumerate(row_elem.find_all(['td', 'th'], recursive=False)):
            col += span_offset
            while rowspans.get(col, 0):
                span_offset += 1
                col += 1

            rowspan = rowspans[col] = int(cell.get('rowspan', 1)) or len(rows) - row
            colspan = int(cell.get('colspan', 1)) or colcount - col

            span_offset += colspan - 1
            value = cell.get_text()
            if col == 3:
                value = parse_value_on_active(cell)
            for drow, dcol in product(range(rowspan), range(colspan)):
                try:
                    table[row + drow][col + dcol] = cleaned_text(value)
                    rowspans[col + dcol] = rowspan
                except IndexError:
                    pass

        rowspans = {c: s - 1 for c, s in rowspans.items() if s > 1}

    return table


def parse_details_table(table_tag):
    parsed_table = parse_rowspan_colspan_table(table_tag)

    details_table = []
    for row in parsed_table:
        item = row[1] if row[1] == row[2] else f'{row[1]}: {row[2]}'
        device = row[0] if row[0] else None
        situation = row[3] if row[3] else None
        price = row[4] if row[4] else None
        remarks = row[5] if row[5] else None

        details_table.append(
            {
                'device': device,
                'item': item,
                'situation': situation,
                'price': price,
                'remarks': remarks,
            }
        )

    return details_table


def get_inspection_card_data(car_ids_list, inspection_data_bd_df):
    driver = create_undetected_chrome_driver()
    driver.set_page_load_timeout(20)

    inspection_info = []
    max_parser_id = len(car_ids_list)
    for parser_id in range(max_parser_id):
        car_id_from_photo = car_ids_list[parser_id][0]
        car_id = car_ids_list[parser_id][1]

        logger.info(f'->Запускаем парсер диагностики для id {car_id} {parser_id}/{max_parser_id}<-')
        url = f"http://encar.com/md/sl/mdsl_regcar.do?method=inspectionViewNew&carid={car_id_from_photo}"

        inspection_data = inspection_data_bd_df[inspection_data_bd_df['car_id'] == car_id_from_photo]
        if not inspection_data.empty:
            inspection_info.append(inspection_data.to_dict(orient='records')[0])
            continue

        try:
            driver.get(url)
            time.sleep(2)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'inspec_carinfo')))
            html_page = driver.page_source
            soup = BeautifulSoup(html_page, 'html.parser')
            request_timestamp = datetime.now()

            try:
                car_info_table = soup.find('table', class_="ckst")

                if car_info_table:
                    car_specification = cleaned_text(car_info_table.find('th', string="차명").find_next('td').text)
                    licence_plate = cleaned_text(car_info_table.find('th', string="차량번호").find_next('td').text)
                    registration_date = cleaned_text(car_info_table.find('th', string="최초등록일").find_next('td').text)
                    registration_date = datetime.strptime(registration_date, '%Y년%m월%d일')
                    fuel = cleaned_text(car_info_table.find('th', string="사용연료").find_next('td').text)
                    warranty_type = cleaned_text(car_info_table.find('th', string="보증유형").find_next('td').text)
                    model_year = cleaned_text(car_info_table.find('th', string="연식").find_next('td').text)
                    model_year = datetime.strptime(model_year, '%Y년').year
                    warranty_period = cleaned_text(car_info_table.find('th', string="검사유효기간").find_next('td').text)
                    transmission_type = cleaned_text(car_info_table.find('th', string="변속기종류").find_next('td').text)
                    vin = cleaned_text(car_info_table.find('th', string="차대번호").find_next('td').text)
                    engine_type = cleaned_text(car_info_table.find('th', string="원동기형식").find_next('td').text)

                    # Overall condition
                    overall_condition_table = soup.find('table', class_="tbl_total").find('tbody').find_all('tr')
                    mileage_gauge_status = parse_overall_condition_parameters(overall_condition_table[0])
                    mileage = parse_overall_condition_parameters(overall_condition_table[1])
                    vin_condition = parse_overall_condition_parameters(overall_condition_table[2])
                    exhaust_gas = parse_overall_condition_parameters(overall_condition_table[3])
                    tuning = parse_overall_condition_parameters(overall_condition_table[4])
                    special_history = parse_overall_condition_parameters(overall_condition_table[5])
                    change_of_use = parse_overall_condition_parameters(overall_condition_table[6])
                    color = parse_overall_condition_parameters(overall_condition_table[7])
                    main_options = parse_overall_condition_parameters(overall_condition_table[8])
                    recall_target = parse_overall_condition_parameters(overall_condition_table[9])

                    repair_table = soup.find('table', class_="tbl_repair").find('tbody').find_all('tr')
                    accident_history = parse_value_on_active(repair_table[0].find_next('td'))
                    simple_repair = parse_value_on_active(repair_table[1].find_next('td'))
                    special_notes = cleaned_text(repair_table[2].find_next('td').text)

                    damages_table = {'1st_rank': parse_damage_rank(soup.find('ul', class_='uiListLank1')),
                                     '2nd_rank': parse_damage_rank(soup.find('ul', class_='uiListLank2')),
                                     'a_rank': parse_damage_rank(soup.find('ul', class_='uiListLankA')),
                                     'b_rank': parse_damage_rank(soup.find('ul', class_='uiListLankB')),
                                     'c_rank': parse_damage_rank(soup.find('ul', class_='uiListLankC'))}

                    details_table_tag = soup.find('table', class_="tbl_detail").find('tbody')
                    details_table = parse_details_table(details_table_tag)

                    special_notes_inspector = cleaned_text(soup.find('table', class_="tbl_opinion").find('td').text)

                    photos = []
                    try:
                        photos_tags = soup.find('div', class_="section_img").find_all('img')
                        for img_tag in photos_tags:
                            photos.append(
                                {
                                    'url': img_tag.attrs['src'],
                                    'description': cleaned_text(img_tag.attrs['alt']),
                                }
                            )
                    except Exception as e:
                        pass

                    inspection_tag = soup.find('div', class_="inspc_sign")
                    inspector = cleaned_text(inspection_tag.find_all('p', class_="sign")[0].find_next('span').text)
                    informant = cleaned_text(inspection_tag.find_all('p', class_="sign")[1].find_next('span').text)
                    inspect_date = cleaned_text(inspection_tag.find('p', class_="date").text)
                    inspect_date = datetime.strptime(inspect_date, '%Y년%m월%d일')
                    inspection_photo_list = []

                    inspection_info.append({
                        'car_id': car_id,
                        'car_specification': car_specification,
                        'licence_plate': licence_plate,
                        'registration_date': registration_date.date().__str__(),
                        'fuel': fuel,
                        'warranty_type': warranty_type,
                        'model_year': model_year,
                        'warranty_period': warranty_period,
                        'transmission_type': transmission_type,
                        'vin': vin,
                        'engine_type': engine_type,
                        'mileage_gauge_status': json.dumps(mileage_gauge_status, ensure_ascii=False),
                        'mileage': json.dumps(mileage, ensure_ascii=False),
                        'vin_condition': json.dumps(vin_condition, ensure_ascii=False),
                        'exhaust_gas': json.dumps(exhaust_gas, ensure_ascii=False),
                        'tuning': json.dumps(tuning, ensure_ascii=False),
                        'special_history': json.dumps(special_history, ensure_ascii=False),
                        'change_of_use': json.dumps(change_of_use, ensure_ascii=False),
                        'color': json.dumps(color, ensure_ascii=False),
                        'main_options': json.dumps(main_options, ensure_ascii=False),
                        'recall_target': json.dumps(recall_target, ensure_ascii=False),
                        'accident_history': accident_history,
                        'simple_repair': simple_repair,
                        'special_notes': special_notes,
                        'damages_table': json.dumps(damages_table, ensure_ascii=False),
                        'details_table': json.dumps(details_table, ensure_ascii=False),
                        'photos': json.dumps(photos, ensure_ascii=False),
                        'inspector': inspector,
                        'informant': informant,
                        'special_notes_inspector': special_notes_inspector,
                        'inspect_date':  inspect_date.date().__str__(),
                        'parsing_time': request_timestamp.__str__(),
                        'inspection_photo_list': inspection_photo_list,
                    })

                else:
                    inspection_photo_list = []

                    try:
                        photos_tags = soup.find('div', class_="box_photo_view").find_all('img')
                        for img_tag in photos_tags:
                            inspection_photo_list.append(
                                {
                                    'url': img_tag.attrs['src'],
                                    'description': cleaned_text(img_tag.attrs['alt']),
                                }
                            )
                    except Exception as e:
                        logger.error(f'->Ошибка {e} при парсинге фото диагностики<-')
                        pass

                    inspection_info.append({
                        'car_id': car_id,
                        'car_specification': None,
                        'licence_plate': None,
                        'registration_date': None,
                        'fuel': None,
                        'warranty_type': None,
                        'model_year': None,
                        'warranty_period': None,
                        'transmission_type': None,
                        'vin': None,
                        'engine_type': None,
                        'mileage_gauge_status': None,
                        'mileage': None,
                        'vin_condition': None,
                        'exhaust_gas': None,
                        'tuning': None,
                        'special_history': None,
                        'change_of_use': None,
                        'color': None,
                        'main_options': None,
                        'recall_target': None,
                        'accident_history': None,
                        'simple_repair': None,
                        'special_notes': None,
                        'damages_table': None,
                        'details_table': None,
                        'photos': None,
                        'inspector': None,
                        'informant': None,
                        'special_notes_inspector': None,
                        'inspect_date': None,
                        'parsing_time': None,
                        'inspection_photo_list': json.dumps(inspection_photo_list, ensure_ascii=False),
                    })

            except Exception as e:
                logger.info(f'-> Ошибка {e} во время парсера диагностики для id {car_id} <-')
                continue

        except TimeoutException:
            driver.quit()
            driver = create_undetected_chrome_driver()
            driver.set_page_load_timeout(35)
            parser_id -= 1
            pass

        except Exception as e:
            logger.info(f'-> Ошибка {e} во время захода на диагностику для id {car_id} <-')
            continue

    driver.quit()
    logger.info(f'->Парсер диагностики машин - успешно отработал <-')

    return inspection_info

# from pprint import pprint
# from Common.Utils.sql_processor import SQLProcessor
# from Common.Utils.simple_utils import get_data_of_db_psql_or_mysql, update_data_in_db, load_data_in_db
# config = SQLProcessor.config('Common', 'config_airflow_lc.ini')
# logger.info(f'->Выполняем подключение к бд и выгрузку из таблицы - encar.parsing_result_inspection_card <-')
# inspection_data_bd_df = get_data_of_db_psql_or_mysql(config, 'select_inspection_data.sql', '../')
# logger.info(f'->Выгрузка из таблицы - encar.parsing_result_inspection_card - успешна <-')
#
# pprint(get_inspection_card_data([[36828211, 36434357], ], inspection_data_bd_df))