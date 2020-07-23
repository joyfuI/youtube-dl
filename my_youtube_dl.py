# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# python
import os
import traceback
import tempfile
from threading import Thread
import json
from datetime import datetime
from enum import Enum

# third-party

# sjva 공용, 패키지
import framework.common.celery as celery_shutil
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

    def __init__(self, plugin, url, filename, temp_path, save_path=None, opts=None):
        if save_path is None:
            save_path = temp_path
        if opts is None:
            opts = {}
        self.plugin = plugin
        self.url = url
        self.filename = filename
        if not os.path.isdir(temp_path):
            os.makedirs(temp_path)
        self.temp_path = tempfile.mkdtemp(prefix='youtube-dl_', dir=temp_path)
        if not os.path.isdir(save_path):
            os.makedirs(save_path)
        self.save_path = save_path
        self.opts = opts
        self.index = Youtube_dl._index
        Youtube_dl._index += 1
        self._status = Status.READY
        self._thread = None
        self.key = None
        self.start_time = None  # 시작 시간
        self.end_time = None  # 종료 시간
        self.info_dict = {  # info_dict에서 얻는 정보
            'extractor': None,  # 타입
            'title': None,  # 제목
            'uploader': None,  # 업로더
            'uploader_url': None  # 업로더 주소
        }
        # info_dict에서 얻는 정보(entries)
        # self.info_dict['playlist_index'] = None
        # self.info_dict['duration'] = None	# 길이
        # self.info_dict['format'] = None	# 포맷
        # self.info_dict['thumbnail'] = None	# 썸네일
        self.progress_hooks = {  # progress_hooks에서 얻는 정보
            'downloaded_bytes': None,  # 다운로드한 크기
            'total_bytes': None,  # 전체 크기
            'eta': None,  # 예상 시간(s)
            'speed': None  # 다운로드 속도(bytes/s)
        }

    def start(self):
        if self.status != Status.READY:
            return False
        self._thread = Thread(target=self.run)
        self._thread.start()
        return True

    def run(self):
        import youtube_dl
        import glob2
        try:
            self.start_time = datetime.now()
            self.status = Status.START
            info_dict = Youtube_dl.get_info_dict(self.url, self.opts.get('proxy'))  # 동영상 정보 가져오기
            if info_dict is None:  # 가져오기 실패
                self.status = Status.ERROR
                return
            self.info_dict['extractor'] = info_dict['extractor']
            self.info_dict['title'] = info_dict['title']
            self.info_dict['uploader'] = info_dict['uploader']
            self.info_dict['uploader_url'] = info_dict['uploader_url']
            ydl_opts = {
                'logger': MyLogger(),
                'progress_hooks': [self.my_hook],
                # 'match_filter': self.match_filter_func,
                'outtmpl': os.path.join(self.temp_path, self.filename),
                'ignoreerrors': True,
                'cachedir': False
            }
            ydl_opts.update(self.opts)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            if self.status == Status.FINISHED:  # 다운로드 성공
                for i in glob2.glob(self.temp_path + '/**/*'):
                    path = i.replace(self.temp_path, self.save_path, 1)
                    if os.path.isdir(i):
                        if not os.path.isdir(path):
                            os.mkdir(path)
                        continue
                    celery_shutil.move(i, path)  # 파일 이동
                self.status = Status.COMPLETED
        except Exception as e:
            self.status = Status.ERROR
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        finally:
            celery_shutil.rmtree(self.temp_path)  # 임시폴더 삭제
            if self.status != Status.STOP:
                self.end_time = datetime.now()

    def stop(self):
        if self.status in (Status.ERROR, Status.STOP, Status.COMPLETED):
            return False
        self.status = Status.STOP
        self.end_time = datetime.now()
        return True

    @staticmethod
    def get_version():
        import youtube_dl
        return youtube_dl.version.__version__

    @staticmethod
    def get_info_dict(url, proxy=None):
        import youtube_dl
        try:
            ydl_opts = {
                'simulate': True,
                'dump_single_json': True,
                'extract_flat': 'in_playlist',
                'logger': MyLogger()
            }
            if proxy:
                ydl_opts['proxy'] = proxy
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None
        return json.loads(Youtube_dl._last_msg)

    def my_hook(self, d):
        if self.status != Status.STOP:
            self.status = {
                'downloading': Status.DOWNLOADING,
                'error': Status.ERROR,
                'finished': Status.FINISHED  # 다운로드 완료. 변환 시작
            }[d['status']]
        if d['status'] != 'error':
            self.filename = os.path.basename(d.get('filename'))
            self.progress_hooks['downloaded_bytes'] = d.get('downloaded_bytes')
            self.progress_hooks['total_bytes'] = d.get('total_bytes')
            self.progress_hooks['eta'] = d.get('eta')
            self.progress_hooks['speed'] = d.get('speed')

    def match_filter_func(self, info_dict):
        self.info_dict['playlist_index'] = info_dict['playlist_index']
        self.info_dict['duration'] = info_dict['duration']
        self.info_dict['format'] = info_dict['format']
        self.info_dict['thumbnail'] = info_dict['thumbnail']
        return None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        from .plugin import socketio_emit
        self._status = value
        socketio_emit('status', self)


class MyLogger(object):
    def debug(self, msg):
        Youtube_dl._last_msg = msg
        if msg.find('') != -1 or msg.find('{') != -1:
            return  # 과도한 로그 방지
        logger.debug(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)
