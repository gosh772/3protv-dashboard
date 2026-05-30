import streamlit as st
import datetime
from youtube_fetcher import fetch_videos_in_range
from summarizer import summarize_video
from cache_manager import CacheManager

st.set_page_config(
    page_title="삼프로TV 온디맨드 대시보드",
    page_icon="📺",
    layout="wide",
)

st.markdown("""
<style>
.card {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
}
.card-title { font-size: 1.1rem; font-weight: 700; color: #cdd6f4; margin-bottom: 6px; }
.card-meta { font-size: 0.82rem; color: #a6adc8; margin-bottom: 12px; }
.card-summary {
    font-size: 0.9rem; color: #cdd6f4; line-height: 1.7;
    background: #181825; border-radius: 8px; padding: 12px 16px;
    white-space: pre-wrap;
}
</style>
""", unsafe_allow_html=True)

st.title("📺 삼프로TV 온디맨드 대시보드")
st.caption("버튼을 누르면 지정 기간의 영상을 전부 수집·요약합니다. 처리된 영상은 캐시에 저장되어 재호출 시 비용이 발생하지 않습니다.")

cache = CacheManager()

with st.sidebar:
    st.header("⚙️ 설정")

    st.subheader("📅 수집 기간")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input("시작일", value=datetime.date(2026, 5, 1),
            min_value=datetime.date(2020, 1, 1), max_value=datetime.date.today())
    with col_e:
        end_date = st.date_input("종료일", value=datetime.date.today(),
            min_value=datetime.date(2020, 1, 1), max_value=datetime.date.today())

    st.divider()
    cached_ids = cache.get_all_ids()
    st.metric("캐시된 영상 수", len(cached_ids))
    if st.button("🗑️ 캐시 초기화", type="secondary"):
        cache.clear()
        st.success("캐시가 초기화되었습니다.")
        st.rerun()

run_btn = st.button("🚀 요약 시작", type="primary", use_container_width=True)

if run_btn:
    if start_date > end_date:
        st.error("시작일이 종료일보다 늦습니다.")
        st.stop()

    st.divider()

    with st.status("📡 YouTube에서 영상 목록을 가져오는 중...", expanded=True) as status:
        try:
            # max_results=500으로 설정해 사실상 전체 영상 수집
            videos = fetch_videos_in_range(
                start_date=start_date,
                end_date=end_date,
                max_results=500,
            )
            status.update(label=f"✅ {len(videos)}개 영상 발견", state="complete")
        except Exception as e:
            status.update(label=f"❌ 수집 실패: {e}", state="error")
            st.error(str(e))
            st.stop()

    if not videos:
        st.warning("해당 기간에 업로드된 영상이 없습니다.")
        st.stop()

    new_videos = [v for v in videos if not cache.exists(v["video_id"])]
    cached_videos = [v for v in videos if cache.exists(v["video_id"])]

    c1, c2, c3 = st.columns(3)
    c1.metric("전체 영상", len(videos))
    c2.metric("신규 (API 호출)", len(new_videos))
    c3.metric("캐시 히트", len(cached_videos))

    st.divider()

    results = [cache.get(v["video_id"]) for v in cached_videos]

    if new_videos:
        progress = st.progress(0, text="신규 영상 요약 중...")
        for i, video in enumerate(new_videos):
            progress.progress(
                (i + 1) / len(new_videos),
                text=f"[{i+1}/{len(new_videos)}] {video['title'][:40]}..."
            )
            try:
                result = summarize_video(video=video)
                cache.save(result)
                results.append(result)
            except Exception as e:
                results.append({**video, "summary": f"⚠️ 요약 실패: {e}", "cast": "-"})
        progress.empty()

    results.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    st.success(f"✅ 총 {len(results)}개 영상 처리 완료")
    st.divider()

    for r in results:
        is_cached = r.get("video_id") in [v["video_id"] for v in cached_videos]
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
    {'💾 캐시' if is_cached else '🆕 신규'}
  </div>
  <div class="card-summary">{r.get('summary','요약 없음')}</div>
</div>
""", unsafe_allow_html=True)

with st.expander("📦 저장된 캐시 전체 보기"):
    all_cache = cache.get_all()
    if all_cache:
        for item in sorted(all_cache, key=lambda x: x.get("published_at",""), reverse=True):
            st.markdown(f"**{item.get('published_at','')[:10]}** — [{item.get('title','')}]({item.get('url','#')}) — {item.get('cast','-')}")
    else:
        st.info("아직 캐시된 영상이 없습니다.")
