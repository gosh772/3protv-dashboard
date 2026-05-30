"""
summarizer.py
최신 google-genai SDK로 Gemini 2.5 Flash-Lite를 사용해 요약합니다.
"""

import os
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """당신은 금융·경제 방송 요약 전문가입니다.
주어진 유튜브 영상을 직접 분석하여 아래 형식으로 요약하세요.
각 항목은 2~3문장으로 핵심만 간결하게 작성하세요.
정보가 없는 항목은 '언급 없음'으로 표시하세요.

출력 형식:
📈 시황 동향: (현재 시장 분위기, 지수 움직임 등)

📌 주요 언급 종목 & 전망:
(종목별로 줄바꿈하여 나열)
🔥 종목명: 내용 (긍정적 전망/매수 의견)
⚠️ 종목명: 내용 (부정적 전망/매도 의견)
   종목명: 내용 (중립)

🔮 전망 및 의견: (출연자의 핵심 전망)
🌐 거시경제: (금리, 환율, 글로벌 이슈 등)
💡 핵심 요점: (한 줄 핵심 메시지)

⭐ 오늘의 주목 투자 포인트:
(매수/매도/비중확대 등 구체적 액션이 언급된 종목만. 없으면 이 항목 생략)
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

아래 유튜브 영상을 직접 보고 형식에 맞게 요약해주세요.

[영상 제목]: {title}
[영상 링크]: {url}

특히 출연자가 특정 종목에 대해 매수·매도·비중확대·목표가 등 구체적인 투자 의견을 밝힌 경우,
🔥 또는 ⚠️ 이모지와 함께 '⭐ 오늘의 주목 투자 포인트' 항목에 강조해주세요."""

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return response.text

    except ImportError:
        return "❌ google-genai 패키지가 없습니다. requirements.txt를 확인하세요."
    except Exception as e:
        return f"❌ Gemini API 오류: {str(e)}"
