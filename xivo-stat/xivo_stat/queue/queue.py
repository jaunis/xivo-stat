# -*- coding: UTF-8 -*-

from xivo_stat.dao import queue_log_dao
from xivo_stat.dao import call_on_queue_dao


def fill_full_call(start, end):
    full_calls = queue_log_dao.get_queue_full_call(start, end)
    for call in full_calls:
        call_on_queue_dao.add_full_call(call['callid'],
                                        call['time'],
                                        call['queue_name'])
