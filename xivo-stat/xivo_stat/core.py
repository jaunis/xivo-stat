# -*- coding: utf-8 -*-

# Copyright (C) 2013 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging
import datetime
import sys

from xivo_stat import queue
from xivo_stat import agent
from xivo_dao import stat_queue_periodic_dao
from xivo_dao import stat_agent_periodic_dao
from xivo_dao import stat_call_on_queue_dao
from xivo_dao import queue_log_dao
from xivo_dao import stat_queue_dao
from xivo_dao import stat_agent_dao
from sqlalchemy.exc import IntegrityError
from xivo_dao.helpers.db_manager import session

logger = logging.getLogger(__name__)

_ERASE_TIME_WHEN_STARTING = datetime.timedelta(hours=8)
DELTA_1HOUR = datetime.timedelta(hours=1)
dao_sess = session()


def hour_start(t):
    return datetime.datetime(t.year,
                             t.month,
                             t.day,
                             t.hour)


def end_of_previous_hour(t):
    return hour_start(t) - datetime.timedelta(microseconds=1)


def get_start_time():
    try:
        start = hour_start(stat_queue_periodic_dao.get_most_recent_time(dao_sess))
    except LookupError:
        try:
            start = hour_start(queue_log_dao.get_first_time(dao_sess))
        except LookupError:
            raise RuntimeError('No data to generate stats from')
    return start - _ERASE_TIME_WHEN_STARTING


def get_end_time():
    return datetime.datetime.now()


def get_start_end_time():
    return get_start_time(), get_end_time()


def _clean_up_after_error(dao_sess):
    logger.info('Inconsistent cache, cleaning up...')
    dao_sess.rollback()
    sys.exit(1)


def update_db():
    try:
        start, end = get_start_end_time()
    except RuntimeError:
        return

    logger.info('Filling cache into DB')
    logger.info('Start Time: %s, End time: %s', start, end)
    try:
        dao_sess.begin()
        insert_missing_queues(start, end)
        insert_missing_agents()
        dao_sess.commit()

        dao_sess.begin()
        queue.remove_after_start(dao_sess, start)
        agent.remove_after_start(dao_sess, start)
        queue.fill_simple_calls(dao_sess, start, end)
        dao_sess.commit()

        agent.insert_periodic_stat(dao_sess, start, end)

        for period_start in queue_log_dao.hours_with_calls(dao_sess, start, end):
            period_end = period_start + datetime.timedelta(hours=1) - datetime.timedelta(microseconds=1)
            queue.fill_calls(dao_sess, period_start, period_end)
            queue.insert_periodic_stat(dao_sess, period_start, period_end)
    except (IntegrityError, KeyboardInterrupt):
        _clean_up_after_error(dao_sess)


def clean_db():
    stat_call_on_queue_dao.clean_table(dao_sess)
    stat_agent_periodic_dao.clean_table(dao_sess)
    stat_queue_periodic_dao.clean_table(dao_sess)
    stat_agent_dao.clean_table(dao_sess)
    stat_queue_dao.clean_table(dao_sess)


def insert_missing_agents():
    logger.info('Inserting missing agents...')
    stat_agent_dao.insert_missing_agents(dao_sess)


def insert_missing_queues(start, end):
    logger.info('Inserting missing queues...')
    queue_names = queue_log_dao.get_queue_names_in_range(dao_sess, start, end)
    stat_queue_dao.insert_if_missing(dao_sess, queue_names)
