"use strict";

const ffmpeg_version_btn = document.getElementById('ffmpeg_version_btn');
const ffmpeg_path = document.getElementById('ffmpeg_path');
const modal_title = document.getElementById('modal_title');
const modal_body = document.getElementById('modal_body');

// FFmpeg 버전확인
ffmpeg_version_btn.addEventListener('click', (event) => {
    event.preventDefault();
    let ffmpeg = ffmpeg_path.value;
    if (ffmpeg.length === 0) {
        ffmpeg = 'ffmpeg';
    }

    fetch(`/${package_name}/ajax/ffmpeg_version`, {
        method: 'POST',
        cache: 'no-cache',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        },
        body: new URLSearchParams({
            path: ffmpeg
        })
    }).then(response => response.json()).then((data) => {
        modal_title.innerHTML = `${ffmpeg} -version`;
        modal_body.innerHTML = data;
        $('#large_modal').modal();
    }).catch(() => {
        notify('버전확인 실패', 'danger');
    });
});
