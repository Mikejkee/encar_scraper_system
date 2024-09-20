import re
from .bd_utils import load_data_from_bd


def extract_car_id(url):
    pattern = r'carid=(\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def extract_filename_from_photo_url(url):
    parts = url.split('/')
    return parts[-1]


def extract_car_id_from_photo_url(url):
    pattern = r'/(\d+)_'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None


def cards_data_by_car_id(car_id, config, base_dir):
    card_info = load_data_from_bd(config, 'select_cards_by_car_id.sql', base_dir, 'encar', 'cards',
                                  params_values={'car_id': car_id}, expanding=False)
    columns_to_drop = ['id', 'create_date', 'create_user', 'change_date', 'search_run', 'parser_run']
    card_info = card_info.drop(columns_to_drop, axis=1)

    return card_info


def insurance_data_by_car_id(car_id, config, base_dir):
    insurance_info = load_data_from_bd(config, 'select_insurance_by_car_id.sql', base_dir, 'encar', 'insurance_list',
                                       params_values={'car_id': car_id}, expanding=False)
    columns_to_drop = ['id', 'create_date', 'create_user', 'change_date', 'search_run', 'parser_run']
    insurance_info = insurance_info.drop(columns_to_drop, axis=1)

    return insurance_info


def inspection_data_by_car_id(car_id, config, base_dir):
    inspection_info = load_data_from_bd(config, 'select_inspection_by_car_id.sql', base_dir, 'encar', 'inspection_list',
                                        params_values={'car_id': car_id}, expanding=False)
    columns_to_drop = ['id', 'create_date', 'create_user', 'change_date', 'search_run', 'parser_run']
    inspection_info = inspection_info.drop(columns_to_drop, axis=1)

    return inspection_info


def inspection_data_by_car_vin(car_vin, config, base_dir):
    inspection_info = load_data_from_bd(config, 'select_inspection_by_car_vin.sql', base_dir, 'encar', 'inspection_list',
                                        params_values={'vin': car_vin}, expanding=False)
    columns_to_drop = ['id', 'create_date', 'create_user', 'change_date', 'search_run', 'parser_run']
    inspection_info = inspection_info.drop(columns_to_drop, axis=1)

    return inspection_info
