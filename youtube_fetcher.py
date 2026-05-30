"""
youtube_fetcher.py - KST 시간대 처리 포함
"""

import os
import datetime
import re
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")


def _build_service():
    if not YOUTUBE_API_KEY:
        raise ValueError("❌ YOUTUBE_API_KEY가 설정되어 있지 않습니다.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def fetch_videos_in_range(
    start_date: datetime.date,
    end_date: datetime.date,
    max_results: int = 500,
    channel_id: str = "UChlv4GSd7OQl3js-jkLOnFA",
) -> list[dict]:
    service = _build_service()

    # KST 00:00 → UTC 변환 (KST = UTC+9)
    start_kst = datetime.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=KST)
    end_kst = datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=KST)

    published_after = start_kst.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    published_before = end_kst.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

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

                # publishedAt을 KST로 변환해서 저장
                pub_utc = snippet.get("publishedAt", "")
                pub_kst = _utc_to_kst_str(pub_utc)

                videos.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "published_at": pub_kst,
                    "description": snippet.get("description", ""),
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "cast": _extract_cast(snippet.get("title", ""), snippet.get("description", "")),
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    except HttpError as e:
        raise RuntimeError(f"❌ YouTube API 오류: {e.reason} (코드: {e.status_code})")

    return videos


def _utc_to_kst_str(utc_str: str) -> str:
    """UTC ISO 문자열을 KST로 변환"""
    try:
        dt = datetime.datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        dt_kst = dt.astimezone(KST)
        return dt_kst.strftime("%Y-%m-%d %H:%M KST")
    except Exception:
        return utc_str


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
