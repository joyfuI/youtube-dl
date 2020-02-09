# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import platform
from datetime import datetime

# third-party

# sjva 공용
from framework import db, path_data
from framework.util import Util

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting
from .my_youtube_dl import Status

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

			# youtube-dl 업데이트
			if platform.system() == 'Windows':	# 윈도우일 때
				os.system('pip.exe install --upgrade youtube-dl')
			else:
				os.system('pip install --upgrade youtube-dl')

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

	youtube_dl_list = []

	@staticmethod
	def get_data(youtube_dl):
		try:
			data = { }
			data['url'] = youtube_dl.url
			data['filename'] = youtube_dl.filename
			data['temp_path'] = youtube_dl.temp_path
			data['save_path'] = youtube_dl.save_path
			data['index'] = youtube_dl.index
			data['status_str'] = youtube_dl.status.name
			data['status_ko'] = str(youtube_dl.status)
			data['end_time'] = ''
			data['extractor'] = youtube_dl.extractor if youtube_dl.extractor is not None else ''
			data['title'] = youtube_dl.title if youtube_dl.title is not None else youtube_dl.url
			data['uploader'] = youtube_dl.uploader if youtube_dl.uploader is not None else ''
			data['uploader_url'] = youtube_dl.uploader_url if youtube_dl.uploader_url is not None else ''
			data['downloaded_bytes_str'] = ''
			data['total_bytes_str'] = ''
			data['percent'] = '0'
			data['eta'] = youtube_dl.eta if youtube_dl.eta is not None else ''
			data['speed_str'] = Logic.human_readable_size(youtube_dl.speed, '/s') if youtube_dl.speed is not None else ''
			if youtube_dl.status == Status.READY:	# 다운로드 전
				data['start_time'] = ''
				data['download_time'] = ''
			else:
				if youtube_dl.end_time is None:	# 완료 전
					download_time = datetime.now() - youtube_dl.start_time
				else:
					download_time = youtube_dl.end_time - youtube_dl.start_time
					data['end_time'] = youtube_dl.end_time.strftime('%m-%d %H:%M:%S')
				if None not in (youtube_dl.downloaded_bytes, youtube_dl.total_bytes):	# 둘 다 값이 있으면
					data['downloaded_bytes_str'] = Logic.human_readable_size(youtube_dl.downloaded_bytes)
					data['total_bytes_str'] = Logic.human_readable_size(youtube_dl.total_bytes)
					data['percent'] = '%.2f' % (float(youtube_dl.downloaded_bytes) / float(youtube_dl.total_bytes) * 100)
				data['start_time'] = youtube_dl.start_time.strftime('%m-%d %H:%M:%S')
				data['download_time'] = '%02d:%02d' % (download_time.seconds / 60, download_time.seconds % 60)
			return data
		except Exception as e:
			logger.error('Exception:%s', e)
			logger.error(traceback.format_exc())
			return None

	@staticmethod
	def human_readable_size(size, suffix=''):
		for unit in ['Bytes','KB','MB','GB','TB','PB','EB','ZB']:
			if size < 1024.0:
				return '%3.1f %s%s' % (size, unit, suffix)
			size /= 1024.0
		return '%.1f %s%s' % (size, 'YB', suffix)
