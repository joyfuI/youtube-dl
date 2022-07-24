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

  const url = document.getElementById('url');
  const download_btn = document.getElementById('download_btn');

  // 모든 자막 다운로드
  $('#all_subs').change(() => {
    use_collapse('all_subs', true);
  });

  // 다운로드
  download_btn.addEventListener('click', (event) => {
    event.preventDefault();
    if (!url.value.startsWith('http')) {
      notify('URL을 입력하세요.', 'warning');
      return;
    }

    post_ajax('/sub', get_formdata('#download'));
  });
})();
