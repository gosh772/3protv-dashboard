"""
summarizer.py - 할루시네이션 최소화, 확실한 내용만 요약
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """당신은 금융·경제 방송 요약 전문가입니다.
주어진 유튜브 영상을 직접 시청하고 아래 형식으로 요약하세요.

[매우 중요한 규칙]
- 영상에서 실제로 언급된 내용만 작성하세요. 추측하거나 만들어내지 마세요.
- 목표가, 수치, 종목명은 출연자가 직접 말한 경우에만 작성하세요.
- 확실하지 않은 내용은 절대 포함하지 말고, 해당 항목을 '언급 없음'으로 표시하세요.
- 분/초 타임스탬프는 포함하지 마세요.
- 출연자가 실제로 언급한 종목명, 정책명, 수치만 사용하세요.

[출력 형식]

🎙️ 영상 개요:
(어떤 출연자가 어떤 주제로 출연했는지 2~3문장)

📈 시황 동향:
(영상에서 실제 언급된 시장 흐름. 없으면 '해당 없음')

📌 주요 언급 종목 & 전망:
(출연자가 실제로 언급한 종목만. 긍정=🔥, 부정=⚠️, 중립=공백. 목표가는 직접 언급한 경우에만)
(없으면 '해당 없음')

🔑 핵심 내용:
(영상에서 다룬 주요 토픽 3~5개를 bullet로. 실제 언급 내용만)
• 토픽: 설명
• 토픽: 설명

🔮 출연자 전망:
(실제 발언 기반. 추측 금지)

🌐 거시경제:
(실제 언급된 금리/환율/글로벌 이슈. 없으면 '해당 없음')

💡 핵심 요점:
(영상 핵심 메시지 1~2문장)

⭐ 오늘의 주목 투자 포인트:
(출연자가 직접 매수/매도/목표가를 언급한 경우에만. 없으면 이 항목 완전 생략)"""


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

[영상 제목]: {title}
[영상 링크]: {url}

반드시 영상에서 실제로 언급된 내용만 요약하세요. 목표가나 수치는 출연자가 직접 말한 경우에만 포함하세요."""

        time.sleep(7)  # 분당 10개 제한 방지

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            time.sleep(30)
            try:
                from google import genai
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=f"{SYSTEM_PROMPT}\n\n[영상 제목]: {title}\n[영상 링크]: {url}",
                )
                return response.text
            except Exception as e2:
                return f"❌ Gemini API 오류 (재시도 실패): {str(e2)}"
        return f"❌ Gemini API 오류: {error_msg}"
