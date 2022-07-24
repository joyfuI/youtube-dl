import os
import sys
import platform
import traceback
import subprocess
import sqlite3
from datetime import datetime

from flask import render_template, jsonify

from framework import db, path_app_root, path_data, socketio
from framework.common.plugin import LogicModuleBase, default_route_socketio

from .plugin import Plugin
from .my_youtube_dl import MyYoutubeDL, Status

logger = Plugin.logger
package_name = Plugin.package_name
ModelSetting = Plugin.ModelSetting


class LogicMain(LogicModuleBase):
    db_default = {
        "db_version": "2",
        "youtube_dl_package": "1",
        "ffmpeg_path": ""
        if platform.system() != "Windows"
        else os.path.join(path_app_root, "bin", "Windows", "ffmpeg.exe"),
        "temp_path": os.path.join(path_data, "download_tmp"),
        "save_path": os.path.join(path_data, "download"),
        "default_filename": "",
        "proxy": "",
    }

    def __init__(self, plugin):
        super(LogicMain, self).__init__(plugin, None)
        self.name = package_name  # 모듈명
        default_route_socketio(plugin, self)

    def plugin_load(self):
        try:
            # youtube-dl 업데이트
            youtube_dl = Plugin.youtube_dl_packages[
                int(ModelSetting.get("youtube_dl_package"))
            ]
            logger.debug(f"{youtube_dl} upgrade")
            logger.debug(
                subprocess.check_output(
                    [sys.executable, "-m", "pip", "install", "--upgrade", youtube_dl],
                    universal_newlines=True,
                )
            )
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())

    def process_menu(self, sub, req):
        try:
            arg = {
                "package_name": package_name,
                "sub": sub,
                "template_name": f"{package_name}_{sub}",
                "package_version": Plugin.plugin_info["version"],
            }

            if sub == "setting":
                arg.update(ModelSetting.to_dict())
                arg["package_list"] = Plugin.youtube_dl_packages
                arg["youtube_dl_version"] = LogicMain.get_youtube_dl_version()
                arg["DEFAULT_FILENAME"] = LogicMain.get_default_filename()

            elif sub == "download":
                default_filename = ModelSetting.get("default_filename")
                arg["filename"] = (
                    default_filename
                    if default_filename
                    else LogicMain.get_default_filename()
                )
                arg["preset_list"] = LogicMain.get_preset_list()
                arg["postprocessor_list"] = LogicMain.get_postprocessor_list()

            elif sub == "thumbnail":
                default_filename = ModelSetting.get("default_filename")
                arg["filename"] = (
                    default_filename
                    if default_filename
                    else LogicMain.get_default_filename()
                )

            elif sub == "sub":
                default_filename = ModelSetting.get("default_filename")
                arg["filename"] = (
                    default_filename
                    if default_filename
                    else LogicMain.get_default_filename()
                )

            elif sub == "list":
                pass

            return render_template(f"{package_name}_{sub}.html", arg=arg)
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())
            return render_template("sample.html", title=f"{package_name} - {sub}")

    def process_ajax(self, sub, req):
        try:
            logger.debug("AJAX: %s, %s", sub, req.values)
            ret = {"ret": "success"}

            if sub == "ffmpeg_version":
                path = req.form["path"]
                output = subprocess.check_output([path, "-version"])
                output = output.decode().replace("\n", "<br>")
                ret["data"] = output

            elif sub == "download":
                postprocessor = req.form["postprocessor"]
                video_convertor, extract_audio = LogicMain.get_postprocessor()
                preferedformat = None
                preferredcodec = None
                preferredquality = None
                if postprocessor in video_convertor:
                    preferedformat = postprocessor
                elif postprocessor in extract_audio:
                    preferredcodec = postprocessor
                    preferredquality = 192
                youtube_dl = LogicMain.download(
                    plugin=package_name,
                    url=req.form["url"],
                    filename=req.form["filename"],
                    temp_path=ModelSetting.get("temp_path"),
                    save_path=ModelSetting.get("save_path"),
                    format=req.form["format"],
                    preferedformat=preferedformat,
                    preferredcodec=preferredcodec,
                    preferredquality=preferredquality,
                    proxy=ModelSetting.get("proxy"),
                    ffmpeg_path=ModelSetting.get("ffmpeg_path"),
                )
                youtube_dl.start()
                LogicMain.socketio_emit("add", youtube_dl)
                ret["ret"] = "info"
                ret["msg"] = "분석중..."

            elif sub == "thumbnail":
                youtube_dl = LogicMain.thumbnail(
                    plugin=package_name,
                    url=req.form["url"],
                    filename=req.form["filename"],
                    temp_path=ModelSetting.get("temp_path"),
                    save_path=ModelSetting.get("save_path"),
                    all_thumbnails=req.form["all_thumbnails"],
                    proxy=ModelSetting.get("proxy"),
                    ffmpeg_path=ModelSetting.get("ffmpeg_path"),
                )
                youtube_dl.start()
                LogicMain.socketio_emit("add", youtube_dl)
                ret["ret"] = "info"
                ret["msg"] = "분석중..."

            elif sub == "sub":
                youtube_dl = LogicMain.sub(
                    plugin=package_name,
                    url=req.form["url"],
                    filename=req.form["filename"],
                    temp_path=ModelSetting.get("temp_path"),
                    save_path=ModelSetting.get("save_path"),
                    all_subs=req.form["all_subs"],
                    sub_lang=req.form["sub_lang"],
                    auto_sub=req.form["auto_sub"],
                    proxy=ModelSetting.get("proxy"),
                    ffmpeg_path=ModelSetting.get("ffmpeg_path"),
                )
                youtube_dl.start()
                LogicMain.socketio_emit("add", youtube_dl)
                ret["ret"] = "info"
                ret["msg"] = "분석중..."

            elif sub == "list":
                ret["data"] = []
                for i in LogicMain.youtube_dl_list:
                    data = LogicMain.get_data(i)
                    if data is not None:
                        ret["data"].append(data)

            elif sub == "all_stop":
                for i in LogicMain.youtube_dl_list:
                    i.stop()

            elif sub == "stop":
                index = int(req.form["index"])
                LogicMain.youtube_dl_list[index].stop()

            return jsonify(ret)
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())
            return jsonify({"ret": "danger", "msg": str(error)})

    def migration(self):
        try:
            db_version = ModelSetting.get_int("db_version")
            connect = sqlite3.connect(
                os.path.join(path_data, "db", f"{package_name}.db")
            )

            if db_version < 2:
                logger.debug("youtube-dlc uninstall")
                logger.debug(
                    subprocess.check_output(
                        [sys.executable, "-m", "pip", "uninstall", "-y", "youtube-dlc"],
                        universal_newlines=True,
                    )
                )

            connect.commit()
            connect.close()
            ModelSetting.set("db_version", LogicMain.db_default["db_version"])
            db.session.flush()
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())

    youtube_dl_list = []

    @staticmethod
    def get_youtube_dl_version():
        try:
            return MyYoutubeDL.get_version()
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())
            return "패키지 임포트 실패"

    @staticmethod
    def get_default_filename():
        return MyYoutubeDL.DEFAULT_FILENAME

    @staticmethod
    def get_preset_list():
        return [
            ["bestvideo+bestaudio/best", "최고 화질"],
            ["bestvideo[height<=1080]+bestaudio/best[height<=1080]", "1080p"],
            ["worstvideo+worstaudio/worst", "최저 화질"],
            ["bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]", "최고 화질(mp4)"],
            [
                "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]",
                "1080p(mp4)",
            ],
            ["bestvideo[filesize<50M]+bestaudio/best[filesize<50M]", "50MB 미만"],
            ["bestaudio/best", "오디오만"],
            ["_custom", "사용자 정의"],
        ]

    @staticmethod
    def get_postprocessor_list():
        return [
            ["", "후처리 안함", None],
            ["mp4", "MP4", "비디오 변환"],
            ["flv", "FLV", "비디오 변환"],
            ["webm", "WebM", "비디오 변환"],
            ["ogg", "Ogg", "비디오 변환"],
            ["mkv", "MKV", "비디오 변환"],
            ["ts", "TS", "비디오 변환"],
            ["avi", "AVI", "비디오 변환"],
            ["wmv", "WMV", "비디오 변환"],
            ["mov", "MOV", "비디오 변환"],
            ["gif", "GIF", "비디오 변환"],
            ["mp3", "MP3", "오디오 추출"],
            ["aac", "AAC", "오디오 추출"],
            ["flac", "FLAC", "오디오 추출"],
            ["m4a", "M4A", "오디오 추출"],
            ["opus", "Opus", "오디오 추출"],
            ["vorbis", "Vorbis", "오디오 추출"],
            ["wav", "WAV", "오디오 추출"],
        ]

    @staticmethod
    def get_postprocessor():
        video_convertor = []
        extract_audio = []
        for i in LogicMain.get_postprocessor_list():
            if i[2] == "비디오 변환":
                video_convertor.append(i[0])
            elif i[2] == "오디오 추출":
                extract_audio.append(i[0])
        return video_convertor, extract_audio

    @staticmethod
    def download(**kwagrs):
        try:
            logger.debug(kwagrs)
            plugin = kwagrs["plugin"]
            url = kwagrs["url"]
            filename = kwagrs["filename"]
            temp_path = kwagrs["temp_path"]
            save_path = kwagrs["save_path"]
            opts = {}
            if "format" in kwagrs and kwagrs["format"]:
                opts["format"] = kwagrs["format"]
            postprocessor = []
            if "preferedformat" in kwagrs and kwagrs["preferedformat"]:
                postprocessor.append(
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": kwagrs["preferedformat"],
                    }
                )
            if "preferredcodec" in kwagrs and kwagrs["preferredcodec"]:
                postprocessor.append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": kwagrs["preferredcodec"],
                        "preferredquality": str(kwagrs["preferredquality"]),
                    }
                )
            if postprocessor:
                opts["postprocessors"] = postprocessor
            if "playlist" in kwagrs and kwagrs["playlist"]:
                if kwagrs["playlist"] == "reverse":
                    opts["playlistreverse"] = True
                elif kwagrs["playlist"] == "random":
                    opts["playlistrandom"] = True
                else:
                    opts["playlist_items"] = kwagrs["playlist"]
            if "archive" in kwagrs and kwagrs["archive"]:
                opts["download_archive"] = kwagrs["archive"]
            if "proxy" in kwagrs and kwagrs["proxy"]:
                opts["proxy"] = kwagrs["proxy"]
            if "ffmpeg_path" in kwagrs and kwagrs["ffmpeg_path"]:
                opts["ffmpeg_location"] = kwagrs["ffmpeg_path"]
            if "cookiefile" in kwagrs and kwagrs["cookiefile"]:
                opts["cookiefile"] = kwagrs["cookiefile"]
            if "headers" in kwagrs and kwagrs["headers"]:
                opts["http_headers"] = kwagrs["headers"]
            dateafter = kwagrs.get("dateafter")
            youtube_dl = MyYoutubeDL(
                plugin, "video", url, filename, temp_path, save_path, opts, dateafter
            )
            youtube_dl.key = kwagrs.get("key")
            LogicMain.youtube_dl_list.append(youtube_dl)  # 리스트 추가
            return youtube_dl
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def thumbnail(**kwagrs):
        try:
            logger.debug(kwagrs)
            plugin = kwagrs["plugin"]
            url = kwagrs["url"]
            filename = kwagrs["filename"]
            temp_path = kwagrs["temp_path"]
            save_path = kwagrs["save_path"]
            opts = {"skip_download": True}
            if (
                "all_thumbnails" in kwagrs
                and str(kwagrs["all_thumbnails"]).lower() != "false"
            ):
                opts["write_all_thumbnails"] = True
            else:
                opts["writethumbnail"] = True
            if "playlist" in kwagrs and kwagrs["playlist"]:
                if kwagrs["playlist"] == "reverse":
                    opts["playlistreverse"] = True
                elif kwagrs["playlist"] == "random":
                    opts["playlistrandom"] = True
                else:
                    opts["playlist_items"] = kwagrs["playlist"]
            if "archive" in kwagrs and kwagrs["archive"]:
                opts["download_archive"] = kwagrs["archive"]
            if "proxy" in kwagrs and kwagrs["proxy"]:
                opts["proxy"] = kwagrs["proxy"]
            if "ffmpeg_path" in kwagrs and kwagrs["ffmpeg_path"]:
                opts["ffmpeg_location"] = kwagrs["ffmpeg_path"]
            if "cookiefile" in kwagrs and kwagrs["cookiefile"]:
                opts["cookiefile"] = kwagrs["cookiefile"]
            if "headers" in kwagrs and kwagrs["headers"]:
                opts["http_headers"] = kwagrs["headers"]
            dateafter = kwagrs.get("dateafter")
            youtube_dl = MyYoutubeDL(
                plugin,
                "thumbnail",
                url,
                filename,
                temp_path,
                save_path,
                opts,
                dateafter,
            )
            youtube_dl.key = kwagrs.get("key")
            LogicMain.youtube_dl_list.append(youtube_dl)  # 리스트 추가
            return youtube_dl
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def sub(**kwagrs):
        try:
            logger.debug(kwagrs)
            plugin = kwagrs["plugin"]
            url = kwagrs["url"]
            filename = kwagrs["filename"]
            temp_path = kwagrs["temp_path"]
            save_path = kwagrs["save_path"]
            opts = {"skip_download": True}
            sub_lang = map(
                lambda x: x.strip(), kwagrs["sub_lang"].split(",")
            )  # 문자열을 리스트로 변환
            if "all_subs" in kwagrs and str(kwagrs["all_subs"]).lower() != "false":
                opts["allsubtitles"] = True
            else:
                opts["subtitleslangs"] = sub_lang
            if "auto_sub" in kwagrs and str(kwagrs["auto_sub"]).lower() != "false":
                opts["writeautomaticsub"] = True
            else:
                opts["writesubtitles"] = True
            if "playlist" in kwagrs and kwagrs["playlist"]:
                if kwagrs["playlist"] == "reverse":
                    opts["playlistreverse"] = True
                elif kwagrs["playlist"] == "random":
                    opts["playlistrandom"] = True
                else:
                    opts["playlist_items"] = kwagrs["playlist"]
            if "archive" in kwagrs and kwagrs["archive"]:
                opts["download_archive"] = kwagrs["archive"]
            if "proxy" in kwagrs and kwagrs["proxy"]:
                opts["proxy"] = kwagrs["proxy"]
            if "ffmpeg_path" in kwagrs and kwagrs["ffmpeg_path"]:
                opts["ffmpeg_location"] = kwagrs["ffmpeg_path"]
            if "cookiefile" in kwagrs and kwagrs["cookiefile"]:
                opts["cookiefile"] = kwagrs["cookiefile"]
            if "headers" in kwagrs and kwagrs["headers"]:
                opts["http_headers"] = kwagrs["headers"]
            dateafter = kwagrs.get("dateafter")
            youtube_dl = MyYoutubeDL(
                plugin, "subtitle", url, filename, temp_path, save_path, opts, dateafter
            )
            youtube_dl.key = kwagrs.get("key")
            LogicMain.youtube_dl_list.append(youtube_dl)  # 리스트 추가
            return youtube_dl
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def get_data(youtube_dl):
        try:
            data = {}
            data["plugin"] = youtube_dl.plugin
            data["url"] = youtube_dl.url
            data["filename"] = youtube_dl.filename
            data["temp_path"] = youtube_dl.temp_path
            data["save_path"] = youtube_dl.save_path
            data["index"] = youtube_dl.index
            data["status_str"] = youtube_dl.status.name
            data["status_ko"] = str(youtube_dl.status)
            data["end_time"] = ""
            data["extractor"] = youtube_dl.type + (
                " - " + youtube_dl.info_dict["extractor"]
                if youtube_dl.info_dict["extractor"] is not None
                else ""
            )
            data["title"] = (
                youtube_dl.info_dict["title"]
                if youtube_dl.info_dict["title"] is not None
                else youtube_dl.url
            )
            data["uploader"] = (
                youtube_dl.info_dict["uploader"]
                if youtube_dl.info_dict["uploader"] is not None
                else ""
            )
            data["uploader_url"] = (
                youtube_dl.info_dict["uploader_url"]
                if youtube_dl.info_dict["uploader_url"] is not None
                else ""
            )
            data["downloaded_bytes_str"] = ""
            data["total_bytes_str"] = ""
            data["percent"] = "0"
            data["eta"] = (
                youtube_dl.progress_hooks["eta"]
                if youtube_dl.progress_hooks["eta"] is not None
                else ""
            )
            data["speed_str"] = (
                LogicMain.human_readable_size(youtube_dl.progress_hooks["speed"], "/s")
                if youtube_dl.progress_hooks["speed"] is not None
                else ""
            )
            if youtube_dl.status == Status.READY:  # 다운로드 전
                data["start_time"] = ""
                data["download_time"] = ""
            else:
                if youtube_dl.end_time is None:  # 완료 전
                    download_time = datetime.now() - youtube_dl.start_time
                else:
                    download_time = youtube_dl.end_time - youtube_dl.start_time
                    data["end_time"] = youtube_dl.end_time.strftime("%m-%d %H:%M:%S")
                if None not in (
                    youtube_dl.progress_hooks["downloaded_bytes"],
                    youtube_dl.progress_hooks["total_bytes"],
                ):  # 둘 다 값이 있으면
                    data["downloaded_bytes_str"] = LogicMain.human_readable_size(
                        youtube_dl.progress_hooks["downloaded_bytes"]
                    )
                    data["total_bytes_str"] = LogicMain.human_readable_size(
                        youtube_dl.progress_hooks["total_bytes"]
                    )
                    data[
                        "percent"
                    ] = f"{(float(youtube_dl.progress_hooks['downloaded_bytes']) / float(youtube_dl.progress_hooks['total_bytes']) * 100):.2f}"
                data["start_time"] = youtube_dl.start_time.strftime("%m-%d %H:%M:%S")
                data[
                    "download_time"
                ] = f"{int(download_time.seconds / 60):02d}:{int(download_time.seconds % 60):02d}"
            return data
        except Exception as error:
            logger.error("Exception:%s", error)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def get_info_dict(url, proxy):
        return MyYoutubeDL.get_info_dict(url, proxy)

    @staticmethod
    def human_readable_size(size, suffix=""):
        for unit in ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"):
            if size < 1024.0:
                return f"{size:3.1f} {unit}{suffix}"
            size /= 1024.0
        return f"{size:.1f} YB{suffix}"

    @staticmethod
    def socketio_emit(cmd, data):
        socketio.emit(
            cmd, LogicMain.get_data(data), namespace=f"/{package_name}", broadcast=True
        )
