# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import platform
import subprocess

# third-party

# sjva 공용
from framework import db, path_app_root, path_data
from framework.util import Util

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting

#########################################################

class Logic(object):
	db_default = {
		'temp_path': os.path.join(path_data, 'download_tmp'),
		'save_path': os.path.join(path_data, 'download')
	}

	@staticmethod
	def db_init():
		try:
			for key, value in Logic.db_default.items():
				if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
					db.session.add(ModelSetting(key, value))
			db.session.commit()
		except Exception as e: 
			logger.error('Exception:%s', e)
			logger.error(traceback.format_exc())

	@staticmethod
	def plugin_load():
		try:
			logger.debug('%s plugin_load', package_name)
			Logic.db_init()	# DB 초기화
			if platform.system() == 'Windows':	# 윈도우일 때
				Logic.youtube_dl_path = os.path.join(path_app_root, 'bin', 'Windows', 'youtube-dl.exe')
				if not os.path.isfile(Logic.youtube_dl_path):	# youtube-dl.exe가 없으면
					Logic.youtube_dl_update()

			# 편의를 위해 json 파일 생성
			from plugin import plugin_info
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
	def setting_save(req):
		try:
			for key, value in req.form.items():
				logger.debug('Key:%s Value:%s', key, value)
				entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
				entity.value = value
			db.session.commit()
			return True
		except Exception as e: 
			logger.error('Exception:%s', e)
			logger.error(traceback.format_exc())
			return False

	@staticmethod
	def get_setting_value(key):
		try:
			return db.session.query(ModelSetting).filter_by(key=key).first().value
		except Exception as e: 
			logger.error('Exception:%s', e)
			logger.error(traceback.format_exc())

#########################################################

	youtube_dl_path = 'youtube-dl'
	youtube_dl_list = []

	@staticmethod
	def youtube_dl_update():
		if platform.system() == 'Windows':	# 윈도우일 때
			subprocess.call(['powershell', "(new-Object System.Net.WebClient).DownloadFile('https://yt-dl.org/latest/youtube-dl.exe', '%s')" % os.path.join(path_app_root, 'bin', 'Windows', 'youtube-dl.exe')])
		else:	# 나머지 Unix-like
			subprocess.call(['curl', '-L', 'https://yt-dl.org/downloads/latest/youtube-dl', '-o', '/usr/local/bin/youtube-dl'])
			subprocess.call(['chmod', 'a+rx', '/usr/local/bin/youtube-dl'])
