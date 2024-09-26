import re
from .db_utils import load_data_from_bd


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
