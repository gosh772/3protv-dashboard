"""
youtube_fetcher.py
YouTube Data API v3를 사용해 삼프로TV 채널의 영상 목록과 메타데이터를 가져옵니다.
"""

import os
import datetime
import re
from typing import Optional

from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
# 삼프로TV 채널 ID (핸들 @3protv → 실제 channel ID)
CHANNEL_ID = "UCsJ6RuBiWBv0RAQWD2PDQMQ"


def _build_service():
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def fetch_videos_in_range(
    start_date: datetime.date,
    end_date: datetime.date,
    max_results: int = 20,
    channel_id: str = CHANNEL_ID,
) -> list[dict]:
    """
    지정 기간 동안 채널에 업로드된 영상 목록을 반환합니다.
    각 항목에는 video_id, title, published_at, url, description 포함.
    """
    service = _build_service()

    # RFC 3339 형식으로 변환
    published_after = datetime.datetime(
        start_date.year, start_date.month, start_date.day, 0, 0, 0
    ).isoformat() + "Z"
    published_before = datetime.datetime(
        end_date.year, end_date.month, end_date.day, 23, 59, 59
    ).isoformat() + "Z"

    videos = []
    next_page_token = None

    while len(videos) < max_results:
        fetch_count = min(50, max_results - len(videos))

        request = service.search().list(
            part="id,snippet",
            channelId=channel_id,
            publishedAfter=published_after,
            publishedBefore=published_before,
            maxResults=fetch_count,
            order="date",
            type="video",
            pageToken=next_page_token,
        )
        response = request.execute()

        items = response.get("items", [])
        for item in items:
            vid_id = item["id"].get("videoId")
            if not vid_id:
                continue
            snippet = item["snippet"]
            videos.append({
                "video_id": vid_id,
                "title": snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", ""),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "cast": _extract_cast(snippet.get("title", ""), snippet.get("description", "")),
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token or len(items) == 0:
            break

    return videos[:max_results]


def fetch_transcript(video_id: str, languages: list[str] = ["ko", "en"]) -> Optional[str]:
    """
    영상의 자막을 가져옵니다. 한국어 → 영어 순으로 시도하며,
    자동 생성 자막도 포함합니다. 없으면 None을 반환합니다.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # 수동 자막 우선 시도
        for lang in languages:
            try:
                t = transcript_list.find_manually_created_transcript([lang])
                return _join_transcript(t.fetch())
            except Exception:
                pass

        # 자동 생성 자막 시도
        for lang in languages:
            try:
                t = transcript_list.find_generated_transcript([lang])
                return _join_transcript(t.fetch())
            except Exception:
                pass

        # 첫 번째 사용 가능한 자막 사용
        for t in transcript_list:
            return _join_transcript(t.fetch())

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception:
        return None

    return None


def _join_transcript(fetched: list) -> str:
    """자막 세그먼트 리스트를 하나의 텍스트로 합칩니다."""
    parts = []
    for seg in fetched:
        # FetchedTranscriptSnippet 객체 또는 dict 모두 처리
        if hasattr(seg, "text"):
            parts.append(seg.text.strip())
        elif isinstance(seg, dict):
            parts.append(seg.get("text", "").strip())
    return " ".join(parts)


def _extract_cast(title: str, description: str) -> str:
    """
    제목 또는 설명에서 출연자를 추출합니다.
    삼프로TV는 주로 '[OOO의 OOO]' 또는 '| OOO' 패턴을 사용합니다.
    """
    # 패턴 1: 괄호 안 이름 (예: [홍길동의 시황])
    bracket_match = re.findall(r"[\[【]([가-힣a-zA-Z\s·&]+?)(?:의|,|】|\])", title)
    if bracket_match:
        return ", ".join(m.strip() for m in bracket_match[:3])

    # 패턴 2: 파이프 뒤 이름 (예: | 이름1, 이름2)
    pipe_match = re.findall(r"\|\s*([가-힣a-zA-Z\s·,]+?)(?:\||$)", title)
    if pipe_match:
        return pipe_match[0].strip()

    # 패턴 3: 설명 첫 줄에서 이름 패턴
    first_line = description.split("\n")[0] if description else ""
    name_match = re.findall(r"([가-힣]{2,4})\s*(?:대표|위원|교수|기자|선생|이사|부장)", first_line)
    if name_match:
        return ", ".join(name_match[:3])

    return "정보 없음"
