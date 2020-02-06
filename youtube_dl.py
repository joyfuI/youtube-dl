# -*- coding: utf-8 -*-
# python
import os
import platform
from threading import Thread
import subprocess
import json
from datetime import datetime
from enum import Enum

# 패키지
from .plugin import logger
from .logic import Logic

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
			Logic.youtube_dl_path,
			'--print-json',
			'-o', os.path.join(self.temp_path, self.filename),
			'--exec', 'move /y {} ' + self.save_path + '\\' if platform.system() == 'Windows' else 'mv -f {} ' + self.save_path + '/',
			self.url
		]
		logger.debug(command)
		self._process = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)	# youtube-dl 실행
		data = json.loads(self._process.stdout.readline())	# 파일 정보
		self.filename = os.path.basename(data['_filename'])
		self.duration = data['duration']
		self.format = data['format']
		self.status = Status.START
		self.errorlevel = self._process.wait()	# 실행 결과
		logger.debug('returncode %d', self.errorlevel)
		self.end_time = datetime.now()
		if self.errorlevel == 0:	# 다운로드 성공
			self.status = Status.SUCCESS
		else:	# 다운로드 실패
			if self.status != Status.STOP:
				self.status = Status.FAILURE
			if platform.system() == 'Windows':	# 윈도우일 때
				logger.debug('del /q "' + self.temp_path + '\\' + ''.join(self.filename.split('.')[:-1]) + '"*')
				os.system('del /q "' + self.temp_path + '\\' + ''.join(self.filename.split('.')[:-1]) + '"*')	# 임시파일 삭제
			else:
				logger.debug('rm -f "' + self.temp_path + '/' + ''.join(self.filename.split('.')[:-1]) + '"*')
				os.system('rm -f "' + self.temp_path + '/' + ''.join(self.filename.split('.')[:-1]) + '"*')	# 임시파일 삭제

	def stop(self):
		self.status = Status.STOP
		self._process.terminate()
