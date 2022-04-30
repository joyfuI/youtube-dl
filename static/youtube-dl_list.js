'use strict';

const all_stop_btn = document.getElementById('all_stop_btn');
const list_tbody = document.getElementById('list_tbody');

// 소켓
const socket = io.connect(`${location.origin}/${package_name}`);
socket.on('add', (data) => {
  list_tbody.innerHTML += make_item(data);
});
socket.on('status', (data) => {
  status_html(data);
});

// 목록 불러오기
fetch(`/${package_name}/ajax/list`, {
  method: 'POST',
  cache: 'no-cache',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  },
})
  .then((response) => response.json())
  .then((data) => {
    let str = '';
    for (const item of data) {
      str += make_item(item);
    }
    list_tbody.innerHTML = str;
  });

// 전체 중지
all_stop_btn.addEventListener('click', (event) => {
  event.preventDefault();
  fetch(`/${package_name}/ajax/all_stop`, {
    method: 'POST',
    cache: 'no-cache',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    },
  })
    .then((response) => response.json())
    .then(() => {
      location.reload();
    });
});

// 중지
list_tbody.addEventListener('click', (event) => {
  event.preventDefault();
  const target = event.target;
  if (!target.classList.contains('youtubeDl-stop')) {
    return;
  }
  fetch(`/${package_name}/ajax/stop`, {
    method: 'POST',
    cache: 'no-cache',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    },
    body: new URLSearchParams({
      index: target.dataset.index,
    }),
  })
    .then((response) => response.json())
    .then(() => {
      location.reload();
    });
});

function make_item(data) {
  let str = `<tr id="item_${data.index}" class="cursor-pointer" aria-expanded="true" data-toggle="collapse" data-target="#collapse_${data.index}">`;
  str += get_item(data);
  str += '</tr>';
  str += `<tr id="collapse_${data.index}" class="collapse tableRowHoverOff">`;
  str += '<td colspan="9">';
  str += `<div id="detail_${data.index}">`;
  str += get_detail(data);
  str += '</div>';
  str += '</td>';
  str += '</tr>';
  return str;
}

function get_item(data) {
  let str = `<td>${data.index + 1}</td>`;
  str += `<td>${data.plugin}</td>`;
  str += `<td>${data.start_time}</td>`;
  str += `<td>${data.extractor}</td>`;
  str += `<td>${data.title}</td>`;
  str += `<td>${data.status_ko}</td>`;
  let visi = 'hidden';
  if (parseInt(data.percent) > 0 && data.status_str !== 'STOP') {
    visi = 'visible';
  }
  str += `<td><div class="progress"><div class="progress-bar" style="visibility: ${visi}; width: ${data.percent}%">${data.percent}%</div></div></td>`;
  str += `<td>${data.download_time}</td>`;
  str += '<td class="tableRowHoverOff">';
  if (
    data.status_str === 'START' ||
    data.status_str === 'DOWNLOADING' ||
    data.status_str === 'FINISHED'
  ) {
    str += `<button class="align-middle btn btn-outline-danger btn-sm youtubeDl-stop" data-index="${data.index}">중지</button>`;
  }
  str += '</td>';
  return str;
}

function get_detail(data) {
  let str = info_html('URL', data.url, data.url);
  str += info_html('업로더', data.uploader, data.uploader_url);
  str += info_html('임시폴더', data.temp_path);
  str += info_html('저장폴더', data.save_path);
  str += info_html('종료시간', data.end_time);
  if (data.status_str === 'DOWNLOADING') {
    str += info_html('', '<b>현재 다운로드 중인 파일에 대한 정보</b>');
    str += info_html('파일명', data.filename);
    str += info_html(
      '진행률(current/total)',
      `${data.percent}% (${data.downloaded_bytes_str} / ${data.total_bytes_str})`
    );
    str += info_html('남은 시간', `${data.eta}초`);
    str += info_html('다운 속도', data.speed_str);
  }
  return str;
}

function info_html(left, right, option) {
  let str = '<div class="row">';
  const link = left === 'URL' || left === '업로더';
  str += '<div class="col-sm-2">';
  str += `<b>${left}</b>`;
  str += '</div>';
  str += '<div class="col-sm-10">';
  str += '<div class="input-group col-sm-9">';
  str += '<span class="text-left info-padding">';
  if (link) {
    str += `<a href="${option}" target="_blank">`;
  }
  str += right;
  if (link) {
    str += '</a>';
  }
  str += '</span></div></div></div>';
  return str;
}

function status_html(data) {
  document.getElementById(`item_${data.index}`).innerHTML = get_item(data);
  document.getElementById(`detail_${data.index}`).innerHTML = get_detail(data);
}
