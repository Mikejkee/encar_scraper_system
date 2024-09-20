from pathlib import Path
import os

import pandas as pd


def normalize_hosts(site):
    result = str(site).strip()
    if str(result).endswith('/'):
        result = result[:-1]
    if str(result).startswith('http://'):
        result = result[7:]

    if str(result).startswith('https://'):
        result = result[8:]

    if str(result).startswith('www.'):
        result = result[4:]
    if '/' in str(result):
        result = str(result).split('/')[0]
    if result == 'нет':
        result = None
    return result


def normalize_phone_number(phone_string):
    phone = ''.join(filter(lambda x: x.isdigit(), str(phone_string)))
    if len(phone) > 11:
        return ''
    elif len(phone) == 11:
        phone = '7' + phone[1:]
        return phone
    elif len(phone) == 10:
        return '7' + phone
    else:
        return ''


def save_html_to_txt_file(name_dir: str, name_file: str, html_text: str):
    from pathlib import Path
    import os
    dir_path = Path.cwd()
    path_to_load = Path(dir_path, name_dir, name_file)

    if not os.path.exists(name_dir):
        os.mkdir(Path(dir_path, name_dir))

    with open(str(path_to_load), 'w') as file:
        file.write(html_text)


def check_full_keys(answer: dict):
    """
    Проверяем все ли ключи в словаре заполнены
    """
    name_keys = list()

    for i in answer.keys():
        if not answer[i]:
            name_keys.append(i)
    if not name_keys:
        return True
    return name_keys


def save_to_excel_df(name_dir: str, name_file: str, df: pd.DataFrame):
    dir_path = Path.cwd()
    path_to_load = Path(dir_path, name_dir, name_file)

    if not os.path.exists(name_dir):
        os.mkdir(Path(dir_path, name_dir))

    df.to_excel(
        str(path_to_load),
        sheet_name='result',
        index=False,
    )

def get_df_of_one_excel(name_dir: str, name_file: str):
    dir_path = Path.cwd()
    path_to_load = Path(dir_path, name_dir, name_file)

    return pd.read_excel(
        str(path_to_load)
    )

