# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback

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
from .my_youtube_dl import Youtube_dl

#########################################################

blueprint = Blueprint(package_name, package_name, url_prefix='/%s' % package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

def plugin_load():
	Logic.plugin_load()

def plugin_unload():
	Logic.plugin_unload()

plugin_info = {
	'version': '1.1.1',
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
			arg['youtube_dl_version'] = Youtube_dl.get_version()
			return render_template('%s_setting.html' % package_name, arg=arg)

		elif sub == 'download':
			arg = { }
			arg['package_name'] = package_name
			arg['file_name'] = '%(title)s-%(id)s.%(ext)s'
			arg['preset_list'] = Logic.get_preset_list()
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
@blueprint.route('/ajax/<sub>', methods=['POST'])
@login_required
def ajax(sub):
	logger.debug('AJAX %s %s', package_name, sub)
	try:
		if sub == 'setting_save':
			ret = Logic.setting_save(request)
			return jsonify(ret)

		elif sub == 'download':
			url = request.form['url']
			filename = request.form['filename']
			temp_path = Logic.get_setting_value('temp_path')
			save_path = Logic.get_setting_value('save_path')
			format_code = request.form['format'] if request.form['format'] else None
			youtube_dl = Youtube_dl(url, filename, temp_path, save_path, format_code)
			Logic.youtube_dl_list.append(youtube_dl)	# 리스트 추가
			youtube_dl.start()
			return jsonify([])

		elif sub == 'list':
			ret = []
			for i in Logic.youtube_dl_list:
				data = Logic.get_data(i)
				if data is not None:
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
