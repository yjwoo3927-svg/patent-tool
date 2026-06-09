import streamlit as st
import sys, os, tempfile
from collections import Counter
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))

from patent_engine import collect_patents, FOREIGN_COUNTRIES
from excel_output import create_patent_excel
from report_output import create_patent_report
from map_output import create_patent_map
from gsheet import load_internal_patents, filter_internal_patents

st.set_page_config(page_title="특허 서지정보 수집", page_icon="🔍", layout="wide")
st.title("🔍 특허 · 선행기술 서지정보 수집")
st.caption("KIPRIS Plus 한국 · 미국 · 유럽 · 일본 · 중국 · PCT + 내부 특허 통합 조회")

# ── API 키 ────────────────────────────────────────────────────────────────
try:
    KIPRIS_KEY = st.secrets["KIPRIS_KEY"]
    key_from_secret = True
except Exception:
    KIPRIS_KEY = ""
    key_from_secret = False

FLAG = {"KR":"🇰🇷","US":"🇺🇸","EP":"🇪🇺","WO":"🌐","JP":"🇯🇵","CN":"🇨🇳"}

# ════════════════════════════════════════════════════════════════════════════
# 공통 결과 표시 함수 (맨 위에 정의)
# ════════════════════════════════════════════════════════════════════════════
def _show_results(patents, keyword, assignee, key_prefix="ext", is_internal=False):
    t1, t2, t3, t4 = st.tabs(["📋 목록", "📊 특허지도", "⬇️ Excel", "📄 보고서"])

    with t1:
        rows = [{
            "국가":       FLAG.get(p["country"], p["country"]) + " " + p["country"],
            "출원번호":   p["patent_number"],
            "발명의 명칭": p["title"],
            "출원인":     p["assignee"],
            "발명자":     p.get("inventors") or "-",
            "IPC":        p["ipc_codes"],
            "출원일":     p["application_date"],
            "법적상태":   p["status"],
            "피인용":     p.get("citations", 0),
            "출처":       p["db_source"],
        } for p in patents]
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        if patents:
            st.subheader("상세 보기")
            sel = st.selectbox("특허 선택",
                [f"[{i+1}] {p['patent_number']} — {p['title'][:45]}"
                 for i, p in enumerate(patents)],
                key=f"{key_prefix}_sel")
            idx = int(sel.split("]")[0][1:]) - 1
            p = patents[idx]
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"**출원번호:** {p['patent_number']}")
                if is_internal and p.get("register_number"):
                    st.markdown(f"**등록번호:** {p['register_number']}")
                st.markdown(f"**국가:** {FLAG.get(p['country'],'')} {p['country']}")
                st.markdown(f"**출원인:** {p['assignee']}")
                st.markdown(f"**발명자:** {p.get('inventors') or '-'}")
                st.markdown(f"**IPC:** {p['ipc_codes']}")
                st.markdown(f"**출원일:** {p['application_date']}")
                st.markdown(f"**법적상태:** {p['status']}")
                if is_internal and p.get("exam_status"):
                    st.markdown(f"**심사상태:** {p['exam_status']}")
            with c2:
                st.markdown("**발명의 명칭**")
                st.info(p["title"])
                if is_internal and p.get("title_eng"):
                    st.caption(p["title_eng"])
                st.markdown("**초록**")
                st.write(p.get("abstract", ""))

    with t2:
        with st.spinner("특허지도 생성 중..."):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                map_path = f.name
            create_patent_map(patents, map_path)
        st.image(map_path, use_container_width=True)
        with open(map_path, "rb") as f:
            st.download_button("⬇️ 특허지도 PNG", data=f.read(),
                               file_name="특허지도.png", mime="image/png",
                               use_container_width=True, key=f"{key_prefix}_map")
        os.unlink(map_path)

    with t3:
        st.markdown("출원번호, 출원인, 발명자, IPC, 초록 등 전체 서지정보 + 요약 통계 차트")
        if st.button("📊 Excel 생성", use_container_width=True, key=f"{key_prefix}_xl_btn"):
            with st.spinner("Excel 생성 중..."):
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                    xl_path = f.name
                create_patent_excel(patents, xl_path)
            with open(xl_path, "rb") as f:
                st.download_button("⬇️ 특허_서지정보.xlsx", data=f.read(),
                                   file_name="특허_서지정보.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True, key=f"{key_prefix}_xl_dl")
            os.unlink(xl_path)

    with t4:
        st.markdown("조사 개요, 국가별·출원인별 현황 표, 특허 상세 서지정보, 분석 의견 포함")
        if st.button("📄 보고서 생성", use_container_width=True, key=f"{key_prefix}_rp_btn"):
            with st.spinner("보고서 생성 중..."):
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                    doc_path = f.name
                create_patent_report(patents, keyword, assignee, doc_path)
            with open(doc_path, "rb") as f:
                st.download_button("⬇️ 특허_조사보고서.docx", data=f.read(),
                                   file_name="특허_조사보고서.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   use_container_width=True, key=f"{key_prefix}_rp_dl")
            os.unlink(doc_path)


# ════════════════════════════════════════════════════════════════════════════
# 메인 탭
# ════════════════════════════════════════════════════════════════════════════
main_tab1, main_tab2 = st.tabs(["🌐 외부 특허 검색 (KIPRIS)", "🏢 내부 특허 조회 (네패스)"])

# ── 탭1: 외부 특허 검색 ──────────────────────────────────────────────────
with main_tab1:
    with st.sidebar:
        st.header("🔑 API 설정")
        if key_from_secret:
            st.success("API 키 연결됨 ✓")
            api_key = KIPRIS_KEY
        else:
            api_key = st.text_input("KIPRIS API 키", type="password",
                                    placeholder="KIPRIS Plus 서비스키 입력")
            if api_key:
                st.success("API 키 입력됨 ✓")

        use_demo = st.toggle("데모 데이터 사용", value=(not bool(api_key)))
        if use_demo:
            st.info("샘플 데이터로 동작 중")

        st.divider()
        st.header("🔍 검색 조건")
        keyword  = st.text_input("검색 키워드", placeholder="예: 배터리, lithium")
        assignee = st.text_input("출원인 / 권리자", placeholder="예: 삼성SDI")
        ipc      = st.text_input("IPC 코드", placeholder="예: H01M 4/36")
        c1, c2 = st.columns(2)
        with c1: date_from = st.text_input("출원일 시작", value="2020")
        with c2: date_to   = st.text_input("출원일 종료", value="2024")

        st.markdown("**검색 범위**")
        col1, col2 = st.columns(2)
        with col1: use_kr      = st.checkbox("🇰🇷 한국", value=True)
        with col2: use_foreign = st.checkbox("🌍 해외",  value=True)

        sel_countries = []
        if use_foreign:
            st.markdown("해외 국가")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                if st.checkbox("🇺🇸 US", value=True): sel_countries.append("US")
                if st.checkbox("🇪🇺 EP", value=True): sel_countries.append("EP")
            with cc2:
                if st.checkbox("🌐 WO", value=True): sel_countries.append("WO")
                if st.checkbox("🇯🇵 JP", value=True): sel_countries.append("JP")
            with cc3:
                if st.checkbox("🇨🇳 CN", value=True): sel_countries.append("CN")

        st.divider()
        search_btn = st.button("🔍 검색 시작", use_container_width=True, type="primary")

    if search_btn:
        if not keyword and not assignee and not ipc:
            st.warning("키워드, 출원인, IPC 코드 중 하나 이상 입력하세요.")
            st.stop()
        databases = []
        if use_kr:      databases.append("KIPRIS")
        if use_foreign: databases.append("KIPRIS_FOREIGN")
        if not databases:
            st.warning("한국 또는 해외 중 하나 이상 선택하세요.")
            st.stop()

        with st.spinner("특허 서지정보 수집 중..."):
            patents, total_kr, total_foreign = collect_patents(
                keyword=keyword, assignee=assignee, ipc=ipc,
                date_from=date_from, date_to=date_to,
                databases=databases, use_demo=use_demo,
                kipris_key=api_key, countries=sel_countries,
            )
        if not patents:
            st.warning("검색 결과가 없습니다. 조건을 변경해 보세요.")
            st.stop()
        st.session_state.update({
            "ext_patents": patents, "ext_keyword": keyword,
            "ext_assignee": assignee, "total_kr": total_kr,
            "total_foreign": total_foreign,
        })

    if "ext_patents" not in st.session_state:
        st.info("왼쪽 사이드바에서 검색 조건을 입력하고 검색 시작 버튼을 누르세요.")
    else:
        patents  = st.session_state["ext_patents"]
        keyword  = st.session_state.get("ext_keyword", "")
        assignee = st.session_state.get("ext_assignee", "")
        country_cnt  = Counter(p["country"]  for p in patents)
        assignee_cnt = Counter(p["assignee"] for p in patents)

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("총 수집",   f"{len(patents)}건")
        m2.metric("🇰🇷 한국",  f"{country_cnt.get('KR',0)}건")
        m3.metric("🌍 해외",   f"{sum(v for k,v in country_cnt.items() if k!='KR')}건")
        m4.metric("출원인 수", f"{len(assignee_cnt)}개사")
        m5.metric("국가 수",   f"{len(country_cnt)}개국")
        st.divider()
        _show_results(patents, keyword, assignee, key_prefix="ext")

# ── 탭2: 내부 특허 조회 ──────────────────────────────────────────────────
with main_tab2:
    st.subheader("🏢 네패스 내부 특허 조회")
    st.caption("Google Sheets 연동 — KIPRIS 다운로드 데이터 기준")

    col_r, _ = st.columns([1, 5])
    with col_r:
        if st.button("🔄 새로고침"):
            st.cache_data.clear()

    with st.spinner("내부 특허 데이터 불러오는 중..."):
        all_patents, err = load_internal_patents()

    if err:
        st.error(f"데이터 로드 실패: {err}\nGoogle Sheets 공개 설정을 확인해주세요.")
        st.stop()

    if not all_patents:
        st.warning("데이터가 없습니다. Google Sheets에 데이터를 입력해주세요.")
        st.info("👉 헤더: 순번 | 발명의명칭 | 발명의명칭(영문) | IPC분류 | 출원번호 | 출원일자 | 출원인 | 등록번호 | 등록일자 | 공개일자 | 법적상태 | 심사진행상태 | 요약 | 발명자 | 지정국 | 피인용 횟수 | 청구항")
        st.stop()

    with st.expander("🔍 검색 필터", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1: int_keyword  = st.text_input("키워드",  key="int_kw", placeholder="발명 명칭, 초록")
        with fc2: int_assignee = st.text_input("출원인",  key="int_as", placeholder="출원인명")
        with fc3: int_ipc      = st.text_input("IPC 코드", key="int_ipc", placeholder="예: H01L")
        fc4, fc5, fc6 = st.columns(3)
        with fc4: int_from   = st.text_input("출원일 시작", key="int_df", value="")
        with fc5: int_to     = st.text_input("출원일 종료", key="int_dt", value="")
        with fc6:
            statuses   = ["전체"] + list(set(p["status"] for p in all_patents if p["status"]))
            int_status = st.selectbox("법적상태", statuses, key="int_st")

    patents = filter_internal_patents(
        all_patents, keyword=int_keyword, assignee=int_assignee,
        ipc=int_ipc, date_from=int_from, date_to=int_to, status=int_status)

    status_cnt = Counter(p["status"] for p in all_patents)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("전체 보유",  f"{len(all_patents)}건")
    m2.metric("검색 결과", f"{len(patents)}건")
    m3.metric("등록",      f"{status_cnt.get('등록',0)}건")
    m4.metric("출원중",    f"{sum(v for k,v in status_cnt.items() if k not in ['등록','소멸','포기'])}건")
    st.divider()
    _show_results(patents, int_keyword, int_assignee, key_prefix="int", is_internal=True)
