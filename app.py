import streamlit as st
import datetime
import json
import os
from pathlib import Path

from youtube_fetcher import fetch_videos_in_range
from summarizer import summarize_video
from cache_manager import CacheManager

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="삼프로TV 온디맨드 대시보드",
    page_icon="📺",
    layout="wide",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
.card {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
}
.card-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #cdd6f4;
    margin-bottom: 6px;
}
.card-meta {
    font-size: 0.82rem;
    color: #a6adc8;
    margin-bottom: 12px;
}
.card-summary {
    font-size: 0.9rem;
    color: #cdd6f4;
    line-height: 1.7;
    background: #181825;
    border-radius: 8px;
    padding: 12px 16px;
}
.badge {
    display: inline-block;
    background: #313244;
    color: #89b4fa;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.78rem;
    margin-right: 6px;
}
.stat-box {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ── 헤더 ─────────────────────────────────────────────────────
st.title("📺 삼프로TV 온디맨드 대시보드")
st.caption("버튼을 누르면 지정 기간의 영상을 수집·요약합니다. 이미 처리된 영상은 캐시에서 불러와 API 비용을 절감합니다.")

cache = CacheManager()

# ── 사이드바 설정 ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")

    st.subheader("📅 수집 기간")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input(
            "시작일",
            value=datetime.date(2026, 5, 1),
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date.today(),
        )
    with col_e:
        end_date = st.date_input(
            "종료일",
            value=datetime.date.today(),
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date.today(),
        )

    st.subheader("🤖 LLM 선택")
    llm_choice = st.radio("요약에 사용할 LLM", ["Anthropic (Claude)", "OpenAI (GPT)"])

    st.subheader("📊 처리 옵션")
    max_videos = st.slider("최대 영상 수", 5, 50, 20)
    skip_no_transcript = st.checkbox("자막 없는 영상 건너뛰기", value=True)

    st.divider()
    cached_ids = cache.get_all_ids()
    st.metric("캐시된 영상 수", len(cached_ids))
    if st.button("🗑️ 캐시 초기화", type="secondary"):
        cache.clear()
        st.success("캐시가 초기화되었습니다.")
        st.rerun()

# ── 메인 영역 ─────────────────────────────────────────────────
run_btn = st.button("🚀 요약 시작", type="primary", use_container_width=True)

if run_btn:
    if start_date > end_date:
        st.error("시작일이 종료일보다 늦습니다.")
        st.stop()

    st.divider()

    # 1) 영상 목록 수집
    with st.status("📡 YouTube에서 영상 목록을 가져오는 중...", expanded=True) as status:
        try:
            videos = fetch_videos_in_range(
                start_date=start_date,
                end_date=end_date,
                max_results=max_videos,
            )
            status.update(label=f"✅ {len(videos)}개 영상 발견", state="complete")
        except Exception as e:
            status.update(label=f"❌ 수집 실패: {e}", state="error")
            st.error(str(e))
            st.stop()

    if not videos:
        st.warning("해당 기간에 업로드된 영상이 없습니다.")
        st.stop()

    # 2) 통계
    new_videos = [v for v in videos if not cache.exists(v["video_id"])]
    cached_videos = [v for v in videos if cache.exists(v["video_id"])]

    c1, c2, c3 = st.columns(3)
    c1.metric("전체 영상", len(videos))
    c2.metric("신규 (API 호출)", len(new_videos))
    c3.metric("캐시 히트", len(cached_videos))

    st.divider()

    # 3) 요약 처리
    results = []

    # 캐시된 영상 먼저 로드
    for v in cached_videos:
        results.append(cache.get(v["video_id"]))

    # 신규 영상 요약
    if new_videos:
        progress = st.progress(0, text="신규 영상 요약 중...")
        for i, video in enumerate(new_videos):
            progress.progress(
                (i + 1) / len(new_videos),
                text=f"[{i+1}/{len(new_videos)}] {video['title'][:40]}..."
            )
            try:
                result = summarize_video(
                    video=video,
                    llm=llm_choice,
                    skip_no_transcript=skip_no_transcript,
                )
                cache.save(result)
                results.append(result)
            except Exception as e:
                results.append({**video, "summary": f"⚠️ 요약 실패: {e}", "cast": "-"})

        progress.empty()

    # 날짜 내림차순 정렬
    results.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    st.success(f"✅ 총 {len(results)}개 영상 처리 완료")
    st.divider()

    # 4) 카드 출력
    for r in results:
        from_cache = cache.exists(r.get("video_id", "")) and r in cached_videos

        with st.container():
            st.markdown(f"""
<div class="card">
  <div class="card-title">
    <a href="{r.get('url','#')}" target="_blank" style="color:#89b4fa;text-decoration:none;">
      ▶ {r.get('title','제목 없음')}
    </a>
  </div>
  <div class="card-meta">
    📅 {r.get('published_at','')[:10]} &nbsp;|&nbsp;
    👤 {r.get('cast','-')} &nbsp;|&nbsp;
    {'💾 캐시' if from_cache else '🆕 신규'}
  </div>
  <div class="card-summary">{r.get('summary','요약 없음')}</div>
</div>
""", unsafe_allow_html=True)

# ── 캐시 뷰어 ─────────────────────────────────────────────────
with st.expander("📦 저장된 캐시 전체 보기"):
    all_cache = cache.get_all()
    if all_cache:
        for item in sorted(all_cache, key=lambda x: x.get("published_at",""), reverse=True):
            st.markdown(f"**{item.get('published_at','')[:10]}** — [{item.get('title','')}]({item.get('url','#')}) — {item.get('cast','-')}")
    else:
        st.info("아직 캐시된 영상이 없습니다.")
