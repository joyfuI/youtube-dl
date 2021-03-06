# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import platform
import subprocess
import traceback
import sqlite3

# third-party

# sjva 공용
from framework import db, path_app_root, path_data
from framework.util import Util

# 패키지
from .plugin import logger, package_name
from .logic_normal import LogicNormal
from .model import ModelSetting
#########################################################

class Logic(object):
    db_default = {
        'db_version': '2',
        'youtube_dl_package': '0',
        'ffmpeg_path': '' if platform.system() != 'Windows' else os.path.join(path_app_root, 'bin', 'Windows', 'ffmpeg.exe'),
        'temp_path': os.path.join(path_data, 'download_tmp'),
        'save_path': os.path.join(path_data, 'download'),
        'default_filename': '',
        'proxy': '',
        'activate_cors': False
    }

    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
            Logic.migration()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            Logic.db_init()

            # 모듈 설치
            try:
                import glob2
            except ImportError:
                logger.debug('glob2 install')
                logger.debug(subprocess.check_output([sys.executable, '-m', 'pip', 'install', 'glob2'], universal_newlines=True))

            # youtube-dl 업데이트
            youtube_dl = LogicNormal.get_youtube_dl_package(ModelSetting.get('youtube_dl_package'))
            logger.debug('%s upgrade' % youtube_dl)
            logger.debug(subprocess.check_output([sys.executable, '-m', 'pip', 'install', '--upgrade', youtube_dl], universal_newlines=True))

            # 편의를 위해 json 파일 생성
            from .plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def migration():
        try:
            db_version = ModelSetting.get_int('db_version')
            connect = sqlite3.connect(os.path.join(path_data, 'db', '%s.db' % package_name))

            if db_version < 2:
                logger.debug('youtube-dlc uninstall')
                logger.debug(subprocess.check_output([sys.executable, '-m', 'pip', 'uninstall', '-y', 'youtube-dlc'], universal_newlines=True))

            connect.commit()
            connect.close()
            ModelSetting.set('db_version', Logic.db_default['db_version'])
            db.session.flush()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
