from __future__ import unicode_literals

import os
import traceback
import tempfile
import json
from glob import glob
from datetime import datetime
from threading import Thread
from enum import Enum

from framework.logger import get_logger
import framework.common.celery as celery_shutil

package_name = __name__.split('.')[0]
logger = get_logger(package_name)


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


class MyYoutubeDL(object):
    DEFAULT_FILENAME = '%(title)s-%(id)s.%(ext)s'

    _index = 0
    _last_msg = ''

    def __init__(self, plugin, type_name, url, filename, temp_path, save_path=None, opts=None, dateafter=None,
                 datebefore=None):
        # from youtube_dl.utils import DateRange
        from .plugin import youtube_dl_package
        DateRange = __import__('%s.utils' % youtube_dl_package, fromlist=[
                               'DateRange']).DateRange

        if save_path is None:
            save_path = temp_path
        if opts is None:
            opts = {}
        self.plugin = plugin
        self.type = type_name
        self.url = url
        self.filename = filename
        if not os.path.isdir(temp_path):
            os.makedirs(temp_path)
        self.temp_path = tempfile.mkdtemp(prefix='youtube-dl_', dir=temp_path)
        if not os.path.isdir(save_path):
            os.makedirs(save_path)
        self.save_path = save_path
        self.opts = opts
        if dateafter or datebefore:
            self.opts['daterange'] = DateRange(start=dateafter, end=datebefore)
        self.index = MyYoutubeDL._index
        MyYoutubeDL._index += 1
        self._status = Status.READY
        self._thread = None
        self.key = None
        self.start_time = None  # 시작 시간
        self.end_time = None  # 종료 시간
        # info_dict에서 얻는 정보
        self.info_dict = {
            'extractor': None,  # 타입
            'title': None,  # 제목
            'uploader': None,  # 업로더
            'uploader_url': None  # 업로더 주소
        }
        # info_dict에서 얻는 정보(entries)
        # self.info_dict['playlist_index'] = None
        # self.info_dict['duration'] = None  # 길이
        # self.info_dict['format'] = None  # 포맷
        # self.info_dict['thumbnail'] = None  # 썸네일
        # progress_hooks에서 얻는 정보
        self.progress_hooks = {
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
        # import youtube_dl
        from .plugin import youtube_dl_package
        youtube_dl = __import__('%s' % youtube_dl_package)

        try:
            self.start_time = datetime.now()
            self.status = Status.START
            # 동영상 정보 가져오기
            info_dict = MyYoutubeDL.get_info_dict(
                self.url, self.opts.get('proxy'), self.opts.get('cookiefile'))
            if info_dict is None:
                self.status = Status.ERROR
                return
            self.info_dict['extractor'] = info_dict['extractor']
            self.info_dict['title'] = info_dict.get('title', info_dict['id'])
            self.info_dict['uploader'] = info_dict.get('uploader', '')
            self.info_dict['uploader_url'] = info_dict.get('uploader_url', '')
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
            if self.status in (Status.START, Status.FINISHED):  # 다운로드 성공
                for i in glob(self.temp_path + '/**/*', recursive=True):
                    path = i.replace(self.temp_path, self.save_path, 1)
                    if os.path.isdir(i):
                        if not os.path.isdir(path):
                            os.mkdir(path)
                        continue
                    celery_shutil.move(i, path)
                self.status = Status.COMPLETED
        except Exception as e:
            self.status = Status.ERROR
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        finally:
            # 임시폴더 삭제
            celery_shutil.rmtree(self.temp_path)
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
        # from youtube_dl.version import __version__
        from .plugin import youtube_dl_package
        __version__ = __import__('%s.version' % youtube_dl_package, fromlist=[
                                 '__version__']).__version__

        return __version__

    @staticmethod
    def get_info_dict(url, proxy=None, cookiefile=None):
        # import youtube_dl
        from .plugin import youtube_dl_package
        youtube_dl = __import__('%s' % youtube_dl_package)

        try:
            ydl_opts = {
                'extract_flat': 'in_playlist',
                'logger': MyLogger()
            }
            if proxy:
                ydl_opts['proxy'] = proxy
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None
        return info

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
        MyYoutubeDL._last_msg = msg
        if msg.find('') != -1 or msg.find('{') != -1:
            # 과도한 로그 방지
            return
        logger.debug(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)
