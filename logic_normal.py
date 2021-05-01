import traceback
from datetime import datetime

from flask import jsonify

from framework.logger import get_logger

from .my_youtube_dl import MyYoutubeDL, Status

package_name = __name__.split('.')[0]
logger = get_logger(package_name)


class LogicNormal(object):
    youtube_dl_list = []

    @staticmethod
    def get_youtube_dl_package(index=None, import_pkg=False):
        packages = ['youtube-dl', 'yt-dlp']
        import_name = ['youtube_dl', 'yt_dlp']
        if import_pkg:
            return import_name if index is None else import_name[int(index)]
        else:
            return packages if index is None else packages[int(index)]

    @staticmethod
    def get_youtube_dl_version():
        try:
            return MyYoutubeDL.get_version()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return '패키지 임포트 실패'

    @staticmethod
    def get_default_filename():
        return MyYoutubeDL.DEFAULT_FILENAME

    @staticmethod
    def get_preset_list():
        return [
            ['bestvideo+bestaudio/best', '최고 화질'],
            ['bestvideo[height<=1080]+bestaudio/best[height<=1080]', '1080p'],
            ['worstvideo+worstaudio/worst', '최저 화질'],
            ['bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]', '최고 화질(mp4)'],
            ['bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]', '1080p(mp4)'],
            ['bestvideo[filesize<50M]+bestaudio/best[filesize<50M]', '50MB 미만'],
            ['bestaudio/best', '오디오만'],
            ['_custom', '사용자 정의']
        ]

    @staticmethod
    def get_postprocessor_list():
        return [
            ['', '후처리 안함', None],
            ['mp4', 'MP4', '비디오 변환'],
            ['flv', 'FLV', '비디오 변환'],
            ['webm', 'WebM', '비디오 변환'],
            ['ogg', 'Ogg', '비디오 변환'],
            ['mkv', 'MKV', '비디오 변환'],
            ['ts', 'TS', '비디오 변환'],
            ['avi', 'AVI', '비디오 변환'],
            ['wmv', 'WMV', '비디오 변환'],
            ['mov', 'MOV', '비디오 변환'],
            ['gif', 'GIF', '비디오 변환'],
            ['mp3', 'MP3', '오디오 추출'],
            ['aac', 'AAC', '오디오 추출'],
            ['flac', 'FLAC', '오디오 추출'],
            ['m4a', 'M4A', '오디오 추출'],
            ['opus', 'Opus', '오디오 추출'],
            ['vorbis', 'Vorbis', '오디오 추출'],
            ['wav', 'WAV', '오디오 추출']
        ]

    @staticmethod
    def get_postprocessor():
        video_convertor = []
        extract_audio = []
        for i in LogicNormal.get_postprocessor_list():
            if i[2] == '비디오 변환':
                video_convertor.append(i[0])
            elif i[2] == '오디오 추출':
                extract_audio.append(i[0])
        return video_convertor, extract_audio

    @staticmethod
    def download(**kwagrs):
        try:
            logger.debug(kwagrs)
            plugin = kwagrs['plugin']
            url = kwagrs['url']
            filename = kwagrs['filename']
            temp_path = kwagrs['temp_path']
            save_path = kwagrs['save_path']
            opts = {}
            if 'format' in kwagrs and kwagrs['format']:
                opts['format'] = kwagrs['format']
            postprocessor = []
            if 'preferedformat' in kwagrs and kwagrs['preferedformat']:
                postprocessor.append({
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': kwagrs['preferedformat']
                })
            if 'preferredcodec' in kwagrs and kwagrs['preferredcodec']:
                postprocessor.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': kwagrs['preferredcodec'],
                    'preferredquality': str(kwagrs['preferredquality'])
                })
            if postprocessor:
                opts['postprocessors'] = postprocessor
            if 'playlist' in kwagrs and kwagrs['playlist']:
                if kwagrs['playlist'] == 'reverse':
                    opts['playlistreverse'] = True
                elif kwagrs['playlist'] == 'random':
                    opts['playlistrandom'] = True
                else:
                    opts['playlist_items'] = kwagrs['playlist']
            if 'archive' in kwagrs and kwagrs['archive']:
                opts['download_archive'] = kwagrs['archive']
            if 'proxy' in kwagrs and kwagrs['proxy']:
                opts['proxy'] = kwagrs['proxy']
            if 'ffmpeg_path' in kwagrs and kwagrs['ffmpeg_path']:
                opts['ffmpeg_location'] = kwagrs['ffmpeg_path']
            if 'cookiefile' in kwagrs and kwagrs['cookiefile']:
                opts['cookiefile'] = kwagrs['cookiefile']
            dateafter = kwagrs.get('dateafter')
            youtube_dl = MyYoutubeDL(plugin, 'video', url, filename, temp_path, save_path, opts, dateafter)
            youtube_dl.key = kwagrs.get('key')
            LogicNormal.youtube_dl_list.append(youtube_dl)  # 리스트 추가
            return youtube_dl
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def thumbnail(**kwagrs):
        try:
            logger.debug(kwagrs)
            plugin = kwagrs['plugin']
            url = kwagrs['url']
            filename = kwagrs['filename']
            temp_path = kwagrs['temp_path']
            save_path = kwagrs['save_path']
            opts = {
                'skip_download': True
            }
            if 'all_thumbnails' in kwagrs and str(kwagrs['all_thumbnails']).lower() != 'false':
                opts['write_all_thumbnails'] = True
            else:
                opts['writethumbnail'] = True
            if 'playlist' in kwagrs and kwagrs['playlist']:
                if kwagrs['playlist'] == 'reverse':
                    opts['playlistreverse'] = True
                elif kwagrs['playlist'] == 'random':
                    opts['playlistrandom'] = True
                else:
                    opts['playlist_items'] = kwagrs['playlist']
            if 'archive' in kwagrs and kwagrs['archive']:
                opts['download_archive'] = kwagrs['archive']
            if 'proxy' in kwagrs and kwagrs['proxy']:
                opts['proxy'] = kwagrs['proxy']
            if 'ffmpeg_path' in kwagrs and kwagrs['ffmpeg_path']:
                opts['ffmpeg_location'] = kwagrs['ffmpeg_path']
            if 'cookiefile' in kwagrs and kwagrs['cookiefile']:
                opts['cookiefile'] = kwagrs['cookiefile']
            dateafter = kwagrs.get('dateafter')
            youtube_dl = MyYoutubeDL(plugin, 'thumbnail', url, filename, temp_path, save_path, opts, dateafter)
            youtube_dl.key = kwagrs.get('key')
            LogicNormal.youtube_dl_list.append(youtube_dl)  # 리스트 추가
            return youtube_dl
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def sub(**kwagrs):
        try:
            logger.debug(kwagrs)
            plugin = kwagrs['plugin']
            url = kwagrs['url']
            filename = kwagrs['filename']
            temp_path = kwagrs['temp_path']
            save_path = kwagrs['save_path']
            opts = {
                'skip_download': True
            }
            sub_lang = map(lambda x: x.strip(), kwagrs['sub_lang'].split(','))  # 문자열을 리스트로 변환
            if 'all_subs' in kwagrs and str(kwagrs['all_subs']).lower() != 'false':
                opts['allsubtitles'] = True
            else:
                opts['subtitleslangs'] = sub_lang
            if 'auto_sub' in kwagrs and str(kwagrs['auto_sub']).lower() != 'false':
                opts['writeautomaticsub'] = True
            else:
                opts['writesubtitles'] = True
            if 'playlist' in kwagrs and kwagrs['playlist']:
                if kwagrs['playlist'] == 'reverse':
                    opts['playlistreverse'] = True
                elif kwagrs['playlist'] == 'random':
                    opts['playlistrandom'] = True
                else:
                    opts['playlist_items'] = kwagrs['playlist']
            if 'archive' in kwagrs and kwagrs['archive']:
                opts['download_archive'] = kwagrs['archive']
            if 'proxy' in kwagrs and kwagrs['proxy']:
                opts['proxy'] = kwagrs['proxy']
            if 'ffmpeg_path' in kwagrs and kwagrs['ffmpeg_path']:
                opts['ffmpeg_location'] = kwagrs['ffmpeg_path']
            if 'cookiefile' in kwagrs and kwagrs['cookiefile']:
                opts['cookiefile'] = kwagrs['cookiefile']
            dateafter = kwagrs.get('dateafter')
            youtube_dl = MyYoutubeDL(plugin, 'subtitle', url, filename, temp_path, save_path, opts, dateafter)
            youtube_dl.key = kwagrs.get('key')
            LogicNormal.youtube_dl_list.append(youtube_dl)  # 리스트 추가
            return youtube_dl
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def get_data(youtube_dl):
        try:
            data = {}
            data['plugin'] = youtube_dl.plugin
            data['url'] = youtube_dl.url
            data['filename'] = youtube_dl.filename
            data['temp_path'] = youtube_dl.temp_path
            data['save_path'] = youtube_dl.save_path
            data['index'] = youtube_dl.index
            data['status_str'] = youtube_dl.status.name
            data['status_ko'] = str(youtube_dl.status)
            data['end_time'] = ''
            data['extractor'] = youtube_dl.type + (
                ' - ' + youtube_dl.info_dict['extractor'] if youtube_dl.info_dict['extractor'] is not None else '')
            data['title'] = youtube_dl.info_dict['title'] if \
                youtube_dl.info_dict['title'] is not None else youtube_dl.url
            data['uploader'] = youtube_dl.info_dict['uploader'] if youtube_dl.info_dict['uploader'] is not None else ''
            data['uploader_url'] = youtube_dl.info_dict['uploader_url'] if \
                youtube_dl.info_dict['uploader_url'] is not None else ''
            data['downloaded_bytes_str'] = ''
            data['total_bytes_str'] = ''
            data['percent'] = '0'
            data['eta'] = youtube_dl.progress_hooks['eta'] if youtube_dl.progress_hooks['eta'] is not None else ''
            data['speed_str'] = LogicNormal.human_readable_size(youtube_dl.progress_hooks['speed'], '/s') if \
                youtube_dl.progress_hooks['speed'] is not None else ''
            if youtube_dl.status == Status.READY:  # 다운로드 전
                data['start_time'] = ''
                data['download_time'] = ''
            else:
                if youtube_dl.end_time is None:  # 완료 전
                    download_time = datetime.now() - youtube_dl.start_time
                else:
                    download_time = youtube_dl.end_time - youtube_dl.start_time
                    data['end_time'] = youtube_dl.end_time.strftime('%m-%d %H:%M:%S')
                if None not in (youtube_dl.progress_hooks['downloaded_bytes'],
                                youtube_dl.progress_hooks['total_bytes']):  # 둘 다 값이 있으면
                    data['downloaded_bytes_str'] = LogicNormal.human_readable_size(
                        youtube_dl.progress_hooks['downloaded_bytes']
                    )
                    data['total_bytes_str'] = LogicNormal.human_readable_size(youtube_dl.progress_hooks['total_bytes'])
                    data['percent'] = '%.2f' % (float(youtube_dl.progress_hooks['downloaded_bytes'])
                                                / float(youtube_dl.progress_hooks['total_bytes']) * 100)
                data['start_time'] = youtube_dl.start_time.strftime('%m-%d %H:%M:%S')
                data['download_time'] = '%02d:%02d' % (download_time.seconds / 60, download_time.seconds % 60)
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def get_info_dict(url, proxy):
        return MyYoutubeDL.get_info_dict(url, proxy)

    @staticmethod
    def human_readable_size(size, suffix=''):
        for unit in ('Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB'):
            if size < 1024.0:
                return '%3.1f %s%s' % (size, unit, suffix)
            size /= 1024.0
        return '%.1f %s%s' % (size, 'YB', suffix)

    @staticmethod
    def abort(base, code):
        base['errorCode'] = code
        return jsonify(base)
