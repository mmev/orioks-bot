import logging
import os

import re
import aiohttp
from bs4 import BeautifulSoup

import config
from utils import exceptions
from utils.delete_file import safe_delete
from utils.json_files import JsonFile
from utils.make_request import get_request
from utils.notify_to_user import SendToTelegram
import aiogram.utils.markdown as md


def _orioks_parse_homeworks(raw_html: str) -> dict:
    bs_content = BeautifulSoup(raw_html, "html.parser")
    if bs_content.select_one('.table.table-condensed.table-thread') is None:
        raise exceptions.OrioksCantParseData
    table_raw = bs_content.select('.table.table-condensed.table-thread tr:not(:first-child)')
    homeworks = dict()
    for tr in table_raw:
        _thread_id = int(re.findall(r'\d+$', tr.find_all('td')[2].select_one('a')['href'])[0])
        homeworks[_thread_id] = {
            'status': tr.find_all('td')[1].text,
            'new_messages': int(tr.find_all('td')[8].select_one('b').text),
            'about': {
                'discipline': tr.find_all('td')[3].text,
                'task': tr.find_all('td')[4].text,
                'url': config.ORIOKS_PAGE_URLS['masks']['homeworks'].format(id=_thread_id),
            },
        }
    return homeworks


async def get_orioks_homeworks(session: aiohttp.ClientSession) -> dict:
    raw_html = await get_request(url=config.ORIOKS_PAGE_URLS['notify']['homeworks'], session=session)
    return _orioks_parse_homeworks(raw_html)


async def get_homeworks_to_msg(diffs: list) -> str:
    message = ''
    for diff in diffs:
        if diff['type'] == 'new_status':
            message += md.text(
                md.text(
                    md.text('📝'),
                    md.hbold(diff['about']['task']),
                    md.text('по'),
                    md.text(f"«{diff['about']['discipline']}»"),
                    sep=' '
                ),
                md.text(
                    md.text('Cтатус домашнего задания изменён на:'),
                    md.hcode(diff['current_status']),
                    sep=' ',
                ),
                md.text(),
                md.text(
                    md.text('Подробности по ссылке:'),
                    md.text(diff['about']['url']),
                    sep=' ',
                ),
                sep='\n',
            )
        elif diff['type'] == 'new_message':
            message += md.text(
                md.text(
                    md.text('📝'),
                    md.hbold(diff['about']['task']),
                    md.text('по'),
                    md.text(f"«{diff['about']['discipline']}»"),
                    sep=' '
                ),
                md.text(
                    md.text('Получено личное сообщение от преподавателя.'),
                    md.text(
                        md.text('Количество новых сообщений:'),
                        md.hcode(diff['current_messages']),
                        sep=' ',
                    ),
                    sep=' ',
                ),
                md.text(),
                md.text(
                    md.text('Подробности по ссылке:'),
                    md.text(diff['about']['url']),
                    sep=' ',
                ),
                sep='\n',
            )
        message += '\n' * 3
    return message


def compare(old_dict: dict, new_dict: dict) -> list:
    diffs = []
    for thread_id_old in old_dict:
        try:
            _ = new_dict[thread_id_old]
        except KeyError:
            raise exceptions.FileCompareError
        if old_dict[thread_id_old]['status'] != new_dict[thread_id_old]['status']:
            diffs.append({
                'type': 'new_status',  # or `new_message`
                'current_status': new_dict[thread_id_old]['status'],
                'about': new_dict[thread_id_old]['about'],
            })
        elif old_dict[thread_id_old]['new_messages'] > old_dict[thread_id_old]['new_messages']:
            diffs.append({
                'type': 'new_message',  # or `new_status`
                'current_messages': new_dict[thread_id_old]['new_messages'],
                'about': new_dict[thread_id_old]['about'],
            })
    return diffs


async def user_homeworks_check(user_telegram_id: int, session: aiohttp.ClientSession) -> None:
    student_json_file = config.STUDENT_FILE_JSON_MASK.format(id=user_telegram_id)
    path_users_to_file = os.path.join(config.BASEDIR, 'users_data', 'tracking_data', 'homeworks', student_json_file)
    try:
        homeworks_dict = await get_orioks_homeworks(session=session)
    except exceptions.OrioksCantParseData:
        logging.info('(HOMEWORKS) exception: utils.exceptions.OrioksCantParseData')
        safe_delete(path=path_users_to_file)
        return None
    if student_json_file not in os.listdir(os.path.dirname(path_users_to_file)):
        await JsonFile.save(data=homeworks_dict, filename=path_users_to_file)
        return None

    _old_json = await JsonFile.open(filename=path_users_to_file)
    old_dict = JsonFile.convert_dict_keys_to_int(_old_json)
    try:
        diffs = compare(old_dict=old_dict, new_dict=homeworks_dict)
    except exceptions.FileCompareError:
        await JsonFile.save(data=homeworks_dict, filename=path_users_to_file)
        return None

    if len(diffs) > 0:
        msg_to_send = await get_homeworks_to_msg(diffs=diffs)
        await SendToTelegram.text_message_to_user(user_telegram_id=user_telegram_id, message=msg_to_send)
    await JsonFile.save(data=homeworks_dict, filename=path_users_to_file)
