import requests
import traceback
import time

AFFISE_API_KEY = '1472b075254d6df44e295b3912665295'

def get_partners():
    for attempt in range(10):
        try:
            log.msg.info(f"Попытка {attempt}. Запросили новорегов в аффайз")
            url = f'https://api-lead-magnet.affise.com/3.0/admin/partners?limit=500&page=65&status=active'
            headers = {'API-Key': AFFISE_API_KEY}
            r = requests.get(url, headers=headers)
            res = r.json()
            if res['status'] == 1:
                log.msg.info(f"Попытка {attempt}. Успешно получили новорегов в аффайз")
                return res
            else:
                return None
        except Exception as err:
            log.msg.error(f'Попытка {attempt}. Поймали исключение', err, 'Спим 30 секунд и повторяем попытку')
            time.sleep(30)
            continue

