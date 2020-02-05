# -*- coding: utf-8 -*-
# python
import os
from threading import Thread
import subprocess
import json
from datetime import datetime
from enum import Enum

# 패키지
from .plugin import logger

class Status(Enum):
	READY = 0
	START = 1
	STOP = 2
	SUCCESS = 3
	FAILURE = 4

	def __str__(self):
		str_list = [
			'준비',
			'다운로드중',
			'중지',
			'완료',
			'실패'
		]
		return str_list[self.value]

class Youtube_dl(object):
	_index = 0

	def __init__(self, url, filename, temp_path, save_path):
		self.url = url
		self.filename = filename
		self.temp_path = temp_path
		self.save_path = save_path
		self.index = Youtube_dl._index
		Youtube_dl._index += 1
		self.status = Status.READY
		self._thread = None
		self._process = None
		self.start_time = None
		self.end_time = None
		self.duration = None
		self.format = None
		self.errorlevel = None

	def start(self):
		self._thread = Thread(target=self.run)
		self.start_time = datetime.now()
		self._thread.start()

	def run(self):
		command = [
			'youtube-dl',
			'--print-json',
			'-o', self.temp_path + '/' + self.filename,
			'--exec', 'mv {} ' + self.save_path + '/',
			self.url
		]
		self._process = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)	# youtube-dl 실행
		data = json.loads(self._process.stdout.readline())	# 파일 정보
		self.filename = data['_filename'].split('/')[-1]
		self.duration = data['duration']
		self.format = data['format']
		self.status = Status.START
		self.errorlevel = self._process.wait()	# 실행 결과
		self.end_time = datetime.now()
		if self.errorlevel == 0:	# 다운로드 성공
			self.status = Status.SUCCESS
		else:	# 다운로드 실패
			logger.debug('returncode %d', self.errorlevel)
			if self.status != Status.STOP:
				self.status = Status.FAILURE
			logger.debug('rm -f ' + self.temp_path + '/' + ''.join(str.split('.')[:-1]) + '*')
			os.system('rm -f ' + self.temp_path + '/' + ''.join(str.split('.')[:-1]) + '*')	# 임시 파일 삭제

	def stop(self):
		self.status = Status.STOP
		self._process.terminate()
