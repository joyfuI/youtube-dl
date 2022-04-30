'use strict';

const url = document.getElementById('url');
const download_btn = document.getElementById('download_btn');

// 다운로드
download_btn.addEventListener('click', (event) => {
  event.preventDefault();
  if (!url.value.startsWith('http')) {
    notify('URL을 입력하세요.', 'warning');
    return;
  }

  fetch(`/${package_name}/ajax/thumbnail`, {
    method: 'POST',
    cache: 'no-cache',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    },
    body: get_formdata('#download'),
  })
    .then((response) => response.json())
    .then(() => {
      notify('분석중..', 'info');
    })
    .catch(() => {
      notify('다운로드 요청 실패', 'danger');
    });
});
