"""
summarizer.py
Gemini 2.5 Flash-Lite로 YouTube 영상을 상세 요약합니다.
Rate limit 방지를 위해 요청 사이에 자동 대기합니다.
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """당신은 금융·경제 방송 요약 전문가입니다.
주어진 유튜브 영상을 직접 시청하고 아래 형식으로 상세하게 요약하세요.

[요약 품질 기준]
- 단순한 한두 줄 요약이 아닌, 영상의 핵심 논지와 주요 주장을 구체적으로 서술하세요
- 출연자가 실제로 언급한 수치, 정책명, 종목명, 전망 근거를 포함하세요
- 각 항목당 3~5문장 분량으로 충분히 설명하세요
- 분/초 타임스탬프는 포함하지 마세요

[출력 형식]

🎙️ 영상 개요:
(어떤 출연자가 어떤 주제로 출연했는지 2~3문장으로 설명)

📈 시황 동향:
(언급된 시장 분위기, 지수, 섹터 흐름 등. 없으면 '해당 없음')

📌 주요 언급 종목 & 전망:
(종목별 줄바꿈. 긍정=🔥, 부정=⚠️, 중립=공백)
🔥 종목명: 구체적 이유와 전망
⚠️ 종목명: 구체적 리스크
(주식 관련 내용이 없으면 '해당 없음')

🔑 핵심 내용 요약:
(영상에서 다룬 주요 토픽을 bullet point로 3~5개 정리. 각 항목은 2~3문장으로 구체적으로)
• 토픽1: 설명
• 토픽2: 설명
• 토픽3: 설명

🔮 출연자 전망 및 의견:
(출연자가 강조한 핵심 주장과 근거를 구체적으로)

🌐 거시경제:
(금리, 환율, 글로벌 이슈 등. 없으면 '해당 없음')

💡 핵심 요점:
(영상 전체를 관통하는 핵심 메시지 1~2문장)

⭐ 오늘의 주목 투자 포인트:
(매수/매도/비중확대 등 구체적 액션이 언급된 경우만. 없으면 이 항목 전체 생략)
→ 종목명 매수/매도, 목표가 OOO원 (근거: ...)"""


def summarize_video(video: dict, llm: str = "Gemini", skip_no_transcript: bool = False) -> dict:
    result = dict(video)
    url = video.get("url", "")
    title = video.get("title", "")

    if not url:
        result["summary"] = "⚠️ URL 없음"
        return result

    result["summary"] = _call_gemini_with_url(url, title)
    return result


def _call_gemini_with_url(url: str, title: str) -> str:
    try:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되어 있지 않습니다.")

        client = genai.Client(api_key=api_key)

        prompt = f"""{SYSTEM_PROMPT}

아래 유튜브 영상을 직접 시청하고 형식에 맞게 상세히 요약해주세요.

[영상 제목]: {title}
[영상 링크]: {url}"""

        # 분당 10개 제한 → 영상 1개당 7초 대기 (안전 마진 포함)
        time.sleep(7)

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return response.text

    except ImportError:
        return "❌ google-genai 패키지가 없습니다."
    except Exception as e:
        error_msg = str(e)
        # 429 오류 시 30초 대기 후 1회 재시도
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            time.sleep(30)
            try:
                from google import genai
                api_key = os.getenv("GEMINI_API_KEY")
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=f"{SYSTEM_PROMPT}\n\n[영상 제목]: {title}\n[영상 링크]: {url}",
                )
                return response.text
            except Exception as e2:
                return f"❌ Gemini API 오류 (재시도 실패): {str(e2)}"
        return f"❌ Gemini API 오류: {error_msg}"
