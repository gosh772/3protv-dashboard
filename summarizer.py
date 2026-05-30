"""
summarizer.py
Gemini API에 YouTube 링크를 직접 전달하여 요약합니다.
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
(종목별로 줄바꿈하여 나열. 아래 규칙을 반드시 따를 것)
- 종목명: 내용 (긍정적 전망/매수 의견이면 → 앞에 🔥 이모지 추가)
- 종목명: 내용 (부정적 전망/매도 의견이면 → 앞에 ⚠️ 이모지 추가)
- 종목명: 내용 (중립이면 → 이모지 없음)
예시:
🔥 삼성전자: 추가 매수 추천, 하반기 실적 개선 기대
⚠️ 카카오: 규제 리스크로 단기 하락 우려
  LG에너지솔루션: 현 수준 유지, 뚜렷한 방향성 없음

🔮 전망 및 의견: (출연자의 핵심 전망)
🌐 거시경제: (금리, 환율, 글로벌 이슈 등)
💡 핵심 요점: (한 줄 핵심 메시지)

⭐ 오늘의 주목 투자 포인트:
(매수/매도/비중확대 등 구체적 액션이 언급된 종목만 따로 정리. 없으면 생략)
예시:
→ 삼성전자 매수, 목표가 9만원 (근거: 하반기 반도체 수요 회복)
→ 현대차 비중 축소 (근거: 환율 리스크)"""


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
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되어 있지 않습니다.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-latest",
            system_instruction=SYSTEM_PROMPT,
        )

        prompt = f"""아래 유튜브 영상을 직접 보고 내용을 형식에 맞게 요약해주세요.

[영상 제목]: {title}
[영상 링크]: {url}

특히 출연자가 특정 종목에 대해 매수·매도·비중확대·목표가 등 구체적인 투자 의견을 밝힌 경우,
반드시 🔥 또는 ⚠️ 이모지와 함께 '⭐ 오늘의 주목 투자 포인트' 항목에 따로 강조해주세요."""

        response = model.generate_content(contents=[prompt])
        return response.text

    except ImportError:
        return "❌ google-generativeai 패키지가 없습니다."
    except Exception as e:
        return f"❌ Gemini API 오류: {str(e)}"
