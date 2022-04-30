'use strict';

const url = document.getElementById('url');
const preset = document.getElementById('preset');
const format = document.getElementById('format');
const postprocessor = document.getElementById('postprocessor');
const download_btn = document.getElementById('download_btn');

// 프리셋 변경
preset.addEventListener('change', () => {
  if (preset.value !== '_custom') {
    format.value = preset.value;
  }
});
format.addEventListener('input', () => {
  preset.value = '_custom';
});

// 후처리 변경
postprocessor.addEventListener('change', () => {
  const select = postprocessor.selectedOptions[0];
  if (select.parentElement.label === '오디오 추출') {
    preset.value = 'bestaudio/best';
    format.value = preset.value;
  }
});

// 다운로드
download_btn.addEventListener('click', (event) => {
  event.preventDefault();
  if (!url.value.startsWith('http')) {
    notify('URL을 입력하세요.', 'warning');
    return;
  }

  fetch(`/${package_name}/ajax/download`, {
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
