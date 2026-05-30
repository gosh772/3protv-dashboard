"""
channel_manager.py - 사용자 정의 채널 목록 관리 (JSON 저장)
"""

import json
from pathlib import Path

CHANNELS_FILE = Path(__file__).parent / "cache" / "channels.json"

DEFAULT_CHANNELS = [
    {
        "name": "삼프로TV",
        "channel_id": "UChlv4GSd7OQl3js-jkLOnFA",
        "url": "https://youtube.com/@3protv",
    }
]


def load_channels() -> list[dict]:
    CHANNELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CHANNELS_FILE.exists():
        save_channels(DEFAULT_CHANNELS)
        return DEFAULT_CHANNELS
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_channels(channels: list[dict]):
    CHANNELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)


def add_channel(name: str, channel_id: str, url: str) -> list[dict]:
    channels = load_channels()
    # 중복 방지
    if any(c["channel_id"] == channel_id for c in channels):
        return channels
    channels.append({"name": name, "channel_id": channel_id, "url": url})
    save_channels(channels)
    return channels


def remove_channel(channel_id: str) -> list[dict]:
    channels = load_channels()
    channels = [c for c in channels if c["channel_id"] != channel_id]
    save_channels(channels)
    return channels


def resolve_channel_id(youtube_url: str) -> tuple[str, str]:
    """
    유튜브 URL에서 채널 ID와 채널명을 추출합니다.
    @handle 형식은 YouTube API로 조회합니다.
    """
    import os
    import re
    from googleapiclient.discovery import build

    # channel/UC... 형식
    match = re.search(r"channel/(UC[\w-]+)", youtube_url)
    if match:
        cid = match.group(1)
        return cid, cid

    # @handle 형식
    handle_match = re.search(r"@([\w.-]+)", youtube_url)
    if handle_match:
        handle = handle_match.group(1)
        api_key = os.getenv("YOUTUBE_API_KEY")
        service = build("youtube", "v3", developerKey=api_key)
        resp = service.search().list(
            part="snippet", q=f"@{handle}", type="channel", maxResults=1
        ).execute()
        items = resp.get("items", [])
        if items:
            cid = items[0]["snippet"]["channelId"]
            name = items[0]["snippet"]["channelTitle"]
            return cid, name

    raise ValueError("채널 ID를 찾을 수 없습니다. URL을 확인해주세요.")
