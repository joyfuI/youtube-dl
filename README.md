# youtube-dl_sjva
[SJVA](https://sjva.me/) 용 [youtube-dl](https://ytdl-org.github.io/youtube-dl/) 플러그인입니다.  
SJVA에서 유튜브, 네이버TV 등 동영상 사이트 영상을 다운로드할 수 있습니다.

## 설치
SJVA에서 "시스템 → 플러그인 → 플러그인 수동 설치" 칸에 저장소 주소를 넣고 설치 버튼을 누르면 됩니다.  
`https://github.com/joyfuI/youtube-dl`

## 잡담
시놀로지 docker 환경에서 테스트했습니다.  

다른 분들이 만든 플러그인을 참고하며 주먹구구식으로 만들었습니다;;  

드디어! API를 추가했습니다. 다른 플러그인에서 동영상 정보나 다운로드를 요청할 수 있습니다.  
다른 플러그인이 멋대로 다운로드를 중지할 수 없도록 다운로드를 요청할 때 임의의 키를 넘겨 받습니다. 이 중지 요청 시 키가 일치해야 요청이 실행됩니다.  
이걸로 뭔갈 만드실 분이 계실지...

## API
### 공통사항
모든 요청은 `POST`로만 받습니다. 그리고 응답은 `JSON` 형식입니다.  
모든 요청엔 *플러그인 이름* 정보가 있어야 합니다. `plugin` 키에 담아서 보내면 됩니다. 만약 *플러그인 이름* 정보가 없으면 **403 에러**를 반환합니다.  
요청을 처리하는 과정에서 예외가 발생하면 **500 에러**를 반환합니다. 이건 저한테 로그와 함께 알려주시면 됩니다.  
모든 응답에는 `errorCode` 키가 있습니다. 코드의 의미는 아래 문단 참고
#### 에러 코드 (errorCode)
* `0` - 성공. 문제없음
* `1` - 필수 요청 변수가 없음
* `2` - 잘못된 동영상 주소
* `3` - 인덱스 범위를 벗어남
* `4` - 키가 일치하지 않음
* `10` - 실패. 요청은 성공하였으나 실행 결과가 실패
#### Status 타입
상태를 나타냄
* "`READY`" - 준비
* "`START`" - 분석중
* "`DOWNLOADING`" - 다운로드중
* "`ERROR`" - 실패
* "`FINISHED`" - 변환중
* "`STOP`" - 중지
* "`COMPLETED`" - 완료

### /youtube-dl/api/info_dict
동영상 정보를 반환하는 API
#### Request
키 | 설명 | 필수 | 타입
--- | --- | --- | ---
`plugin` | 플러그인 이름 | O | String
`url` | 동영상 주소 | O | String
#### Response
키 | 설명 | 타입
--- | --- | ---
`errorCode` | 에러 코드 | Integer
`info_dict` | 동영상 정보 | Object

동영상 정보(`info_dict` 키)에는 youtube-dl에서 생성한 info_dict 정보가 그대로 들어있습니다. 따라서 이 부분은 직접 주소를 넣어가며 반환되는 정보를 확인해보는게 좋습니다.  
간단한 예로 `thumbnail` 키엔 썸네일 주소, `uploader` 키엔 업로더 이름, `title` 키엔 동영상 제목, `duration` 키엔 동영상 길이 등이 들어 있습니다.  
그리고 만약 주소가 플레이리스트라면 `_type` 키에 "`playlist`"라는 값이 들어 있습니다. 이때는 `entries` 키에 리스트가 들어있어 동영상들의 제목과 ID를 확인할 수 있습니다.

### /youtube-dl/api/download
다운로드 준비를 요청하는 API
#### Request
키 | 설명 | 필수 | 타입
--- | --- | --- | ---
`plugin` | 플러그인 이름 | O | String
`key` | 임의의 키. 이후 다운로드를 제어할 때 이 키가 필요함 | O | String
`url` | 동영상 주소 | O | String
`filename` | 파일명. 템플릿 규칙은 https://github.com/ytdl-org/youtube-dl/blob/master/README.md#output-template 참고 | O | String
`temp_path` | 임시 폴더 경로 | O | String
`save_path` | 저장 폴더 경로 | O | String
`format_code` | 동영상 포맷. 포맷 지정은 https://github.com/ytdl-org/youtube-dl/blob/master/README.md#format-selection 참고. 지정하지 않으면 최고 화질로 다운로드됨 | X | String
`start` | 다운로드 준비 후 바로 다운로드를 시작할지 여부. 기본값: false | X | Boolean
#### Response
키 | 설명 | 타입
--- | --- | ---
`errorCode` | 에러 코드 | Integer
`index` | 동영상 인덱스. 이후 다운로드를 제어할 때 이 값이 필요함 | Integer

### /youtube-dl/api/start
다운로드 시작을 요청하는 API
#### Request
키 | 설명 | 필수 | 타입
--- | --- | --- | ---
`plugin` | 플러그인 이름 | O | String
`index` | 제어할 동영상의 인덱스 | O | Integer
`key` | 제어할 동영상에게 넘겨준 키. 이 값이 일치해야 요청이 실행됨 | O | String
#### Response
키 | 설명 | 타입
--- | --- | ---
`errorCode` | 에러 코드 | Integer
`status` | 요청을 받았을 당시의 상태 | Status

### /youtube-dl/api/stop
다운로드 중지를 요청하는 API
#### Request
키 | 설명 | 필수 | 타입
--- | --- | --- | ---
`plugin` | 플러그인 이름 | O | String
`index` | 제어할 동영상의 인덱스 | O | Integer
`key` | 제어할 동영상에게 넘겨준 키. 이 값이 일치해야 요청이 실행됨 | O | String
#### Response
키 | 설명 | 타입
--- | --- | ---
`errorCode` | 에러 코드 | Integer
`status` | 요청을 받았을 당시의 상태 | Status

### /youtube-dl/api/status
현재 상태를 반환하는 API
#### Request
키 | 설명 | 필수 | 타입
--- | --- | --- | ---
`plugin` | 플러그인 이름 | O | String
`index` | 제어할 동영상의 인덱스 | O | Integer
`key` | 제어할 동영상에게 넘겨준 키. 이 값이 일치해야 요청이 실행됨 | O | String
#### Response
키 | 설명 | 타입
--- | --- | ---
`errorCode` | 에러 코드 | Integer
`status` | 요청을 받았을 당시의 상태 | Status
`start_time` | 다운로드 시작 시간 | String
`end_time` | 다운로드 종료 시간 | String
`temp_path` | 임시 폴더 경로 | String
`save_path` | 저장 폴더 경로 | String

`start_time` 키와 `end_time` 키에 들어있는 시간은 "년 월 일 시 분 초" 형식으로 공백으로 분리된 숫자들이 모여있는 문자열입니다.  
물론 해당 정보가 없으면 null입니다.

## Changelog
v1.2.3
* 저장 경로가 존재하지 않으면 생성하도록 개선

v1.2.2
* youtube-dl 패키지 업그레이드도 로그 찍히도록 수정

v1.2.1

v1.2.0
* API 추가  
  이제 다른 플러그인에서 동영상 정보 가져오기, 다운로드 요청이 가능합니다.  
  자세한 명세는 API 문단을 참고하세요.

v1.1.1
* 플레이리스트 다운로드 중 국가차단 등의 이유로 다운로드 실패한 동영상이 있으면 건너뛰도록 개선

v1.1.0
* 화질 선택 기능 추가
* 잘못된 예외처리 수정

v1.0.2

v1.0.1
* 로그 좀 더 상세히 찍도록 수정

v1.0.0
* 바이너리 실행 방식에서 파이썬 임베딩 방식으로 변경
* SJVA 시작 시 자동으로 youtube-dl 업데이트
* 목록에서 진행률 표시 추가

v0.1.1
* 다운로드 실패 시 임시파일 삭제가 안 되는 문제 수정

v0.1.0
* 최초 공개
