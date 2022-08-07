import os
import traceback
import json

from flask import Blueprint, request, jsonify, abort

from framework import app, path_data
from framework.logger import get_logger
from framework.util import Util
from framework.common.plugin import (
    get_model_setting,
    Logic,
    default_route_single_module,
)


class Plugin:
    package_name = __name__.split(".", maxsplit=1)[0]
    logger = get_logger(package_name)
    blueprint = Blueprint(
        package_name,
        package_name,
        url_prefix=f"/{package_name}",
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    # 메뉴 정의
    menu = {
        "main": [package_name, "youtube-dl"],
        "sub": [
            ["setting", "설정"],
            ["download", "다운로드"],
            ["thumbnail", "썸네일 다운로드"],
            ["sub", "자막 다운로드"],
            ["list", "목록"],
            ["log", "로그"],
        ],
        "category": "vod",
    }

    plugin_info = {
        "version": "4.0.1",
        "name": package_name,
        "category_name": "vod",
        "developer": "joyfuI",
        "description": "유튜브, 네이버TV 등 동영상 사이트에서 동영상 다운로드",
        "home": f"https://github.com/joyfuI/{package_name}",
        "more": "",
    }

    ModelSetting = get_model_setting(package_name, logger)
    logic = None
    module_list = None
    home_module = "list"  # 기본모듈

    youtube_dl_packages = ["youtube-dl", "yt-dlp"]


def initialize():
    try:
        app.config["SQLALCHEMY_BINDS"][
            Plugin.package_name
        ] = f"sqlite:///{os.path.join(path_data, 'db', f'{Plugin.package_name}.db')}"
        Util.save_from_dict_to_json(
            Plugin.plugin_info, os.path.join(os.path.dirname(__file__), "info.json")
        )

        # 로드할 모듈 정의
        from .main import LogicMain

        Plugin.module_list = [LogicMain(Plugin)]

        Plugin.logic = Logic(Plugin)
        default_route_single_module(Plugin)
    except Exception as error:
        Plugin.logger.error("Exception:%s", error)
        Plugin.logger.error(traceback.format_exc())


# API 명세는 https://github.com/joyfuI/youtube-dl#api
@Plugin.blueprint.route("/api/<sub>", methods=["GET", "POST"])
def api(sub):
    from .main import LogicMain
    from .abort import LogicAbort

    try:
        Plugin.logger.debug("API: %s, %s", sub, request.values)
        plugin = request.values.get("plugin")
        if not plugin:  # 요청한 플러그인명이 빈문자열이거나 None면
            abort(403)  # 403 에러(거부)

        # 동영상 정보를 반환하는 API
        if sub == "info_dict":
            url = request.values.get("url")
            ret = {"errorCode": 0, "info_dict": None}
            if None in (url,):
                return LogicAbort.abort(ret, 1)  # 필수 요청 변수가 없음
            if not url.startswith("http"):
                return LogicAbort.abort(ret, 2)  # 잘못된 동영상 주소
            info_dict = LogicMain.get_info_dict(url, Plugin.ModelSetting.get("proxy"))
            if info_dict is None:
                return LogicAbort.abort(ret, 10)  # 실패
            ret["info_dict"] = info_dict

        # 비디오 다운로드 준비를 요청하는 API
        elif sub == "download":
            key = request.values.get("key")
            url = request.values.get("url")
            filename = request.values.get(
                "filename", Plugin.ModelSetting.get("default_filename")
            )
            save_path = request.values.get(
                "save_path", Plugin.ModelSetting.get("save_path")
            )
            format_code = request.values.get("format", None)
            preferedformat = request.values.get("preferedformat", None)
            preferredcodec = request.values.get("preferredcodec", None)
            preferredquality = request.values.get("preferredquality", 192)
            dateafter = request.values.get("dateafter", None)
            playlist = request.values.get("playlist", None)
            archive = request.values.get("archive", None)
            start = request.values.get("start", False)
            cookiefile = request.values.get("cookiefile", None)
            headers = request.values.get("headers", "null")
            ret = {"errorCode": 0, "index": None}
            if None in (key, url):
                return LogicAbort.abort(ret, 1)  # 필수 요청 변수가 없음
            if not url.startswith("http"):
                return LogicAbort.abort(ret, 2)  # 잘못된 동영상 주소
            if preferredcodec not in (
                None,
                "best",
                "mp3",
                "aac",
                "flac",
                "m4a",
                "opus",
                "vorbis",
                "wav",
            ):
                return LogicAbort.abort(ret, 5)  # 허용되지 않은 값이 있음
            if not filename:
                filename = LogicMain.get_default_filename()
            youtube_dl = LogicMain.download(
                plugin=plugin,
                url=url,
                filename=filename,
                temp_path=Plugin.ModelSetting.get("temp_path"),
                save_path=save_path,
                format=format_code,
                preferedformat=preferedformat,
                preferredcodec=preferredcodec,
                preferredquality=preferredquality,
                dateafter=dateafter,
                playlist=playlist,
                archive=archive,
                proxy=Plugin.ModelSetting.get("proxy"),
                ffmpeg_path=Plugin.ModelSetting.get("ffmpeg_path"),
                key=key,
                cookiefile=cookiefile,
                headers=json.loads(headers),
            )
            if youtube_dl is None:
                return LogicAbort.abort(ret, 10)  # 실패
            ret["index"] = youtube_dl.index
            if start:
                youtube_dl.start()
            LogicMain.socketio_emit("add", youtube_dl)

        # 썸네일 다운로드 준비를 요청하는 API
        elif sub == "thumbnail":
            key = request.values.get("key")
            url = request.values.get("url")
            filename = request.values.get(
                "filename", Plugin.ModelSetting.get("default_filename")
            )
            save_path = request.values.get(
                "save_path", Plugin.ModelSetting.get("save_path")
            )
            all_thumbnails = request.values.get("all_thumbnails", False)
            dateafter = request.values.get("dateafter", None)
            playlist = request.values.get("playlist", None)
            archive = request.values.get("archive", None)
            start = request.values.get("start", False)
            cookiefile = request.values.get("cookiefile", None)
            headers = request.values.get("headers", "null")
            ret = {"errorCode": 0, "index": None}
            if None in (key, url):
                return LogicAbort.abort(ret, 1)  # 필수 요청 변수가 없음
            if not url.startswith("http"):
                return LogicAbort.abort(ret, 2)  # 잘못된 동영상 주소
            if not filename:
                filename = LogicMain.get_default_filename()
            youtube_dl = LogicMain.thumbnail(
                plugin=plugin,
                url=url,
                filename=filename,
                temp_path=Plugin.ModelSetting.get("temp_path"),
                save_path=save_path,
                all_thumbnails=all_thumbnails,
                dateafter=dateafter,
                playlist=playlist,
                archive=archive,
                proxy=Plugin.ModelSetting.get("proxy"),
                ffmpeg_path=Plugin.ModelSetting.get("ffmpeg_path"),
                key=key,
                cookiefile=cookiefile,
                headers=json.loads(headers),
            )
            if youtube_dl is None:
                return LogicAbort.abort(ret, 10)  # 실패
            ret["index"] = youtube_dl.index
            if start:
                youtube_dl.start()
            LogicMain.socketio_emit("add", youtube_dl)

        # 자막 다운로드 준비를 요청하는 API
        elif sub == "sub":
            key = request.values.get("key")
            url = request.values.get("url")
            filename = request.values.get(
                "filename", Plugin.ModelSetting.get("default_filename")
            )
            save_path = request.values.get(
                "save_path", Plugin.ModelSetting.get("save_path")
            )
            all_subs = request.values.get("all_subs", False)
            sub_lang = request.values.get("sub_lang", "ko")
            auto_sub = request.values.get("all_subs", False)
            dateafter = request.values.get("dateafter", None)
            playlist = request.values.get("playlist", None)
            archive = request.values.get("archive", None)
            start = request.values.get("start", False)
            cookiefile = request.values.get("cookiefile", None)
            headers = request.values.get("headers", "null")
            ret = {"errorCode": 0, "index": None}
            if None in (key, url):
                return LogicAbort.abort(ret, 1)  # 필수 요청 변수가 없음
            if not url.startswith("http"):
                return LogicAbort.abort(ret, 2)  # 잘못된 동영상 주소
            if not filename:
                filename = LogicMain.get_default_filename()
            youtube_dl = LogicMain.sub(
                plugin=plugin,
                url=url,
                filename=filename,
                temp_path=Plugin.ModelSetting.get("temp_path"),
                save_path=save_path,
                all_subs=all_subs,
                sub_lang=sub_lang,
                auto_sub=auto_sub,
                dateafter=dateafter,
                playlist=playlist,
                archive=archive,
                proxy=Plugin.ModelSetting.get("proxy"),
                ffmpeg_path=Plugin.ModelSetting.get("ffmpeg_path"),
                key=key,
                cookiefile=cookiefile,
                headers=json.loads(headers),
            )
            if youtube_dl is None:
                return LogicAbort.abort(ret, 10)  # 실패
            ret["index"] = youtube_dl.index
            if start:
                youtube_dl.start()
            LogicMain.socketio_emit("add", youtube_dl)

        # 다운로드 시작을 요청하는 API
        elif sub == "start":
            index = request.values.get("index")
            key = request.values.get("key")
            ret = {"errorCode": 0, "status": None}
            if None in (index, key):
                return LogicAbort.abort(ret, 1)  # 필수 요청 변수가 없음
            index = int(index)
            if not 0 <= index < len(LogicMain.youtube_dl_list):
                return LogicAbort.abort(ret, 3)  # 인덱스 범위를 벗어남
            youtube_dl = LogicMain.youtube_dl_list[index]
            if youtube_dl.key != key:
                return LogicAbort.abort(ret, 4)  # 키가 일치하지 않음
            ret["status"] = youtube_dl.status.name
            if not youtube_dl.start():
                return LogicAbort.abort(ret, 10)  # 실패

        # 다운로드 중지를 요청하는 API
        elif sub == "stop":
            index = request.values.get("index")
            key = request.values.get("key")
            ret = {"errorCode": 0, "status": None}
            if None in (index, key):
                return LogicAbort.abort(ret, 1)  # 필수 요청 변수가 없음
            index = int(index)
            if not 0 <= index < len(LogicMain.youtube_dl_list):
                return LogicAbort.abort(ret, 3)  # 인덱스 범위를 벗어남
            youtube_dl = LogicMain.youtube_dl_list[index]
            if youtube_dl.key != key:
                return LogicAbort.abort(ret, 4)  # 키가 일치하지 않음
            ret["status"] = youtube_dl.status.name
            if not youtube_dl.stop():
                return LogicAbort.abort(ret, 10)  # 실패

        # 현재 상태를 반환하는 API
        elif sub == "status":
            index = request.values.get("index")
            key = request.values.get("key")
            ret = {
                "errorCode": 0,
                "status": None,
                "type": None,
                "start_time": None,
                "end_time": None,
                "temp_path": None,
                "save_path": None,
            }
            if None in (index, key):
                return LogicAbort.abort(ret, 1)  # 필수 요청 변수가 없음
            index = int(index)
            if not 0 <= index < len(LogicMain.youtube_dl_list):
                return LogicAbort.abort(ret, 3)  # 인덱스 범위를 벗어남
            youtube_dl = LogicMain.youtube_dl_list[index]
            if youtube_dl.key != key:
                return LogicAbort.abort(ret, 4)  # 키가 일치하지 않음
            ret["status"] = youtube_dl.status.name
            ret["type"] = youtube_dl.type
            ret["start_time"] = (
                youtube_dl.start_time.strftime("%Y-%m-%dT%H:%M:%S")
                if youtube_dl.start_time is not None
                else None
            )
            ret["end_time"] = (
                youtube_dl.end_time.strftime("%Y-%m-%dT%H:%M:%S")
                if youtube_dl.end_time is not None
                else None
            )
            ret["temp_path"] = youtube_dl.temp_path
            ret["save_path"] = youtube_dl.save_path

        return jsonify(ret)
    except Exception as error:
        Plugin.logger.error("Exception:%s", error)
        Plugin.logger.error(traceback.format_exc())


logger = Plugin.logger
initialize()
