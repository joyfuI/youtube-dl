# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import subprocess
from datetime import datetime

# third-party
from flask import Blueprint, request, render_template, redirect, jsonify
from flask_login import login_required

# sjva 공용
from framework.logger import get_logger
from framework import db
from framework.util import Util

# 로그
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

# 패키지
from .logic import Logic
from .model import ModelSetting
from .youtube_dl import Youtube_dl, Status

#########################################################

blueprint = Blueprint(package_name, package_name, url_prefix='/%s' % package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

def plugin_load():
	Logic.plugin_load()

def plugin_unload():
	Logic.plugin_unload()

plugin_info = {
	'version': '0.1.1',
	'name': 'youtube-dl',
	'category_name': 'vod',
	'icon': '',
	'developer': 'joyfuI',
	'description': '유튜브, 네이버TV 등 동영상 사이트에서 동영상 다운로드',
	'home': 'https://github.com/joyfuI/youtube-dl',
	'more': ''
}

# 메뉴 구성
menu = {
	'main': [package_name, 'youtube-dl'],
	'sub': [
		['setting', '설정'], ['download', '다운로드'], ['list', '목록'], ['log', '로그']
	],
	'category': 'vod'
}

#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
	return redirect('/%s/list' % package_name)

@blueprint.route('/<sub>')
@login_required
def detail(sub):
	try:
		if sub == 'setting':
			setting_list = db.session.query(ModelSetting).all()
			arg = Util.db_list_to_dict(setting_list)
			arg['package_name'] = package_name
			arg['youtube_dl_path'] = Logic.youtube_dl_path
			return render_template('%s_setting.html' % package_name, arg=arg)

		elif sub == 'download':
			arg = { }
			arg['package_name'] = package_name
			arg['file_name'] = '%(title)s-%(id)s.%(ext)s'
			return render_template('%s_download.html' % package_name, arg=arg)

		elif sub == 'list':
			arg = { }
			arg['package_name'] = package_name
			return render_template('%s_list.html' % package_name, arg=arg)

		elif sub == 'log':
			return render_template('log.html', package=package_name)
	except Exception as e:
		logger.error('Exception:%s', e)
		logger.error(traceback.format_exc())
	return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
def ajax(sub):
	logger.debug('AJAX %s %s', package_name, sub)
	try:
		if sub == 'setting_save':
			ret = Logic.setting_save(request)
			return jsonify(ret)

		elif sub == 'youtube_dl_version':
			ret = subprocess.check_output([Logic.youtube_dl_path, '--version'])
			return jsonify(ret)

		elif sub == 'youtube_dl_update':
			Logic.youtube_dl_update()
			return jsonify([])

		elif sub == 'download':
			url = request.form['url']
			filename = request.form['filename']
			temp_path = Logic.get_setting_value('temp_path')
			save_path = Logic.get_setting_value('save_path')
			youtube_dl = Youtube_dl(url, filename, temp_path, save_path)
			Logic.youtube_dl_list.append(youtube_dl)	# 리스트 추가
			youtube_dl.start()
			return jsonify([])

		elif sub == 'list':
			ret = []
			for i in Logic.youtube_dl_list:
				data = { }
				data['url'] = i.url
				data['filename'] = i.filename
				data['temp_path'] = i.temp_path
				data['save_path'] = i.save_path
				data['index'] = i.index
				data['status_str'] = i.status.name
				data['status_ko'] = str(i.status)
				data['format'] = i.format
				data['end_time'] = ''
				if i.status == Status.READY:	# 다운로드 전
					data['duration_str'] = ''
					data['download_time'] = ''
					data['start_time'] = ''
				else:
					data['duration_str'] = '%02d:%02d:%02d' % (i.duration / 60 / 60, i.duration / 60 % 60, i.duration % 60)
					if i.end_time == None:	# 완료 전
						download_time = datetime.now() - i.start_time
					else:
						download_time = i.end_time - i.start_time
						data['end_time'] = i.end_time.strftime('%m-%d %H:%M:%S')
					data['download_time'] = '%02d:%02d' % (download_time.seconds / 60, download_time.seconds % 60)
					data['start_time'] = i.start_time.strftime('%m-%d %H:%M:%S')
				ret.append(data)
			return jsonify(ret)

		elif sub == 'stop':
			index = int(request.form['index'])
			Logic.youtube_dl_list[index].stop()
			return jsonify([])
	except Exception as e:
		logger.error('Exception:%s', e)
		logger.error(traceback.format_exc())

#########################################################
# API
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
def api(sub):
	logger.debug('api %s %s', package_name, sub)
