# 📺 삼프로TV 온디맨드 대시보드

YouTube 채널의 최근 영상을 수집·요약해주는 온디맨드 대시보드입니다.
버튼 한 번으로 지정 기간의 영상을 수집하고, LLM으로 자동 요약합니다.

---

## 📁 프로젝트 구조

```
dashboard/
├── app.py               # Streamlit 메인 앱
├── youtube_fetcher.py   # YouTube API 수집 모듈
├── summarizer.py        # LLM 요약 모듈
├── cache_manager.py     # SQLite 캐시 관리
├── .env.example         # 환경변수 템플릿
├── .env                 # 실제 API 키 (직접 생성, Git에 올리지 마세요!)
├── requirements.txt     # 패키지 목록
└── cache/
    └── summaries.db     # SQLite 캐시 DB (자동 생성)
```

---

## 🚀 빠른 시작 (5분 설치)

### 1단계 — 패키지 설치

```bash
pip install -r requirements.txt
```

### 2단계 — API 키 설정

```bash
# .env.example을 복사해서 .env 파일 생성
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력합니다:

```
YOUTUBE_API_KEY=AIzaSy...          # 필수
ANTHROPIC_API_KEY=sk-ant-...       # Claude 사용 시
OPENAI_API_KEY=sk-proj-...         # GPT 사용 시
```

### 3단계 — 실행

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`로 접속됩니다.

---

## 🔑 API 키 발급 방법

### YouTube Data API v3

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성 (또는 기존 프로젝트 선택)
3. **API 및 서비스 > 라이브러리** → "YouTube Data API v3" 검색 후 사용 설정
4. **API 및 서비스 > 사용자 인증 정보 > 사용자 인증 정보 만들기 > API 키** 생성
5. 생성된 키를 `.env`의 `YOUTUBE_API_KEY`에 입력

> ⚠️ 무료 할당량: 하루 10,000 units. 영상 1개 수집에 약 100 units 소모.

### Anthropic Claude

1. [console.anthropic.com](https://console.anthropic.com) 가입
2. **API Keys** 메뉴에서 키 생성
3. `.env`의 `ANTHROPIC_API_KEY`에 입력

### OpenAI

1. [platform.openai.com](https://platform.openai.com/api-keys) 접속
2. **Create new secret key** 클릭
3. `.env`의 `OPENAI_API_KEY`에 입력

---

## 💰 비용 절감 전략

| 항목 | 절감 방법 |
|------|----------|
| YouTube API | 페이지네이션으로 최소 호출, 캐시로 중복 차단 |
| LLM 자막 | 최대 3,000자로 트리밍하여 토큰 절감 |
| LLM 모델 | Anthropic: claude-sonnet-4 / OpenAI: gpt-4o-mini 사용 |
| 캐시 DB | SQLite로 처리된 영상 저장, 재실행 시 API 호출 없음 |

---

## ⚠️ 보안 주의사항

- `.env` 파일을 **절대 Git에 커밋하지 마세요**
- `.gitignore`에 반드시 `.env`와 `cache/` 추가:

```
.env
cache/
__pycache__/
```
