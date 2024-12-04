import requests
import time
import datetime as dt
from affise import api
from database import db
import math

from logs import logger as log
import crm
import traceback

AFFISE_API_KEY = '1472b075254d6df44e295b3912665295'
HEADERS = {'API-Key': AFFISE_API_KEY}


def get_new_partners():
    today = str(dt.date.today())
    yesterday = str(dt.date.today() - dt.timedelta(days=1))
    two_days = str(dt.date.today() - dt.timedelta(days=2))
    three_days = str(dt.date.today() - dt.timedelta(days=3))
    four_days = str(dt.date.today() - dt.timedelta(days=4))
    five_days = str(dt.date.today() - dt.timedelta(days=5))

    partners = api.get_partners()
    partners_list = []
    partners_info_list = []
    for partner in partners['partners']:
        if today in partner['created_at'] or yesterday in partner['created_at'] or two_days in partner['created_at']:
            partners_list.append(partner)
    for partner in partners_list:
        create_date, create_time = str(partner['created_at']).split(" ")
        partner_info = {'created_at': create_date, 'email': partner['email'], 'partner_id': partner['id'],
                        'status': partner['status'], 'balance': partner['balance']['RUB']['balance'],
                        'ref_partner': partner['ref']}
        form_fields_list = []
        partner_info['phone'] = 'None'
        partner_info['exp_years'] = 'None'
        partner_info['solo_or_team'] = 'None'
        partner_info['verticals'] = "None"
        partner_info['sources_lm'] = "None"
        partner_info['thematics'] = "None"
        partner_info['about_us'] = 'None'
        for fields in partner['customFields']:
            if type(fields['label']) is dict:
                form_fields_list.append({'field_id': fields['id'], 'label': ", ".join(list(fields['label'].values()))})
            else:
                form_fields_list.append({'field_id': fields['id'], 'label': fields['label']})
        for field in form_fields_list:
            if field['field_id'] == 5:
                partner_info['phone'] = field['label']
            if field['field_id'] == 1:
                if "https://t.me/" in field['label']:
                    partner_info['telegram'] = field['label']
                elif "https://t.me/" not in field['label']:
                    try:
                        partner_info['telegram'] = int(field['label'])
                    except ValueError:
                        tg_value = "https://t.me/" + str(field['label']).strip('@')
                        partner_info['telegram'] = tg_value
            elif field['field_id'] == 16:
                partner_info['exp_years'] = field['label']
            elif field['field_id'] == 18:
                partner_info['solo_or_team'] = field['label']
            elif field['field_id'] == 20:  # multiple types
                partner_info['verticals'] = field['label']
            elif field['field_id'] == 22:  # multiple types
                partner_info['sources_lm'] = field['label']
            elif field['field_id'] == 23:  # multiple types
                partner_info['thematics'] = field['label']
            elif field['field_id'] == 25:
                partner_info['about_us'] = field['label']

        partners_info_list.append(partner_info)
    # for i in partners_info_list:
    #     print(i)
    # return partners_info_list
    db_partners = db.get_partners_id()

    for partner in partners_info_list:
        if partner['partner_id'] not in db_partners:
            db.add_new_partner(partner)
            log.msg.info(f"Успешно добавили партнера {partner['partner_id']} в базу")
    return partners_info_list




def get_common_charge(attempt, date_from, partner_id):
    TODAY = dt.date.today()
    log.msg.info(f"Попытка {attempt}.  Пробуем получить ОРБ для веба {partner_id} за все время")
    common_charge_url = f"https://api-lead-magnet.affise.com/3.0/stats/getbypartner?filter[date_from]={date_from}&filter[date_to]={TODAY}&filter[partner]={partner_id}&limit=500"
    common_charge_r = requests.get(common_charge_url, headers=HEADERS)
    log.msg.info(f"Попытка {attempt}.  Успешно получили ОРБ для веба {partner_id} за все время")
    common_charge_url_res = common_charge_r.json()
    common_charge = common_charge_url_res['stats'][0]['actions']['confirmed']['charge']
    return common_charge

def get_common_roi(attempt, date_from, partner_id):
    TODAY = dt.date.today()
    log.msg.info(f"Попытка {attempt}. Пробуем получить продажи для веба {partner_id} за все время")
    common_sales_url = f"https://api-lead-magnet.affise.com/3.0/stats/conversions?date_from={date_from}&date_to={TODAY}&partner[]={partner_id}&goal=5&limit=500"

    common_sales_r = requests.get(common_sales_url, headers=HEADERS)
    common_sales_url_res = common_sales_r.json()
    log.msg.info(f"Попытка {attempt}. Успешно получили продажи для веба {partner_id} за все время на странице {common_sales_url_res['pagination']['page']}")
    if len(common_sales_url_res['conversions']) > 0: # если есть продажи за все время
        common_sales_list = []
        common_sales_affprices_list = []
        if "next_page" in common_sales_url_res['pagination']:
            total_count_pages = math.ceil(common_sales_url_res['pagination']['total_count'] / 500)
            log.msg.info(f"Попытка {attempt}. Получили несколько страниц ({total_count_pages}) с продажами для веба {partner_id} за все время")
            for page in range(1, total_count_pages + 1):
                log.msg.info(f"Попытка {attempt}. Пробуем получить продажи для веба {partner_id} за все время на странице {page}")
                common_sales_url = f"https://api-lead-magnet.affise.com/3.0/stats/conversions?date_from={date_from}&date_to={TODAY}&partner[]={partner_id}&goal=5&limit=500&page={page}"
                common_sales_r = requests.get(common_sales_url, headers=HEADERS)
                common_sales_url_res = common_sales_r.json()
                log.msg.info(f"Попытка {attempt}. Успешно получили продажи для веба {partner_id} за все время на странице {common_sales_url_res['pagination']['page']}")

                for goal in common_sales_url_res['conversions']:
                    sale = {'offer_id': goal['offer_id'],
                            'affprice': goal['sum']}
                    common_sales_affprices_list.append(int(goal['sum']))
                    common_sales_list.append(sale)
        else:
            for goal in common_sales_url_res['conversions']:
                sale = {'offer_id': goal['offer_id'],
                        'affprice': goal['sum']}
                common_sales_affprices_list.append(int(goal['sum']))
                common_sales_list.append(sale)

        common_sales_sum = sum(common_sales_affprices_list)

        common_charge = get_common_charge(attempt, date_from, partner_id)
        common_roi = int(round(common_sales_sum / common_charge * 100))
    else:
        common_roi = 0

    return common_roi
