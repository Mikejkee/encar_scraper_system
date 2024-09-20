import sys
from datetime import datetime, timedelta
from os.path import dirname, realpath, abspath
import asyncio
import pytz
import re

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from sqlalchemy import INTEGER, String, JSON, TEXT, TIMESTAMP, BIGINT, DATE
import pandas as pd
from googletrans import Translator

begin_path = dirname(dirname(dirname(dirname(realpath(__file__)))))
sys.path.append(begin_path)

from Common.Utils.sql_processor import SQLProcessor
from Common.Utils.simple_utils import load_data_from_bd, load_data_in_db, update_data_in_db, convert_columns_to_json, \
    get_df_with_last_existing_data_each_cell
from dags.repo.ENCAR.utils.telegram_bot import send_data_to_group, send_file_to_group
from dags.repo.ENCAR.utils.encar_search_parser import get_encar_data
from dags.repo.ENCAR.utils.encar_card_parser import get_car_data
from dags.repo.ENCAR.utils.encar_insurance_parser import get_insurance_data
from dags.repo.ENCAR.utils.encar_inspection_card_parser import get_inspection_card_data

# TODO: 1. Перписать формирование уникальных таблиц, выделить повторяющиеся блоки в отдельные функции
#  2. Сделать парсинг независимый.
sql_processor = SQLProcessor()
CONNECTION_NAME = 'encar_data_connection'


def get_connections():
    return {
        CONNECTION_NAME: BaseHook.get_connection(CONNECTION_NAME),
    }


connections = get_connections()

config = {
    'psql_conn_type': connections[CONNECTION_NAME].conn_type,
    'psql_hostname': connections[CONNECTION_NAME].host,
    'psql_port': connections[CONNECTION_NAME].port,
    'psql_login': connections[CONNECTION_NAME].login,
    'psql_password': connections[CONNECTION_NAME].password,
    'psql_name_bd': 'cars',
}
monitoring_chat_id = Variable.get('MONITORING_CHAT_ID')
results_chat_id = Variable.get('RESULTS_CHAT_ID')

# config = SQLProcessor.config('Common', 'config_airflow_lc.ini')

logger = LoggingMixin().log
base_dir = dirname(abspath(__file__))

temp_cards_table_columns = {'car_id': BIGINT, 'car_id_from_photo': BIGINT, 'last_id': BIGINT,
                            'last_parsing_ts': TIMESTAMP, 'brand_id': INTEGER, 'model_id': INTEGER, 'fuel_id': INTEGER,
                            'transmission_id': INTEGER, 'brand': String(length=128), 'model': String(length=128),
                            'price': BIGINT, 'mileage': String(length=32), 'manufacture_date': DATE,
                            'model_year': String(length=32), 'fuel': String(length=64), 'body_type': String(length=32),
                            'engine_capacity': String(length=32), 'transmission': String(length=128),
                            'color': String(length=64), 'registration_number': String(length=64),
                            'view_count': String(length=64), 'bookmarks': INTEGER,
                            'card_create_date': String(length=64), 'photo_list': JSON,
                            'perfomance_check': String(length=2048), 'insurance_report': String(length=2048),
                            'option_list': JSON, 'packet_list': JSON, 'seller_name': String(length=64),
                            'seller_region': String(length=64), 'seller_comment': TEXT,
                            'change_date': TIMESTAMP, 'search_run': INTEGER, 'parser_run': INTEGER,
                            'mileage_km': INTEGER, 'engine_capacity_cc': INTEGER}

temp_insurance_table_columns = {'car_id': BIGINT, 'last_id': BIGINT, 'last_parsing_ts': TIMESTAMP,
                                'actual_date': DATE, 'car_specification': String(length=256),
                                'usage_history': String(length=256), 'owner_changes': String(length=256),
                                'total_loss': String(length=256), 'damage_my_car': String(length=256),
                                'damage_another_car': String(length=256), 'car_specification_table': JSON,
                                'usage_history_table': JSON, 'owner_changes_table': JSON, 'total_loss_table': JSON,
                                'damage_my_car_tables': JSON, 'damage_another_car_tables': JSON,
                                'damage_my_car_cnt': INTEGER, 'damage_my_car_cost': INTEGER,
                                'damage_another_car_cost': INTEGER, 'damage_another_car_cnt': INTEGER,
                                'total_loss_common': INTEGER, 'total_loss_threft': INTEGER,
                                'total_loss_flood': INTEGER, 'owner_changes_lp': INTEGER, 'owner_changes_o': INTEGER,
                                'change_date': TIMESTAMP, 'search_run': INTEGER, 'parser_run': INTEGER}

temp_inspection_table_columns = {'car_id': BIGINT, 'last_id': BIGINT, 'last_parsing_ts': TIMESTAMP,
                                 'car_specification': String(length=256), 'licence_plate': String(length=256),
                                 'registration_date': DATE, 'fuel_id': BIGINT, 'fuel': String(length=64),
                                 'warranty_type': String(length=64), 'model_year': INTEGER,
                                 'warranty_period': String(length=128), 'transmission_id': BIGINT,
                                 'transmission_type': String(length=64), 'vin': String(length=32),
                                 'engine_type': String(length=32), 'mileage_gauge_status': JSON,
                                 'mileage': JSON, 'vin_condition': JSON, 'exhaust_gas': JSON, 'tuning': JSON,
                                 'special_history': JSON, 'change_of_use': JSON, 'color': JSON, 'main_options': JSON,
                                 'recall_target': JSON, 'accident_history': String(length=256),
                                 'simple_repair': String(length=256), 'special_notes': String(length=256),
                                 'damages_table': JSON, 'details_table': JSON, 'photos': JSON,
                                 'inspector': String(length=256), 'informant': String(length=256), 'inspect_date': DATE,
                                 'special_notes_inspector': String(length=256), 'inspection_photo_list': JSON,
                                 'change_date': TIMESTAMP, 'search_run': INTEGER, 'parser_run': INTEGER,
                                 'warranty_period_to': DATE, 'warranty_period_from': DATE}


def replace_and_convert_price(match):
    number = match.group(1) + '.' + match.group(2)
    return str(float(number) * 1000000)


def extract_count_damage(value):
    if value == "없음" or not value:
        return 0, 0
    else:
        # Получаем цифры перед "회"
        num1 = int(value.split('회')[0])

        # Получаем только цифры после запятой и вопросительного знака
        match = re.search(r',([0-9\?\,]+)', value)
        num2 = int()
        if match:
            num2 = re.sub(r'\D', '', match.group(1))
    return num1, num2


def parse_date(date_str):
    if date_str is not None:
        try:
            return datetime.strptime(date_str, '%Y년%m월%d일').date()
        except ValueError:
            try:
                # Попробуйте преобразовать дату без дня
                date_str = date_str.split("월")[0]
                return datetime.strptime(date_str, '%Y년%m').date().replace(day=1)
            except ValueError:
                # Если не получилось, вставьте первый месяц и первый день
                date_str = date_str.split("년")[0]
                return datetime.strptime(date_str, '%Y').date().replace(month=1, day=1)
    else:
        return None


def take_searches_function():
    logger.info(f'->Выполняем подключение к бд и выгрузку из таблицы - encar.searches c условием start, finish<-')
    search_list = load_data_from_bd(logger, config, 'select_searches_checked_start_finish.sql', base_dir, 'encar',
                                    'searches')
    return search_list


def period_check_searches_function(search_list_df):
    current_time = datetime.now()

    search_runs_df = load_data_from_bd(logger, config, 'select_search_runs_max_finish_time.sql', base_dir, 'encar',
                                       'search_runs', params_values={'search_id_list': search_list_df['id'].to_list()})

    # Преобразование значений столбца period из строк в timedelta, чтоб потом складывать
    period_map = {'m': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks'}
    for index, row in search_list_df.iterrows():
        period_value = int(row['period'][:-1])
        period_unit = period_map[row['period'][-1]]
        search_list_df.at[index, 'period'] = timedelta(**{period_unit: period_value})

    # Объединение search_runs и searches по столбцу search_id и id
    merged_df = pd.merge(search_runs_df[['search_id', 'start_time', 'status']], search_list_df,
                         left_on='search_id', right_on='id', how='right')

    # Если парсинг еще идет - удяляем из повторного запуска если выполняются меньше часа,
    # если больше часа - пишем в тг о таких поисках
    proces_search = merged_df[merged_df['status'] == 1]
    proces_search_needed = proces_search[merged_df['start_time'] > current_time - timedelta(hours=24)]
    merged_df = merged_df.drop(proces_search_needed.index)
    try:
        search_tg_remind_id = proces_search[merged_df['start_time'] < current_time - timedelta(hours=1)].id.to_list()
        if search_tg_remind_id:
            logger.info(f'->Сообщение в телеграм о поисках, работающих больше часа <-')
            loop = asyncio.get_event_loop()
            loop.run_until_complete(send_data_to_group(search_tg_remind_id, 'ID, которые работают больше часа'))
            logger.info(f'->Сообщение отправлено <-')
    except Exception as e:
        logger.error(f'->Ошибка {e} при отправке информации в тг <-')

    # Фильтрация записей, где start_time + period больше текущего времени => его надо запустить.
    filtered_df = merged_df[(merged_df['start_time'] + merged_df['period']) < current_time]
    filtered_df = filtered_df[search_list_df.columns]

    # Добавляем сюда те поиски, которые ни разу еще не проводились (информации о них нет в таблице search_runs)
    new_searches_df = merged_df[merged_df['start_time'].isnull()][search_list_df.columns]
    filtered_df = pd.concat([filtered_df, new_searches_df]).drop_duplicates().reset_index(drop=True)

    # Добавляем сюда те поиски, которые завершились ошибкой
    filtered_status = merged_df.loc[merged_df['status'] == -1][search_list_df.columns]
    filtered_df = pd.concat([filtered_df, filtered_status]).drop_duplicates().reset_index(drop=True)

    logger.info(f'-> Поиски отфильтрованы, список необходимых к запуску сформирован <-')
    return filtered_df


def encar_parser_function(search_list_df, full_parser_flag):
    # Проходим по каждому поиску и запускаем парсер
    for index, search in search_list_df.iterrows():
        search_id = search["id"]
        current_time = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Создаем search_run и берем его id
        search_runs_df_to_load = pd.DataFrame({'start_time': f'{current_time}',
                                               'status': '1',
                                               'finish_time': None,
                                               'search_id': f'{search_id}',
                                               'create_time': f'{current_time}',
                                               'create_user': 'postgres',
                                               'cars_cnt': None,
                                               }, index=[0])
        load_data_in_db(search_runs_df_to_load, logger, config, 'encar', 'search_runs')
        search_run_id = load_data_from_bd(logger, config, 'select_search_run_id.sql', base_dir, 'encar',
                                          'search_runs')['id'].values[0]

        # Далее парсим апи, карточки, страховку, диагностику и вставляем
        try:
            parse_result_df = get_encar_data(search_id, search['link'], search_run_id)
        except Exception as e:
            logger.info(f'-> Парсер для id {search_id} выполнен с ошибкой {e} <-')
            parse_result_df = None

        # Если была ошибка - то статус -1
        if not parse_result_df:
            logger.info(f'-> Парсер для id {search_id} выполнен с ошибкой <-')
            parse_status = '-1'
            cars_count = None

            # Пишем в телегу
            loop = asyncio.get_event_loop()
            loop.run_until_complete(send_data_to_group(monitoring_chat_id, [search_id, ],
                                                       'ID, для которого парсинг выполнен с ошибкой'))
        else:
            logger.info(f'-> Парсер для id {search_id} выполнен успешно <-')
            parse_status = '2'
            cars_count = len(parse_result_df)
            parse_result_df = pd.DataFrame(parse_result_df)

            # Проверяем полностью ли мы парсим, если нет - скидываем ссылки на новые машины в тг
            if not full_parser_flag:
                card_data_bd_df = load_data_from_bd(logger, config,
                                                    'select_parsing_result_card_list_id_link.sql', base_dir,
                                                    'encar', 'parsing_result_card_list',
                                                    params_values={'search_id': search_id}, expanding=False)
                not_existed_card_df = parse_result_df[~parse_result_df.car_id.isin(card_data_bd_df.car_id)]
                new_cars_urls = not_existed_card_df['link'].to_list()
                if new_cars_urls:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(send_file_to_group(results_chat_id, new_cars_urls,
                                                               f'Новые машины типа {search["title"]}'))
                finish_time = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                load_data_from_bd(logger, config, 'update_search_runs_status_end_time.sql', base_dir, 'encar',
                                  'search_runs',
                                  params_values={
                                      'status': parse_status,
                                      'finish_time': finish_time,
                                      'cars_cnt': cars_count,
                                      'start_time': f'{current_time}',
                                      'search_id': f'{search_id}',
                                  }, expanding=False)
                load_data_in_db(parse_result_df, logger, config, 'encar', 'parsing_result_card_list')
                continue

            load_data_in_db(parse_result_df, logger, config, 'encar', 'parsing_result_card_list')
            # Парсим карточки машин которых до этого не парсили
            card_data_not_existed_df = pd.DataFrame()
            card_data_to_update_df = pd.DataFrame()
            card_data_bd_df = load_data_from_bd(logger, config, 'select_parsing_result_card_id.sql', base_dir,
                                                'encar', 'parsing_result_card')
            try:
                not_existed_card_df = parse_result_df[~parse_result_df.car_id.isin(card_data_bd_df.car_id)]

                not_existed_card_car_id = not_existed_card_df['car_id'].to_list()
                card_data_not_existed_df = get_car_data(not_existed_card_car_id)
                card_data_not_existed_df = pd.DataFrame(card_data_not_existed_df)

                load_data_in_db(card_data_not_existed_df, logger, config, 'encar', 'parsing_result_card')

                # Приводим типы и парсим карточки, у которых поле ModifiedDate больше давности парсинга
                parse_result_df['modified_date'] = pd.to_datetime(parse_result_df['modified_date'])
                card_data_bd_df['parsing_time'] = pd.to_datetime(card_data_bd_df['parsing_time'])
                parse_result_df['modified_date'] = parse_result_df['modified_date'].dt.tz_convert(pytz.UTC)
                card_data_bd_df['parsing_time'] = card_data_bd_df['parsing_time'].dt.tz_localize(pytz.UTC)

                to_update_df = pd.merge(parse_result_df[['car_id', 'modified_date']],
                                        card_data_bd_df[['car_id', 'parsing_time']], on='car_id', how='inner')

                to_update_df = to_update_df[to_update_df['modified_date'] > to_update_df['parsing_time']]
                to_update_df_car_id = to_update_df['car_id'].to_list()
                card_data_to_update = get_car_data(to_update_df_car_id)
                card_data_to_update_df = pd.DataFrame(card_data_to_update)

                load_data_in_db(card_data_to_update_df, logger, config, 'encar', 'parsing_result_card')

            except Exception as e:
                logger.error(f'->Ошибка {e} при парсинге карточек в основной функции')

            try:
                # Парсим страховку машин которых до этого не парсил
                insurance_data_not_existed_car_id = card_data_not_existed_df[
                    card_data_not_existed_df['insurance_report'] != ""][['car_id_from_photo', 'car_id']].values.tolist()
                insurance_data_not_existed = get_insurance_data(insurance_data_not_existed_car_id, config, base_dir)
                insurance_data_not_existed_df = pd.DataFrame(insurance_data_not_existed)
                load_data_in_db(insurance_data_not_existed_df, logger, config, 'encar', 'parsing_result_insurance_card')
            except KeyError:
                pass
            except Exception as e:
                logger.error(f'->Ошибка {e} при парсинге страховки в основной функции <-')

            # Парсим страховку машин, у которых поле ModifiedDate больше давности парсинга
            # (при этом смотрим на поле актуальности страховки), если она актуальна - пропускаем
            insurance_data_bd_df = load_data_from_bd(logger, config, 'select_insurance_data.sql', base_dir, 'encar',
                                                     'parsing_result_insurance_card')
            try:
                insurance_data_updated_car_id = card_data_to_update_df[
                    card_data_to_update_df['insurance_report'] != ""][['car_id_from_photo', 'car_id']].values.tolist()
                insurance_data_updated = get_insurance_data(insurance_data_updated_car_id, config, base_dir,
                                                            insurance_data_bd_df)
                insurance_data_updated_df = pd.DataFrame(insurance_data_updated)
                load_data_in_db(insurance_data_updated_df, logger, config, 'encar', 'parsing_result_insurance_card')
            except KeyError:
                pass
            except Exception as e:
                logger.error(f'->Ошибка {e} при парсинге страховки в основной функции <-')

            # Парсим диагностику машин, которых до этого не парсили
            inspection_data_bd_df = load_data_from_bd(logger, config, 'select_inspection_data.sql', base_dir, 'encar',
                                                      'parsing_result_inspection_card')
            try:
                inspection_data_not_existed_car_id = card_data_not_existed_df[
                    card_data_not_existed_df['perfomance_check'] != ""][['car_id_from_photo', 'car_id']].values.tolist()
                inspection_data_not_existed = get_inspection_card_data(inspection_data_not_existed_car_id,
                                                                       inspection_data_bd_df)
                inspection_data_not_existed_df = pd.DataFrame(inspection_data_not_existed)
                load_data_in_db(inspection_data_not_existed_df, logger, config, 'encar',
                                'parsing_result_inspection_card')
            except KeyError:
                pass
            except Exception as e:
                logger.error(f'->Ошибка {e} при парсинге диагностики в основной функции <-')

        finish_time = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        load_data_from_bd(logger, config, 'update_search_runs_status_end_time.sql', base_dir, 'encar', 'search_runs',
                          params_values={
                              'status': parse_status,
                              'finish_time': finish_time,
                              'cars_cnt': cars_count,
                              'start_time': f'{current_time}',
                              'search_id': f'{search_id}',
                          }, expanding=False)
    return True


def create_unique_card_list():
    full_cards_data_df = load_data_from_bd(logger, config, 'select_parsing_result_card.sql', base_dir, 'encar',
                                           'parsing_result_card').replace("", None)

    full_cards_data_df['parsing_time'] = pd.to_datetime(full_cards_data_df['parsing_time'])
    dirty_unique_cards_data_df = full_cards_data_df.loc[
        full_cards_data_df.groupby('car_id')['parsing_time'].idxmax()].replace("", None)

    # dirty_unique_cards_data_df = load_data_from_bd(logger, config, 'select_parsing_result_card_max_parsing_time.sql',
    #                                                base_dir, 'encar', 'parsing_result_card').replace("", None)

    brands_data_df = load_data_from_bd(logger, config, 'select_brands.sql', base_dir, 'encar', 'brands')
    model_data_df = load_data_from_bd(logger, config, 'select_models.sql', base_dir, 'encar', 'models')
    fuel_data_df = load_data_from_bd(logger, config, 'select_fuels.sql', base_dir, 'encar', 'fuels')
    transmission_data_df = load_data_from_bd(logger, config, 'select_transmissions.sql', base_dir, 'encar',
                                             'transmissions')
    cards_data_list_df = load_data_from_bd(logger, config, 'select_parsing_result_card_list.sql',
                                           base_dir, 'encar', 'parsing_result_card_list')

    # Формируем последние известные данные
    cleaned_unique_cards_data_df = get_df_with_last_existing_data_each_cell(dirty_unique_cards_data_df,
                                                                            full_cards_data_df, 'car_id')

    # Мерджим с parsing_result_card_list оставляем brand и model (потому что их нет в таблице parsing_result_card)
    # и берем уникальные
    cleaned_unique_cards_data_df = pd.merge(cleaned_unique_cards_data_df, cards_data_list_df, on='car_id', how='left')
    cleaned_unique_cards_data_df = cleaned_unique_cards_data_df.sort_values('parsing_time').drop_duplicates('car_id',
                                                                                                            keep='last')
    # Чистим и добавляем нужные данные`
    cleaned_unique_cards_data_df['price'] = cleaned_unique_cards_data_df['price'].apply(
        lambda x: float(re.sub(r'(\d*?)[\?,]*(\d*?)만원.*', replace_and_convert_price, x)) if pd.notnull(x) else 0)
    cleaned_unique_cards_data_df['price'] = cleaned_unique_cards_data_df['price'].astype(int)
    cleaned_unique_cards_data_df['manufacture_date'] = cleaned_unique_cards_data_df['manufacture_date'].apply(
        lambda x: datetime.strptime(re.sub(r'\(.*?\)', '', x), '%Y년%m월') if pd.notnull(x) else x)
    cleaned_unique_cards_data_df['mileage_km'] = cleaned_unique_cards_data_df['mileage'].apply(
        lambda x: float(re.sub(r'\D', '', x)) if pd.notnull(x) else 0).astype(int)
    cleaned_unique_cards_data_df['model_year'] = cleaned_unique_cards_data_df['model_year'].apply(
        lambda x: float(re.sub(r'\D', '', x)) if pd.notnull(x) else 0).astype(int)
    cleaned_unique_cards_data_df['engine_capacity_cc'] = cleaned_unique_cards_data_df['engine_capacity'].apply(
        lambda x: float(re.sub(r'\D', '', x)) if pd.notnull(x) else 0).astype(int)

    # Добавляем brand_id, model_id, fuel_id, transmission_id
    cleaned_unique_cards_data_df = pd.merge(cleaned_unique_cards_data_df, brands_data_df, left_on='brand',
                                            right_on='title_korean', how='left', suffixes=('', '_brand'))
    cleaned_unique_cards_data_df = pd.merge(cleaned_unique_cards_data_df, model_data_df, left_on='model',
                                            right_on='title_korean', how='left', suffixes=('', '_model'))
    cleaned_unique_cards_data_df = pd.merge(cleaned_unique_cards_data_df, fuel_data_df, left_on='fuel',
                                            right_on='title_korean', how='left', suffixes=('', '_fuel'))
    cleaned_unique_cards_data_df = pd.merge(cleaned_unique_cards_data_df, transmission_data_df, left_on='transmission',
                                            right_on='title_korean', how='left', suffixes=('', '_transmission'))
    cleaned_unique_cards_data_df['change_date'] = pd.Timestamp(datetime.now())
    # Подготавливаем к загрузке
    cleaned_unique_cards_data_df = cleaned_unique_cards_data_df.rename(columns={'id': 'last_id',
                                                                                'parsing_time': 'last_parsing_ts',
                                                                                'id_brand': 'brand_id',
                                                                                'id_model': 'model_id',
                                                                                'id_fuel': 'fuel_id',
                                                                                'id_transmission': 'transmission_id'
                                                                                })
    columns_to_drop = ['title_korean', 'title_korean_model', 'title_korean_fuel', 'title_korean_transmission',
                       'create_time', 'create_user']
    cleaned_unique_cards_data_df = cleaned_unique_cards_data_df.drop(columns_to_drop, axis=1)
    # Преобразуем столбцы в JSON
    columns_to_convert = ['photo_list', 'option_list', 'packet_list']
    cleaned_unique_cards_data_df = convert_columns_to_json(cleaned_unique_cards_data_df, columns_to_convert)

    update_data_in_db(logger, cleaned_unique_cards_data_df, config, 'update_card_list.sql', 'drop_temp_table.sql',
                      temp_cards_table_columns, base_dir, 'encar', 'cards')


def create_unique_insurance_list():
    full_insurance_data_df = load_data_from_bd(logger, config, 'select_insurance_data.sql', base_dir, 'encar',
                                               'parsing_result_insurance_card').replace("", None)

    # dirty_unique_insurance_data_df = load_data_from_bd(logger, config, 'select_insurance_data_max_parsing_time.sql',
    #                                                    base_dir, 'encar',
    #                                                    'parsing_result_insurance_card').replace("", None)
    full_insurance_data_df['parsing_time'] = pd.to_datetime(full_insurance_data_df['parsing_time'])
    dirty_unique_insurance_data_df = full_insurance_data_df.loc[
        full_insurance_data_df.groupby('car_id')['parsing_time'].idxmax()].replace("", None)

    # Формируем последние известные данные
    cleaned_insurance_data_df = get_df_with_last_existing_data_each_cell(dirty_unique_insurance_data_df,
                                                                         full_insurance_data_df, 'car_id')

    # Добавляем damage_my_car_cnt, damage_my_car_cost, damage_another_car_cnt, damage_another_car_cost,
    # total_loss_common, total_loss_threft, total_loss_flood, owner_changes_lp, owner_changes
    cleaned_insurance_data_df['damage_my_car_cnt'], cleaned_insurance_data_df['damage_my_car_cost'] = \
        zip(*cleaned_insurance_data_df['damage_my_car'].apply(lambda x: extract_count_damage(x)))

    cleaned_insurance_data_df['damage_another_car_cnt'], cleaned_insurance_data_df['damage_another_car_cost'] = \
        zip(*cleaned_insurance_data_df['damage_another_car'].apply(lambda x: extract_count_damage(x)))

    cleaned_insurance_data_df['total_loss_common'] = cleaned_insurance_data_df['total_loss'].str.extract(r'전손:(\d+)')
    cleaned_insurance_data_df['total_loss_threft'] = cleaned_insurance_data_df['total_loss'].str.extract(r'도난:(\d+)')
    cleaned_insurance_data_df['total_loss_flood'] = cleaned_insurance_data_df['total_loss'].str.extract(r'침수\(전손/분손'
                                                                                                        r'\):(\d+)')

    cleaned_insurance_data_df['owner_changes_lp'] = cleaned_insurance_data_df['owner_changes'].str.extract(r'(\d+)회/\d+'
                                                                                                           r'회')
    cleaned_insurance_data_df['owner_changes_o'] = cleaned_insurance_data_df['owner_changes'].str.extract(
        r'\d+회/(\d+)회')
    cleaned_insurance_data_df['change_date'] = pd.Timestamp(datetime.now())

    # Подготавливаем к загрузке
    cleaned_insurance_data_df = cleaned_insurance_data_df.rename(columns={'id': 'last_id',
                                                                          'parsing_time': 'last_parsing_ts'
                                                                          })
    columns_to_drop = ['create_date', 'create_user']
    cleaned_insurance_data_df = cleaned_insurance_data_df.drop(columns_to_drop, axis=1)
    # Преобразуем столбцы в JSON
    columns_to_convert = ['car_specification_table', 'usage_history_table', 'owner_changes_table', 'total_loss_table',
                          'damage_my_car_tables', 'damage_another_car_tables']
    cleaned_insurance_data_df = convert_columns_to_json(cleaned_insurance_data_df, columns_to_convert)

    update_data_in_db(logger, cleaned_insurance_data_df, config, 'update_insurance_list.sql', 'drop_temp_table.sql',
                      temp_insurance_table_columns, base_dir, 'encar', 'insurance_list')


def create_unique_inspection_list():
    full_inspection_data_df = load_data_from_bd(logger, config, 'select_inspection_data.sql', base_dir, 'encar',
                                                'parsing_result_inspection_card').replace("", None)

    cleaned_inspection_data_df = full_inspection_data_df.drop_duplicates(subset='car_id')

    fuel_data_df = load_data_from_bd(logger, config, 'select_fuels.sql', base_dir, 'encar', 'fuels')
    transmission_data_df = load_data_from_bd(logger, config, 'select_transmissions.sql', base_dir, 'encar',
                                             'transmissions')

    # Добавляем fuel_id, transmission_id
    cleaned_inspection_data_df = pd.merge(cleaned_inspection_data_df, fuel_data_df, left_on='fuel',
                                          right_on='title_korean', how='left', suffixes=('', '_fuel'))
    cleaned_inspection_data_df = pd.merge(cleaned_inspection_data_df, transmission_data_df, left_on='transmission_type',
                                          right_on='title_korean', how='left', suffixes=('', '_transmission'))
    cleaned_inspection_data_df['warranty_period_from'] = cleaned_inspection_data_df['warranty_period'].apply(
        lambda x: x.split('~')[0] if x and '~' in x else None)
    cleaned_inspection_data_df['warranty_period_to'] = cleaned_inspection_data_df['warranty_period'].apply(
        lambda x: x.split('~')[1] if x and '~' in x else None)
    cleaned_inspection_data_df['warranty_period_from'] = cleaned_inspection_data_df['warranty_period_from'] \
        .apply(parse_date)
    cleaned_inspection_data_df['warranty_period_to'] = cleaned_inspection_data_df['warranty_period_to'] \
        .apply(parse_date)

    cleaned_inspection_data_df['change_date'] = pd.Timestamp(datetime.now())

    # Подготавливаем к загрузке
    cleaned_inspection_data_df = cleaned_inspection_data_df.rename(columns={'id': 'last_id',
                                                                            'parsing_time': 'last_parsing_ts',
                                                                            'id_fuel': 'fuel_id',
                                                                            'id_transmission': 'transmission_id'
                                                                            })
    columns_to_drop = ['title_korean', 'title_korean_transmission', 'create_date', 'create_user']
    cleaned_inspection_data_df = cleaned_inspection_data_df.drop(columns_to_drop, axis=1)
    # Преобразуем столбцы в JSON
    columns_to_convert = ['mileage_gauge_status', 'mileage', 'vin_condition', 'exhaust_gas', 'tuning',
                          'special_history', 'change_of_use', 'color', 'main_options', 'recall_target', 'damages_table',
                          'details_table', 'photos', 'inspection_photo_list']
    cleaned_inspection_data_df = convert_columns_to_json(cleaned_inspection_data_df, columns_to_convert)

    update_data_in_db(logger, cleaned_inspection_data_df, config, 'update_inspection_list.sql', 'drop_temp_table.sql',
                      temp_inspection_table_columns, base_dir, 'encar', 'inspection_list')


def translate_text(text):
    translator = Translator()
    try:
        russian_translation = translator.translate(text, dest='ru').text
    except Exception as e:
        logger.info(f'->Ошибка {e} при переводе значения на русский {text} <-')
        russian_translation = None
    try:
        english_translation = translator.translate(text, dest='en').text
    except Exception as e:
        logger.info(f'->Ошибка {e} при переводе значения на английский {text} <-')
        english_translation = None
    return text, russian_translation, english_translation


def translate_df(value_list, existed_translate):
    # Проверяем есть ли уже их перевод, если нет - переводим
    unique_value = [value for value in value_list if value not in existed_translate]
    translations = [translate_text(value) for value in unique_value]

    # Создаем датафрейм с тремя столбцами
    translated_df = pd.DataFrame(translations, columns=['korean', 'russian', 'english'])
    translated_df.dropna().apply(lambda col: col[col != ""])

    return translated_df


def create_list_values_to_translate(to_translate_column_values):
    cleaned_value = to_translate_column_values.dropna()
    cleaned_value = cleaned_value[cleaned_value != ""]
    if not cleaned_value.empty:
        unique_values = set()
        for item in cleaned_value:
            if isinstance(item, dict):
                for value_list in item.values():
                    for value in value_list:
                        unique_values.add(value)
            else:
                return cleaned_value.unique().tolist()
        return list(unique_values)
    else:
        return list()


def create_not_translated_value(to_translate_df, column_to_translate, existed_translate):
    # Перевод строчных данных с корейского на русский
    try:
        korean_value_list = []
        for column in column_to_translate:
            korean_value_list += create_list_values_to_translate(to_translate_df[column])

        # Создаем датафрейм с тремя столбцами
        translated_value_df = translate_df(korean_value_list, existed_translate)

        return translated_value_df

    except Exception as e:
        logger.info(f'->Ошибка {e} при создании переводов обычных столбцов <-')
        raise e


def create_not_translated_json_value(to_translate_df, column_dict_to_translate, existed_translate):
    # Перевод данных с корейского на русский из стобцов json
    try:
        korean_json_value_list = []
        for json_column_name in column_dict_to_translate:
            json_to_translate = to_translate_df[json_column_name]
            json_to_translate_list = []
            for sublist in json_to_translate:
                if not isinstance(sublist, list):
                    sublist = [sublist, ]
                for item in sublist:
                    if item:
                        json_to_translate_list.append(item)
            json_to_translate_df = pd.DataFrame(json_to_translate_list)

            table_columns_in_json = column_dict_to_translate[json_column_name]
            if isinstance(table_columns_in_json, tuple):
                for column_to_translate in json_to_translate_df.columns:
                    if column_to_translate not in korean_json_value_list:
                        korean_json_value_list.append(column_to_translate)
                    if column_to_translate not in table_columns_in_json:
                        korean_json_value_list += create_list_values_to_translate(json_to_translate_df[
                                                                                      column_to_translate])
            else:
                for column_to_translate in table_columns_in_json:
                    korean_json_value_list += create_list_values_to_translate(json_to_translate_df[column_to_translate])

        translated_json_value_df = translate_df(korean_json_value_list, existed_translate)

        return translated_json_value_df
    except Exception as e:
        logger.info(f'->Ошибка {e} при создании переводов json столбцов <-')
        raise e


def merge_and_load_translate(main_data_df, column_to_translate, column_json_to_translate):
    # Вставляем новые встречающиеся слова в korean_dictionary
    korean_dictionary_data_df = load_data_from_bd(logger, config, 'select_korean_dictionary.sql', base_dir,
                                                  'encar', 'korean_dictionary')
    existed_translate = korean_dictionary_data_df['korean'].tolist()

    not_translated_value_df = create_not_translated_value(main_data_df, column_to_translate, existed_translate)
    not_translated_json_value_df = create_not_translated_json_value(main_data_df, column_json_to_translate,
                                                                    existed_translate)

    new_korean_dictionary_df = pd.concat([not_translated_value_df, not_translated_json_value_df])

    load_data_in_db(new_korean_dictionary_df, logger, config, 'encar', 'korean_dictionary')


def translate_json_column(json_value, column_json_to_translate, korean_dictionary_data_df):
    russian_translated_json_values = []
    english_translated_json_values = []

    if not isinstance(json_value, list):
        json_value = [json_value]

    for value_dict in json_value:
        russian_translated_dict = {}
        english_translated_dict = {}
        for key, value in value_dict.items():
            if not column_json_to_translate or (
                    isinstance(column_json_to_translate, tuple) and key not in column_json_to_translate):
                translated_key = korean_dictionary_data_df.loc[korean_dictionary_data_df['korean'] == key]
                russian_translated_key = translated_key['russian'].values[0]
                english_translated_key = translated_key['english'].values[0]
                translated_value = korean_dictionary_data_df.loc[korean_dictionary_data_df['korean'] == value]
                russian_translated_value = translated_value['russian'].values[0] if value else None
                english_translated_value = translated_value['english'].values[0] if value else None

                russian_translated_dict[russian_translated_key] = russian_translated_value
                english_translated_dict[english_translated_key] = english_translated_value
            elif isinstance(column_json_to_translate, list) and key in column_json_to_translate:
                if value and isinstance(value, dict):
                    russian_translated_subdict = {}
                    english_translated_subdict = {}
                    for subkey, subvalue_list in value.items():
                        russian_translated_sublist = [
                            korean_dictionary_data_df.loc[korean_dictionary_data_df['korean'] == subvalue]['russian']
                            .values[0] for subvalue in subvalue_list
                        ]
                        english_translated_sublist = [
                            korean_dictionary_data_df.loc[korean_dictionary_data_df['korean'] == subvalue]['english']
                            .values[0] for subvalue in subvalue_list
                        ]
                        russian_translated_subdict[subkey] = russian_translated_sublist
                        english_translated_subdict[subkey] = english_translated_sublist
                    russian_translated_dict[key] = russian_translated_subdict
                    english_translated_dict[key] = english_translated_subdict
                elif value:
                    russian_translated_dict[key] = korean_dictionary_data_df.loc[korean_dictionary_data_df['korean']
                                                                                 == value]['russian'].values[0]
                    english_translated_dict[key] = korean_dictionary_data_df.loc[korean_dictionary_data_df['korean']
                                                                                 == value]['english'].values[0]
                else:
                    russian_translated_dict[key] = None
                    english_translated_dict[key] = None
            else:
                translated_key = korean_dictionary_data_df.loc[korean_dictionary_data_df['korean'] == key]
                if not translated_key.empty:
                    russian_translated_key = translated_key['russian'].values[0]
                    english_translated_key = translated_key['english'].values[0]

                    russian_translated_dict[russian_translated_key] = value
                    english_translated_dict[english_translated_key] = value
                else:
                    russian_translated_dict[key] = value
                    english_translated_dict[key] = value
        russian_translated_json_values.append(russian_translated_dict)
        english_translated_json_values.append(english_translated_dict)

    return [russian_translated_json_values, english_translated_json_values]


def translate_table(df_to_translate, column_to_translate, column_json_to_translate, temp_table_columns, update_sql,
                    schema, table_name, df_json_columns):
    try:
        merge_and_load_translate(df_to_translate, column_to_translate, column_json_to_translate)
        korean_dictionary_data_df = load_data_from_bd(logger, config, 'select_korean_dictionary.sql', base_dir,
                                                      'encar', 'korean_dictionary')
        for column in column_to_translate:
            try:
                df_to_translate = df_to_translate.merge(korean_dictionary_data_df, left_on=column, right_on='korean',
                                                        how='left')
                df_to_translate[f'{column}_russian'] = df_to_translate['russian']
                df_to_translate[f'{column}_english'] = df_to_translate['english']
                df_to_translate = df_to_translate.drop(['korean', 'russian', 'english'], axis=1)

            except Exception as e:
                logger.info(f'->Ошибка {e} при объединении переводов для стобца {column} <-')
                continue

        for json_column_name in column_json_to_translate:
            try:
                translated_values = df_to_translate[json_column_name].apply(
                    lambda value: translate_json_column(value, column_json_to_translate[json_column_name],
                                                        korean_dictionary_data_df) if value else [None, None])

                df_to_translate[f'{json_column_name}_russian'] = translated_values.apply(lambda x: x[0])
                df_to_translate[f'{json_column_name}_english'] = translated_values.apply(lambda x: x[1])

            except Exception as e:
                logger.info(f'->Ошибка {e} при объединении переводов для стобца {json_column_name} <-')
                continue

        translated_columns = [f'{column}_english' for column in column_to_translate] + \
                             [f'{column}_russian' for column in column_to_translate]
        temp_table_columns.update({column: String(length=256) for column in translated_columns})

        translated_json_columns = [f'{column}_english' for column in column_json_to_translate] + \
                                  [f'{column}_russian' for column in column_json_to_translate]
        temp_table_columns.update({column: JSON for column in translated_json_columns})

        columns_to_drop = ['id', 'create_date', 'create_user']
        df_to_translate = df_to_translate.drop(columns_to_drop, axis=1)

        # Делаем типы json у значений
        columns_to_convert = translated_json_columns + list(column_json_to_translate.keys()) + df_json_columns
        existed_data_df = convert_columns_to_json(df_to_translate, columns_to_convert)

        update_data_in_db(logger, existed_data_df, config, update_sql, 'drop_temp_table.sql',
                          temp_table_columns, base_dir, schema, table_name)
    except Exception as e:
        logger.info(f'->Ошибка {e} при создании переводов новых слов в таблице {schema}.{table_name} <-')
        pass


def translate_tables():
    """Столбцы переводятся по принципу, в столбце строчное значение - то просто их загоняем в *_column_to_translate,
        json значение (таблица): { имя столбца: () - переводим все столбцы таблицы + перевод названия столбца
                                   имя столбца: (..., ...,) - данные столбцы не переводим, остальные переводим
                                                              + перевод названия столбца
                                   имя столбца: [..., ...,] - данные столбцы переводим, название не переводим

    """
    # Перевод cards
    card_list_data_df = load_data_from_bd(logger, config, 'select_card_list.sql', base_dir, 'encar', 'cards')
    cards_column_to_translate = ['fuel', 'brand', 'model', 'body_type', 'transmission', 'color', 'seller_region']
    cards_column_json_to_translate = {'option_list': ['option'], 'packet_list': ['option']}
    cards_json_columns = ['photo_list']

    translate_table(card_list_data_df, cards_column_to_translate, cards_column_json_to_translate,
                    temp_cards_table_columns, 'update_cards_translated.sql', 'encar', 'cards_translated',
                    cards_json_columns)

    # Перевод insurance
    insurance_list_data_df = load_data_from_bd(logger, config, 'select_insurance_list.sql', base_dir, 'encar',
                                               'insurance_list')
    insurance_column_to_translate = ['car_specification', 'usage_history']
    insurance_column_json_to_translate = {'car_specification_table': ('연식', '배기량', '최초보험가입일자'),
                                          'usage_history_table': (),
                                          'owner_changes_table': ['purpose', 'change_type'],
                                          'total_loss_table': ['flood', 'theft', 'total_loss']}
    insurance_json_columns = ['damage_my_car_tables', 'damage_another_car_tables']

    translate_table(insurance_list_data_df, insurance_column_to_translate, insurance_column_json_to_translate,
                    temp_insurance_table_columns, 'update_insurance_list_translated.sql', 'encar',
                    'insurance_translated', insurance_json_columns)

    # Перевод inspection
    inspection_list_data_df = load_data_from_bd(logger, config, 'select_inspection_list.sql', base_dir, 'encar',
                                                'inspection_list')
    inspection_column_to_translate = ['car_specification', 'warranty_type', 'accident_history', 'simple_repair']
    inspection_column_json_to_translate = {'mileage_gauge_status': ['remarks', 'situation', 'applicable'],
                                           'mileage': ['remarks', 'situation', 'applicable'],
                                           'vin_condition': ['remarks', 'situation', 'applicable'],
                                           'exhaust_gas': ['remarks', 'situation', 'applicable'],
                                           'tuning': ['remarks', 'situation', 'applicable'],
                                           'special_history': ['remarks', 'situation', 'applicable'],
                                           'change_of_use': ['remarks', 'situation', 'applicable'],
                                           'color': ['remarks', 'situation', 'applicable'],
                                           'main_options': ['remarks', 'situation', 'applicable'],
                                           'recall_target': ['remarks', 'situation', 'applicable'],
                                           'damages_table': ['a_rank', 'b_rank', 'c_rank', '1st_rank', '2nd_rank'],
                                           'details_table': ['item', 'device', 'remarks', 'situation']}
    inspection_json_columns = ['tuning', 'photos', 'inspection_photo_list']

    translate_table(inspection_list_data_df, inspection_column_to_translate, inspection_column_json_to_translate,
                    temp_inspection_table_columns, 'update_inspection_list_translated.sql', 'encar',
                    'inspection_translated', inspection_json_columns)


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    # logger = Logger.get_logger(__name__)
    load_dotenv('airflow.env')
    monitoring_chat_id = os.environ.get('MONITORING_CHAT_ID')
    results_chat_id = os.environ.get('RESULTS_CHAT_ID')

    config = SQLProcessor.config('Common', 'config.ini')

    a = take_searches_function()
    b = period_check_searches_function(a)
    encar_parser_function(b, False)
    # create_unique_card_list()
    # create_unique_insurance_list()
    # create_unique_inspection_list()
    # translate_tables()
