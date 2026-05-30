"""
summarizer.py
Anthropic Claude 또는 OpenAI GPT를 사용해 자막을 요약합니다.
토큰 절감을 위해 자막을 최대 3,000자로 잘라 핵심 정보만 추출합니다.
"""

import os
from dotenv import load_dotenv
from youtube_fetcher import fetch_transcript

load_dotenv()

# ── 프롬프트 ────────────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 금융·경제 방송 요약 전문가입니다.
주어진 유튜브 영상 자막을 분석하여 다음 항목을 **간결하게** 정리하세요.
각 항목은 2~4문장을 넘지 않게, 핵심만 추출하세요.

출력 형식 (마크다운):
**📈 시황 동향:** (현재 시장 분위기, 지수 움직임 등)
**📌 주요 언급 종목:** (구체적인 종목명과 의견)
**🔮 전망 및 의견:** (출연자의 핵심 전망)
**🌐 거시경제:** (금리, 환율, 글로벌 이슈 등)
**💡 핵심 요점:** (한 줄 핵심 메시지)
"""

USER_TEMPLATE = """[영상 제목]: {title}
[자막 (일부)]:
{transcript}

위 내용을 형식에 맞게 요약해주세요."""

# 자막 최대 길이 (토큰 절감)
MAX_TRANSCRIPT_CHARS = 3000


def summarize_video(video: dict, llm: str, skip_no_transcript: bool = True) -> dict:
    """
    단일 영상을 요약합니다.
    video dict에 'summary'와 'cast'(갱신)를 추가하여 반환합니다.
    """
    result = dict(video)

    # 자막 가져오기
    transcript = fetch_transcript(video["video_id"])

    if not transcript:
        if skip_no_transcript:
            result["summary"] = "⚠️ 자막을 불러올 수 없어 요약을 건너뛰었습니다."
            return result
        else:
            result["summary"] = "⚠️ 자막 없음"
            return result

    # 자막 길이 제한 (비용 절감)
    trimmed = transcript[:MAX_TRANSCRIPT_CHARS]
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        trimmed += "\n...(이하 생략)"

    user_msg = USER_TEMPLATE.format(title=video["title"], transcript=trimmed)

    # LLM 호출
    if "Anthropic" in llm:
        summary = _call_anthropic(user_msg)
    else:
        summary = _call_openai(user_msg)

    result["summary"] = summary
    return result


def _call_anthropic(user_msg: str) -> str:
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY가 .env에 없습니다.")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text

    except ImportError:
        return "❌ anthropic 패키지가 설치되어 있지 않습니다. `pip install anthropic`"
    except Exception as e:
        return f"❌ Anthropic API 오류: {e}"


def _call_openai(user_msg: str) -> str:
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 .env에 없습니다.")

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 비용 효율적인 모델
            max_tokens=600,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        return response.choices[0].message.content

    except ImportError:
        return "❌ openai 패키지가 설치되어 있지 않습니다. `pip install openai`"
    except Exception as e:
        return f"❌ OpenAI API 오류: {e}"
