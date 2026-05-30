import streamlit as st
import datetime
from youtube_fetcher import fetch_videos_in_range
from summarizer import summarize_video
from cache_manager import CacheManager
from channel_manager import load_channels, add_channel, remove_channel, resolve_channel_id

st.set_page_config(page_title="유튜브 경제 채널 대시보드", page_icon="📺", layout="wide")

st.markdown("""
<style>
.card {
    background: #1e1e2e; border: 1px solid #313244;
    border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;
}
.card-title { font-size: 1.05rem; font-weight: 700; color: #cdd6f4; margin-bottom: 6px; }
.card-meta { font-size: 0.82rem; color: #a6adc8; margin-bottom: 12px; }
.card-summary {
    font-size: 0.9rem; color: #cdd6f4; line-height: 1.8;
    background: #181825; border-radius: 8px; padding: 14px 18px;
    white-space: pre-wrap;
}
.search-hit { background: #2a2a3e; border-left: 3px solid #f38ba8; }
.quick-btn { margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

st.title("📺 유튜브 경제 채널 대시보드")
cache = CacheManager()

# ── 사이드바 ──────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")

    # ── 날짜 모드 선택 ──
    st.subheader("📅 수집 기간")
    date_mode = st.radio("", ["날짜 선택", "기간 선택"], horizontal=True, label_visibility="collapsed")

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    if date_mode == "날짜 선택":
        # 빠른 버튼
        st.caption("빠른 선택")
        qcol1, qcol2 = st.columns(2)
        with qcol1:
            if st.button("오늘", use_container_width=True):
                st.session_state["single_date"] = today
            if st.button("그저께", use_container_width=True):
                st.session_state["single_date"] = today - datetime.timedelta(days=2)
        with qcol2:
            if st.button("어제", use_container_width=True):
                st.session_state["single_date"] = yesterday
            if st.button("3일 전", use_container_width=True):
                st.session_state["single_date"] = today - datetime.timedelta(days=3)

        selected_date = st.date_input(
            "날짜",
            value=st.session_state.get("single_date", today),
            min_value=datetime.date(2020, 1, 1),
            max_value=today,
            label_visibility="collapsed",
        )
        st.session_state["single_date"] = selected_date
        start_date = selected_date
        end_date = selected_date
        st.caption(f"📌 {selected_date.strftime('%Y년 %m월 %d일')} 하루 영상")

    else:
        # 빠른 버튼
        st.caption("빠른 선택")
        qcol1, qcol2 = st.columns(2)
        with qcol1:
            if st.button("최근 3일", use_container_width=True):
                st.session_state["range_start"] = today - datetime.timedelta(days=2)
                st.session_state["range_end"] = today
            if st.button("최근 14일", use_container_width=True):
                st.session_state["range_start"] = today - datetime.timedelta(days=13)
                st.session_state["range_end"] = today
        with qcol2:
            if st.button("최근 7일", use_container_width=True):
                st.session_state["range_start"] = today - datetime.timedelta(days=6)
                st.session_state["range_end"] = today
            if st.button("이번 달", use_container_width=True):
                st.session_state["range_start"] = today.replace(day=1)
                st.session_state["range_end"] = today

        col_s, col_e = st.columns(2)
        with col_s:
            start_date = st.date_input(
                "시작일",
                value=st.session_state.get("range_start", datetime.date(2026, 5, 1)),
                min_value=datetime.date(2020, 1, 1),
                max_value=today,
            )
            st.session_state["range_start"] = start_date
        with col_e:
            end_date = st.date_input(
                "종료일",
                value=st.session_state.get("range_end", today),
                min_value=datetime.date(2020, 1, 1),
                max_value=today,
            )
            st.session_state["range_end"] = end_date

        if start_date > end_date:
            st.error("시작일이 종료일보다 늦습니다.")

    st.divider()

    # ── 채널 추가 ──
    st.subheader("➕ 채널 추가")
    new_url = st.text_input("유튜브 채널 URL", placeholder="https://youtube.com/@채널명")
    new_name = st.text_input("채널 별명", placeholder="예: 언더스탠딩")
    if st.button("채널 추가", use_container_width=True):
        if new_url and new_name:
            with st.spinner("채널 ID 조회 중..."):
                try:
                    cid, _ = resolve_channel_id(new_url)
                    add_channel(new_name, cid, new_url)
                    st.success(f"✅ '{new_name}' 채널 추가 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")
        else:
            st.warning("URL과 채널 별명을 모두 입력하세요.")

    st.divider()

    # ── 채널 삭제 ──
    channels = load_channels()
    if len(channels) > 1:
        st.subheader("🗑️ 채널 삭제")
        del_name = st.selectbox("삭제할 채널", [c["name"] for c in channels])
        if st.button("삭제", type="secondary"):
            target = next(c for c in channels if c["name"] == del_name)
            remove_channel(target["channel_id"])
            st.success(f"'{del_name}' 삭제됨")
            st.rerun()

    st.divider()
    st.metric("캐시된 영상 수", len(cache.get_all_ids()))
    if st.button("🗑️ 캐시 초기화", type="secondary"):
        cache.clear()
        st.success("캐시 초기화 완료")
        st.rerun()

# ── 검색 ──────────────────────────────────────────────────────
st.subheader("🔍 종목 / 키워드 검색")
search_col1, search_col2 = st.columns([4, 1])
with search_col1:
    search_query = st.text_input("", placeholder="예: 삼성전자, SK하이닉스, 금리 ...", label_visibility="collapsed")
with search_col2:
    do_search = st.button("검색", use_container_width=True)

if do_search and search_query.strip():
    all_cache = cache.get_all()
    hits = [
        item for item in all_cache
        if search_query.strip() in (item.get("summary") or "")
        or search_query.strip() in (item.get("title") or "")
    ]
    hits.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    st.markdown(f"**'{search_query}' 검색 결과: {len(hits)}건**")
    if hits:
        for r in hits:
            st.markdown(f"""
<div class="card search-hit">
  <div class="card-title">
    <a href="{r.get('url','#')}" target="_blank" style="color:#89b4fa;text-decoration:none;">
      ▶ {r.get('title','')}
    </a>
  </div>
  <div class="card-meta">📅 {r.get('published_at','')[:16]} &nbsp;|&nbsp; 👤 {r.get('cast','-')}</div>
  <div class="card-summary">{r.get('summary','')}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.info("검색 결과가 없습니다. 먼저 해당 기간 영상을 요약해주세요.")
    st.divider()

# ── 채널 탭 ───────────────────────────────────────────────────
channels = load_channels()
tabs = st.tabs([f"📡 {c['name']}" for c in channels])

for tab, channel in zip(tabs, channels):
    with tab:
        run_btn = st.button(
            f"🚀 {channel['name']} 요약 시작",
            key=f"run_{channel['channel_id']}",
            type="primary",
            use_container_width=True,
        )

        if run_btn:
            if start_date > end_date:
                st.error("시작일이 종료일보다 늦습니다.")
                st.stop()

            st.divider()

            with st.status("📡 YouTube에서 영상 목록 수집 중...", expanded=True) as status:
                try:
                    videos = fetch_videos_in_range(
                        start_date=start_date,
                        end_date=end_date,
                        max_results=500,
                        channel_id=channel["channel_id"],
                    )
                    status.update(label=f"✅ {len(videos)}개 영상 발견", state="complete")
                except Exception as e:
                    status.update(label="❌ 수집 실패", state="error")
                    st.error(str(e))
                    st.stop()

            if not videos:
                st.warning("해당 기간에 업로드된 영상이 없습니다.")
                st.stop()

            new_videos = [v for v in videos if not cache.exists(v["video_id"])]
            cached_videos = [v for v in videos if cache.exists(v["video_id"])]

            c1, c2, c3 = st.columns(3)
            c1.metric("전체 영상", len(videos))
            c2.metric("신규 요약", len(new_videos))
            c3.metric("캐시 재사용", len(cached_videos))

            if new_videos:
                est = len(new_videos) * 7
                st.info(f"⏱️ 예상 소요 시간: 약 {est//60}분 {est%60}초")

            st.divider()

            results = [cache.get(v["video_id"]) for v in cached_videos]

            if new_videos:
                progress = st.progress(0, text="요약 중...")
                for i, video in enumerate(new_videos):
                    progress.progress(
                        (i + 1) / len(new_videos),
                        text=f"[{i+1}/{len(new_videos)}] {video['title'][:35]}...",
                    )
                    try:
                        result = summarize_video(video=video)
                        cache.save(result)
                        results.append(result)
                    except Exception as e:
                        results.append({**video, "summary": f"⚠️ 요약 실패: {e}"})
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
    📅 {r.get('published_at','')[:16]} &nbsp;|&nbsp;
    👤 {r.get('cast','-')} &nbsp;|&nbsp;
    {'💾 캐시' if is_cached else '🆕 신규'}
  </div>
  <div class="card-summary">{r.get('summary','요약 없음')}</div>
</div>""", unsafe_allow_html=True)

        else:
            # 버튼 누르기 전 — 기간 내 캐시 자동 표시
            all_cache = cache.get_all()
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            cached_in_range = [
                item for item in all_cache
                if start_str <= item.get("published_at", "")[:10] <= end_str
            ]
            cached_in_range.sort(key=lambda x: x.get("published_at", ""), reverse=True)

            if cached_in_range:
                st.caption(f"💾 선택 기간 내 저장된 요약본 {len(cached_in_range)}개")
                for r in cached_in_range:
                    st.markdown(f"""
<div class="card">
  <div class="card-title">
    <a href="{r.get('url','#')}" target="_blank" style="color:#89b4fa;text-decoration:none;">
      ▶ {r.get('title','제목 없음')}
    </a>
  </div>
  <div class="card-meta">
    📅 {r.get('published_at','')[:16]} &nbsp;|&nbsp;
    👤 {r.get('cast','-')} &nbsp;|&nbsp; 💾 캐시
  </div>
  <div class="card-summary">{r.get('summary','요약 없음')}</div>
</div>""", unsafe_allow_html=True)
            else:
                st.info("위의 '요약 시작' 버튼을 눌러 영상을 수집하세요.")

# ── 전체 캐시 보기 ────────────────────────────────────────────
with st.expander("📦 전체 캐시 보기"):
    all_cache = cache.get_all()
    if all_cache:
        for item in sorted(all_cache, key=lambda x: x.get("published_at", ""), reverse=True):
            st.markdown(
                f"**{item.get('published_at','')[:10]}** — "
                f"[{item.get('title','')}]({item.get('url','#')})"
            )
    else:
        st.info("캐시 없음")
