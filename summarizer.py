"""
summarizer.py
Google Gemini API를 사용해 자막을 요약합니다. (무료)
"""

import os
from dotenv import load_dotenv
from youtube_fetcher import fetch_transcript

load_dotenv()

SYSTEM_PROMPT = """당신은 금융·경제 방송 요약 전문가입니다.
주어진 유튜브 영상 자막을 분석하여 다음 항목을 간결하게 정리하세요.
각 항목은 2~4문장을 넘지 않게 핵심만 추출하세요.

출력 형식:
📈 시황 동향: (현재 시장 분위기, 지수 움직임 등)
📌 주요 언급 종목: (구체적인 종목명과 의견)
🔮 전망 및 의견: (출연자의 핵심 전망)
🌐 거시경제: (금리, 환율, 글로벌 이슈 등)
💡 핵심 요점: (한 줄 핵심 메시지)"""

MAX_TRANSCRIPT_CHARS = 3000


def summarize_video(video: dict, llm: str = "Gemini", skip_no_transcript: bool = True) -> dict:
    result = dict(video)
    transcript = fetch_transcript(video["video_id"])

    if not transcript:
        if skip_no_transcript:
            result["summary"] = "⚠️ 자막을 불러올 수 없어 요약을 건너뛰었습니다."
            return result
        result["summary"] = "⚠️ 자막 없음"
        return result

    trimmed = transcript[:MAX_TRANSCRIPT_CHARS]
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        trimmed += "\n...(이하 생략)"

    result["summary"] = _call_gemini(video["title"], trimmed)
    return result


def _call_gemini(title: str, transcript: str) -> str:
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되어 있지 않습니다.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT,
        )

        prompt = f"[영상 제목]: {title}\n[자막]:\n{transcript}\n\n위 내용을 형식에 맞게 요약해주세요."
        response = model.generate_content(prompt)
        return response.text

    except ImportError:
        return "❌ google-generativeai 패키지가 없습니다. requirements.txt를 확인하세요."
    except Exception as e:
        return f"❌ Gemini API 오류: {e}"
