'use strict';

(() => {
  const post_ajax = (url, data) => {
    const loading = document.getElementById('loading');
    if (loading) {
      loading.style.display = 'block';
    }
    return fetch(`/${package_name}/ajax${url}`, {
      method: 'POST',
      cache: 'no-cache',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      },
      body: new URLSearchParams(data),
    })
      .then((response) => response.json())
      .then((ret) => {
        if (ret.msg) {
          notify(ret.msg, ret.ret);
        }
        return ret;
      })
      .catch(() => {
        notify('요청 실패', 'danger');
      })
      .finally(() => {
        if (loading) {
          loading.style.display = 'none';
        }
      });
  };

  const ffmpeg_path = document.getElementById('ffmpeg_path');
  const ffmpeg_version_btn = document.getElementById('ffmpeg_version_btn');
  const ffmpeg_path_btn = document.getElementById('ffmpeg_path_btn');
  const temp_path = document.getElementById('temp_path');
  const temp_path_btn = document.getElementById('temp_path_btn');
  const save_path = document.getElementById('save_path');
  const save_path_btn = document.getElementById('save_path_btn');
  const modal_title = document.getElementById('modal_title');
  const modal_body = document.getElementById('modal_body');

  // FFmpeg 버전확인
  ffmpeg_version_btn.addEventListener('click', (event) => {
    event.preventDefault();
    let ffmpeg = ffmpeg_path.value;
    if (ffmpeg.length === 0) {
      ffmpeg = 'ffmpeg';
    }

    post_ajax('/ffmpeg_version', {
      path: ffmpeg,
    }).then(({ data }) => {
      modal_title.innerHTML = `${ffmpeg} -version`;
      modal_body.innerHTML = data;
      $('#large_modal').modal();
    });
  });

  // FFmpeg 파일 선택
  ffmpeg_path_btn.addEventListener('click', (event) => {
    event.preventDefault();
    m_select_local_file_modal('실행 파일 선택', '/', false, (result) => {
      ffmpeg_path.value = result;
    });
  });

  // 임시 폴더 경로 선택
  temp_path_btn.addEventListener('click', (event) => {
    event.preventDefault();
    m_select_local_file_modal(
      '저장 경로 선택',
      temp_path.value,
      true,
      (result) => {
        temp_path.value = result;
      }
    );
  });

  // 저장 폴더 경로 선택
  save_path_btn.addEventListener('click', (event) => {
    event.preventDefault();
    m_select_local_file_modal(
      '저장 경로 선택',
      save_path.value,
      true,
      (result) => {
        save_path.value = result;
      }
    );
  });
})();
