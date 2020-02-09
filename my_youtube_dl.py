# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# python
import os
import shutil
import tempfile
import glob
from threading import Thread
import json
from datetime import datetime
from enum import Enum

# third-party
import youtube_dl

# 패키지
from .plugin import logger

class Status(Enum):
	READY = 0
	START = 1
	DOWNLOADING = 2
	ERROR = 3
	FINISHED = 4
	STOP = 5
	COMPLETED = 6

	def __str__(self):
		str_list = [
			'준비',
			'분석중',
			'다운로드중',
			'실패',
			'변환중',
			'중지',
			'완료'
		]
		return str_list[self.value]

class Youtube_dl(object):
	_index = 0
	_last_msg = ''

	def __init__(self, url, filename, temp_path, save_path):
		self.url = url
		self.filename = filename
		self.temp_path = tempfile.mkdtemp(prefix='youtube-dl_', dir=temp_path)
		self.save_path = save_path
		self.index = Youtube_dl._index
		Youtube_dl._index += 1
		self.status = Status.READY
		self._thread = None
		self.start_time = None	# 시작 시간
		self.end_time = None	# 종료 시간
		# info_dict에서 얻는 정보
		self.extractor = None	# 타입
		self.title = None	# 제목
		self.uploader = None	# 업로더
		self.uploader_url = None	# 업로더 주소
		# info_dict에서 얻는 정보(entries)
		"""
		self.playlist_index = None
		self.duration = None	# 길이
		self.format = None	# 포맷
		self.thumbnail = None	# 썸네일
		"""
		# progress_hooks에서 얻는 정보
		self.downloaded_bytes = None	# 다운로드한 크기
		self.total_bytes = None	# 전체 크기
		self.eta = None	# 예상 시간(s)
		self.speed = None	# 다운로드 속도(bytes/s)

	def start(self):
		self._thread = Thread(target=self.run)
		self.start_time = datetime.now()
		self._thread.start()
		self.status = Status.START

	def run(self):
		info_dict = Youtube_dl.get_info_dict(self.url)	# 동영상 정보 가져오기
		if info_dict is None:	# 가져오기 실패
			self.status = Status.ERROR
			return
		self.extractor = info_dict['extractor']
		self.title = info_dict['title']
		self.uploader = info_dict['uploader']
		self.uploader_url = info_dict['uploader_url']
		ydl_opts = {
			'logger': MyLogger(),
			'progress_hooks': [self.my_hook],
			# 'match_filter': self.match_filter_func,
			'outtmpl': os.path.join(self.temp_path, self.filename)
		}
		with youtube_dl.YoutubeDL(ydl_opts) as ydl:
			ydl.download([self.url])
		if self.status == Status.FINISHED:	# 다운로드 성공
			for i in glob.glob(self.temp_path + '/*'):
				shutil.move(i, self.save_path)	# 파일 이동
			self.status = Status.COMPLETED
		shutil.rmtree(self.temp_path)	# 임시폴더 삭제
		self.end_time = datetime.now()

	def stop(self):
		self.status = Status.STOP
		self.end_time = datetime.now()

	@staticmethod
	def get_version():
		return youtube_dl.version.__version__

	@staticmethod
	def get_info_dict(url):
		try:
			ydl_opts = {
				'simulate': True,
				'dump_single_json': True,
				'logger': MyLogger()
			}
			with youtube_dl.YoutubeDL(ydl_opts) as ydl:
				ydl.download([url])
		except Exception as e:
			return None
		return json.loads(Youtube_dl._last_msg)

	def my_hook(self, d):
		if self.status != Status.STOP:
			self.status = {
				'downloading': Status.DOWNLOADING,
				'error': Status.ERROR,
				'finished': Status.FINISHED	# 다운로드 완료. 변환 시작
			}[d['status']]
		if d['status'] != 'error':
			self.filename = os.path.basename(d.get('filename'))
			self.downloaded_bytes = d.get('downloaded_bytes')
			self.total_bytes = d.get('total_bytes')
			self.eta = d.get('eta')
			self.speed = d.get('speed')

	def match_filter_func(self, info_dict):
		self.playlist_index = info_dict['playlist_index']
		self.duration = info_dict['duration']
		self.format = info_dict['format']
		self.thumbnail = info_dict['thumbnail']
		return None

class MyLogger(object):
	def debug(self, msg):
		Youtube_dl._last_msg = msg
		if msg.find('') != -1 or msg.find('{') != -1:
			return	# 과도한 로그 방지
		logger.debug(msg)

	def warning(self, msg):
		logger.warning(msg)

	def error(self, msg):
		logger.error(msg)
