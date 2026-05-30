"""
youtube_fetcher.py
YouTube Data API v3를 사용해 삼프로TV 채널의 영상 목록을 가져옵니다.
"""

import os
import datetime
import re
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UChlv4GSd7OQl3js-jkLOnFA"  # 삼프로TV 3PROTV


def _build_service():
    if not YOUTUBE_API_KEY:
        raise ValueError("❌ YOUTUBE_API_KEY가 설정되어 있지 않습니다. Streamlit Cloud Secrets를 확인하세요.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def fetch_videos_in_range(
    start_date: datetime.date,
    end_date: datetime.date,
    max_results: int = 500,
    channel_id: str = CHANNEL_ID,
) -> list[dict]:
    service = _build_service()

    published_after = datetime.datetime(
        start_date.year, start_date.month, start_date.day, 0, 0, 0
    ).isoformat() + "Z"
    published_before = datetime.datetime(
        end_date.year, end_date.month, end_date.day, 23, 59, 59
    ).isoformat() + "Z"

    videos = []
    next_page_token = None

    try:
        while True:
            fetch_count = min(50, max_results - len(videos))
            if fetch_count <= 0:
                break

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
            if not items:
                break

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
                    "cast": _extract_cast(
                        snippet.get("title", ""),
                        snippet.get("description", "")
                    ),
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    except HttpError as e:
        raise RuntimeError(f"❌ YouTube API 오류: {e.reason} (상태코드: {e.status_code})\n"
                           f"API 키와 할당량을 확인하세요.")

    return videos


def _extract_cast(title: str, description: str) -> str:
    bracket_match = re.findall(r"[\[【]([가-힣a-zA-Z\s·&]+?)(?:의|,|】|\])", title)
    if bracket_match:
        return ", ".join(m.strip() for m in bracket_match[:3])

    pipe_match = re.findall(r"\|\s*([가-힣a-zA-Z\s·,]+?)(?:\||$)", title)
    if pipe_match:
        return pipe_match[0].strip()

    first_line = description.split("\n")[0] if description else ""
    name_match = re.findall(r"([가-힣]{2,4})\s*(?:대표|위원|교수|기자|선생|이사|부장|MP)", first_line)
    if name_match:
        return ", ".join(name_match[:3])

    return "정보 없음"
