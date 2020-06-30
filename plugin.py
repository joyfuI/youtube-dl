# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback

# third-party
from flask import Blueprint, request, render_template, redirect, jsonify, abort
from flask_login import login_required

# sjva 공용
from framework.logger import get_logger
from framework import db, check_api, socketio

# 패키지
package_name = __name__.split('.')[0]
logger = get_logger(package_name)
from .logic import Logic
from .logic_normal import LogicNormal
from .model import ModelSetting
from .my_youtube_dl import Youtube_dl

#########################################################
# 플러그인 공용
#########################################################
blueprint = Blueprint(package_name, package_name, url_prefix='/%s' % package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

menu = {
	'main': [package_name, 'youtube-dl'],
	'sub': [
		['setting', '설정'], ['download', '다운로드'], ['list', '목록'], ['log', '로그']
	],
	'category': 'vod'
}

plugin_info = {
	'version': '1.6.2',
	'name': 'youtube-dl',
	'category_name': 'vod',
	'developer': 'joyfuI',
	'description': '유튜브, 네이버TV 등 동영상 사이트에서 동영상 다운로드',
	'home': 'https://github.com/joyfuI/youtube-dl',
	'more': ''
}

def plugin_load():
	Logic.plugin_load()
	if ModelSetting.get_bool('activate_cors'):
		import flask_cors
		flask_cors.CORS(blueprint)

def plugin_unload():
	Logic.plugin_unload()

#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
	return redirect('/%s/list' % package_name)

@blueprint.route('/<sub>')
@login_required
def first_menu(sub):
	try:
		arg = {'package_name': package_name}

		if sub == 'setting':
			arg.update(ModelSetting.to_dict())
			arg['youtube_dl_version'] = Youtube_dl.get_version()
			return render_template('%s_%s.html' % (package_name, sub), arg=arg)

		elif sub == 'download':
			arg['file_name'] = ModelSetting.get('default_filename')
			arg['preset_list'] = LogicNormal.get_preset_list()
			arg['postprocessor_list'] = LogicNormal.get_postprocessor_list()
			return render_template('%s_%s.html' % (package_name, sub), arg=arg)

		elif sub == 'list':
			return render_template('%s_%s.html' % (package_name, sub), arg=arg)

		elif sub == 'log':
			return render_template('log.html', package=package_name)
	except Exception as e:
		logger.error('Exception:%s', e)
		logger.error(traceback.format_exc())
	return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI
#########################################################
@blueprint.route('/ajax/<sub>', methods=['POST'])
@login_required
def ajax(sub):
	logger.debug('AJAX %s %s', package_name, sub)
	try:
		# 공통 요청
		if sub == 'setting_save':
			ret = ModelSetting.setting_save(request)
			return jsonify(ret)

		# UI 요청
		elif sub == 'download':
			url = request.form['url']
			filename = request.form['filename']
			temp_path = ModelSetting.get('temp_path')
			save_path = ModelSetting.get('save_path')
			format_code = request.form['format']
			postprocessor = request.form['postprocessor']
			proxy = ModelSetting.get('proxy')
			opts = {}
			if format_code:
				opts['format'] = format_code
			video_convertor, extract_audio = LogicNormal.get_postprocessor()
			if postprocessor in video_convertor:
				opts['postprocessors'] = [{
					'key': 'FFmpegVideoConvertor',
					'preferedformat': postprocessor
				}]
			elif postprocessor in extract_audio:
				opts['postprocessors'] = [{
					'key': 'FFmpegExtractAudio',
					'preferredcodec': postprocessor,
					'preferredquality': '192'
				}]
			if proxy:
				opts['proxy'] = proxy
			youtube_dl = Youtube_dl(package_name, url, filename, temp_path, save_path, opts)
			LogicNormal.youtube_dl_list.append(youtube_dl)	# 리스트 추가
			youtube_dl.start()
			socketio_emit('add', youtube_dl)
			return jsonify([])

		elif sub == 'list':
			ret = []
			for i in LogicNormal.youtube_dl_list:
				data = LogicNormal.get_data(i)
				if data is not None:
					ret.append(data)
			return jsonify(ret)

		elif sub == 'stop':
			index = int(request.form['index'])
			LogicNormal.youtube_dl_list[index].stop()
			return jsonify([])
	except Exception as e:
		logger.error('Exception:%s', e)
		logger.error(traceback.format_exc())

#########################################################
# API
#########################################################
# API 명세는 https://github.com/joyfuI/youtube-dl#api
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
@check_api
def api(sub):
	plugin = request.form.get('plugin')
	logger.debug('API %s %s: %s', package_name, sub, plugin)
	if not plugin:	# 요청한 플러그인명이 빈문자열이거나 None면
		abort(403)	# 403 에러(거부)
	try:
		# 동영상 정보를 반환하는 API
		if sub == 'info_dict':
			url = request.form.get('url')
			ret = {
				'errorCode': 0,
				'info_dict': None
			}
			if None in (url,):
				return LogicNormal.abort(ret, 1)	# 필수 요청 변수가 없음
			if not url.startswith('http'):
				return LogicNormal.abort(ret, 2)	# 잘못된 동영상 주소
			info_dict = Youtube_dl.get_info_dict(url)
			if info_dict is None:
				return LogicNormal.abort(ret, 10)	# 실패
			ret['info_dict'] = info_dict
			return jsonify(ret)

		# 다운로드 준비를 요청하는 API
		elif sub == 'download':
			key = request.form.get('key')
			url = request.form.get('url')
			filename = request.form.get('filename', ModelSetting.get('default_filename'))
			save_path = request.form.get('save_path', ModelSetting.get('save_path'))
			format_code = request.form.get('format', None)
			preferedformat = request.form.get('preferedformat', None)
			preferredcodec = request.form.get('preferredcodec', None)
			preferredquality = request.form.get('preferredquality', 192)
			archive = request.form.get('archive', None)
			start = request.form.get('start', False)
			ret = {
				'errorCode': 0,
				'index': None
			}
			if None in (key, url):
				return LogicNormal.abort(ret, 1)	# 필수 요청 변수가 없음
			if not url.startswith('http'):
				return LogicNormal.abort(ret, 2)	# 잘못된 동영상 주소
			opts = {}
			if format_code is not None:
				opts['format'] = format_code
			postprocessor = []
			if preferedformat is not None:
				postprocessor.append({
					'key': 'FFmpegVideoConvertor',
					'preferedformat': preferedformat
				})
			if preferredcodec is not None:
				if preferredcodec not in ('best', 'mp3', 'aac', 'flac', 'm4a', 'opus', 'vorbis', 'wav'):
					return LogicNormal.abort(ret, 5)	# 허용되지 않은 값이 있음
				postprocessor.append({
					'key': 'FFmpegExtractAudio',
					'preferredcodec': preferredcodec,
					'preferredquality': str(preferredquality)
				})
			if postprocessor:
				opts['postprocessors'] = postprocessor
			proxy = ModelSetting.get('proxy')
			if proxy:
				opts['proxy'] = proxy
			if archive is not None:
				opts['download_archive'] = archive
			youtube_dl = Youtube_dl(plugin, url, filename, ModelSetting.get('temp_path'), save_path, opts)
			youtube_dl.key = key
			LogicNormal.youtube_dl_list.append(youtube_dl)	# 리스트 추가
			ret['index'] = youtube_dl.index
			if start:
				youtube_dl.start()
			socketio_emit('add', youtube_dl)
			return jsonify(ret)

		# 다운로드 시작을 요청하는 API
		elif sub == 'start':
			index = request.form.get('index')
			key = request.form.get('key')
			ret = {
				'errorCode': 0,
				'status': None
			}
			if None in (index, key):
				return LogicNormal.abort(ret, 1)	# 필수 요청 변수가 없음
			index = int(index)
			if not (0 <= index < len(LogicNormal.youtube_dl_list)):
				return LogicNormal.abort(ret, 3)	# 인덱스 범위를 벗어남
			youtube_dl = LogicNormal.youtube_dl_list[index]
			if youtube_dl.key != key:
				return LogicNormal.abort(ret, 4)	# 키가 일치하지 않음
			ret['status'] = youtube_dl.status.name
			if not youtube_dl.start():
				return LogicNormal.abort(ret, 10)	# 실패
			return jsonify(ret)

		# 다운로드 중지를 요청하는 API
		elif sub == 'stop':
			index = request.form.get('index')
			key = request.form.get('key')
			ret = {
				'errorCode': 0,
				'status': None
			}
			if None in (index, key):
				return LogicNormal.abort(ret, 1)	# 필수 요청 변수가 없음
			index = int(index)
			if not (0 <= index < len(LogicNormal.youtube_dl_list)):
				return LogicNormal.abort(ret, 3)	# 인덱스 범위를 벗어남
			youtube_dl = LogicNormal.youtube_dl_list[index]
			if youtube_dl.key != key:
				return LogicNormal.abort(ret, 4)	# 키가 일치하지 않음
			ret['status'] = youtube_dl.status.name
			if not youtube_dl.stop():
				return LogicNormal.abort(ret, 10)	# 실패
			return jsonify(ret)

		# 현재 상태를 반환하는 API
		elif sub == 'status':
			index = request.form.get('index')
			key = request.form.get('key')
			ret = {
				'errorCode': 0,
				'status': None,
				'start_time': None,
				'end_time': None,
				'temp_path': None,
				'save_path': None
			}
			if None in (index, key):
				return LogicNormal.abort(ret, 1)	# 필수 요청 변수가 없음
			index = int(index)
			if not (0 <= index < len(LogicNormal.youtube_dl_list)):
				return LogicNormal.abort(ret, 3)	# 인덱스 범위를 벗어남
			youtube_dl = LogicNormal.youtube_dl_list[index]
			if youtube_dl.key != key:
				return LogicNormal.abort(ret, 4)	# 키가 일치하지 않음
			ret['status'] = youtube_dl.status.name
			ret['start_time'] = youtube_dl.start_time.strftime('%Y-%m-%dT%H:%M:%S') if youtube_dl.start_time is not None else None
			ret['end_time'] = youtube_dl.end_time.strftime('%Y-%m-%dT%H:%M:%S') if youtube_dl.end_time is not None else None
			ret['temp_path'] = youtube_dl.temp_path
			ret['save_path'] = youtube_dl.save_path
			return jsonify(ret)
	except Exception as e:
		logger.error('Exception:%s', e)
		logger.error(traceback.format_exc())
		abort(500)	# 500 에러(서버 오류)
	abort(404)	# 404 에러(페이지 없음)

#########################################################
# socketio
#########################################################
def socketio_emit(cmd, data):
	socketio.emit(cmd, LogicNormal.get_data(data), namespace='/%s' % package_name, broadcast=True)
