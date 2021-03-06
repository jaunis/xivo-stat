# -*- coding: utf-8 -*-

# Copyright (C) 2012-2014 Avencall
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

import argparse
import logging
import re
import sys

from datetime import datetime

from xivo import argparse_cmd, pid_file
from xivo_stat import core

PIDFILENAME = '/var/run/xivo-stat.pid'


def main():
    if pid_file.is_already_running(PIDFILENAME):
        print 'XiVO stat is already running'
        sys.exit(1)

    command = _XivoStatCommand()
    with pid_file.pidfile(PIDFILENAME):
        argparse_cmd.execute_command(command)


class _XivoStatCommand(argparse_cmd.AbstractCommand):

    def pre_execute(self, _):
        self._init_logging()

    def _init_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
        root_logger.addHandler(handler)

    def configure_subcommands(self, subcommands):
        subcommands.add_subcommand(_FillDbSubcommand('fill_db'))
        subcommands.add_subcommand(_CleanDbSubcommand('clean_db'))


class _FillDbSubcommand(argparse_cmd.AbstractSubcommand):
    _HELP_DATETIME_FORMAT = '%%Y-%%m-%%dT%%H:%%M:%%S'
    _DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

    def configure_parser(self, parser):
        parser.add_argument('--start',
                            type=_datetime_iso,
                            help='Start date to generate the statistics using this format: %s' % self._HELP_DATETIME_FORMAT)
        parser.add_argument('--end',
                            type=_datetime_iso,
                            default=datetime.now().strftime(self._DATETIME_FORMAT),
                            help='End date to generate the statistics using this format: %s' % self._HELP_DATETIME_FORMAT)

    def execute(self, parsed_args):
        core.update_db(start_date=parsed_args.start,
                       end_date=parsed_args.end)


class _CleanDbSubcommand(argparse_cmd.AbstractSubcommand):

    def execute(self, _):
        core.clean_db()


def _datetime_iso(value):
    datetime_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
    datetime_pattern_re = re.compile(datetime_pattern)
    if not datetime_pattern_re.match(value):
        raise argparse.ArgumentTypeError('%s is not a valid datetime format' % value)
    return value
