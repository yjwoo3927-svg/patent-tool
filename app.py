import streamlit as st
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))

from patent_engine import collect_patents, FOREIGN_COUNTRIES
from excel_output import create_patent_excel
from report_output import create_patent_report
from map_output import create_patent_map

st.set_page_config(page_title="특허 서지정보 수집", page_icon="🔍", layout="wide")
st.title("🔍 특허 · 선행기술 서지정보 수집")
st.caption("KIPRIS Plus — 한국 + 미국 · 유럽 · 일본 · 중국 · PCT 통합 검색")

# ── API 키: Streamlit Secrets 또는 사이드바 입력 ──────────────────────────
try:
    KIPRIS_KEY = st.secrets["KIPRIS_KEY"]
    key_from_secret = True
except Exception:
    KIPRIS_KEY = ""
    key_from_secret = False

# ── 사이드바 ──────────────────────────────────────────────────────────────
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

    keyword  = st.text_input("검색 키워드", placeholder="예: 배터리, lithium ion")
    assignee = st.text_input("출원인 / 권리자", placeholder="예: 삼성SDI, LG Chem")
    ipc      = st.text_input("IPC 코드", placeholder="예: H01M 4/36")

    c1, c2 = st.columns(2)
    with c1: date_from = st.text_input("출원일 시작", value="2020")
    with c2: date_to   = st.text_input("출원일 종료", value="2024")

    st.markdown("**검색 범위**")
    col1, col2 = st.columns(2)
    with col1:
        use_kr = st.checkbox("🇰🇷 한국", value=True)
    with col2:
        use_foreign = st.checkbox("🌍 해외", value=True)

    if use_foreign:
        st.markdown("해외 국가 선택")
        sel_countries = []
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            if st.checkbox("🇺🇸 US", value=True): sel_countries.append("US")
            if st.checkbox("🇪🇺 EP", value=True): sel_countries.append("EP")
        with cc2:
            if st.checkbox("🌐 WO", value=True): sel_countries.append("WO")
            if st.checkbox("🇯🇵 JP", value=True): sel_countries.append("JP")
        with cc3:
            if st.checkbox("🇨🇳 CN", value=True): sel_countries.append("CN")
    else:
        sel_countries = []

    st.divider()
    search_btn = st.button("🔍 검색 시작", use_container_width=True, type="primary")

# ── 검색 실행 ────────────────────────────────────────────────────────────
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

    with st.spinner("특허 서지정보 수집 중... (상세정보 포함 시 시간이 걸릴 수 있어요)"):
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
        "patents": patents, "keyword": keyword, "assignee": assignee,
        "total_kr": total_kr, "total_foreign": total_foreign,
    })

# ── 결과 표시 ────────────────────────────────────────────────────────────
if "patents" not in st.session_state:
    st.info("왼쪽 사이드바에서 검색 조건을 입력하고 검색 시작 버튼을 누르세요.")
    st.stop()

patents  = st.session_state["patents"]
keyword  = st.session_state.get("keyword", "")
assignee = st.session_state.get("assignee", "")
total_kr = st.session_state.get("total_kr", 0)
total_fo = st.session_state.get("total_foreign", 0)

from collections import Counter
country_cnt  = Counter(p["country"]  for p in patents)
assignee_cnt = Counter(p["assignee"] for p in patents)

# 요약 지표
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("총 수집", f"{len(patents)}건")
m2.metric("🇰🇷 한국", f"{country_cnt.get('KR',0)}건")
m3.metric("🌍 해외", f"{sum(v for k,v in country_cnt.items() if k!='KR')}건")
m4.metric("출원인 수", f"{len(assignee_cnt)}개사")
m5.metric("국가 수", f"{len(country_cnt)}개국")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📋 서지정보 목록", "📊 특허지도", "⬇️ Excel", "📄 보고서"])

# ── 탭1: 목록 ──────────────────────────────────────────────────────────
with tab1:
    import pandas as pd
    FLAG = {"KR":"🇰🇷","US":"🇺🇸","EP":"🇪🇺","WO":"🌐","JP":"🇯🇵","CN":"🇨🇳"}

    rows = [{
        "국가": FLAG.get(p["country"],p["country"]) + " " + p["country"],
        "출원번호": p["patent_number"],
        "발명의 명칭": p["title"],
        "출원인": p["assignee"],
        "발명자": p["inventors"] or "-",
        "IPC": p["ipc_codes"],
        "출원일": p["application_date"],
        "현황": p["status"],
        "출처": p["db_source"],
    } for p in patents]

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 더보기 안내
    if total_kr + total_fo > len(patents):
        st.info(f"전체 {total_kr+total_fo}건 중 {len(patents)}건 표시 중. "
                f"더 많은 결과는 페이지 번호를 변경하세요.")

    st.subheader("상세 보기")
    options = [f"[{i+1}] {p['patent_number']} — {p['title'][:50]}" for i, p in enumerate(patents)]
    sel = st.selectbox("특허 선택", options)
    idx = int(sel.split("]")[0][1:]) - 1
    p = patents[idx]

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"**출원번호:** {p['patent_number']}")
        st.markdown(f"**국가:** {FLAG.get(p['country'],'')} {p['country']}")
        st.markdown(f"**출원인:** {p['assignee']}")
        st.markdown(f"**발명자:** {p['inventors'] or '-'}")
        st.markdown(f"**IPC:** {p['ipc_codes']}")
        st.markdown(f"**출원일:** {p['application_date']}")
        st.markdown(f"**현황:** {p['status']}")
        st.markdown(f"**출처:** {p['db_source']}")
    with c2:
        st.markdown("**발명의 명칭**")
        st.info(p["title"])
        st.markdown("**초록**")
        st.write(p.get("abstract",""))

# ── 탭2: 특허지도 ──────────────────────────────────────────────────────
with tab2:
    with st.spinner("특허지도 생성 중..."):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            map_path = f.name
        create_patent_map(patents, map_path)
    st.image(map_path, use_container_width=True)
    with open(map_path, "rb") as f:
        st.download_button("⬇️ 특허지도 PNG 다운로드", data=f.read(),
                           file_name="특허지도.png", mime="image/png",
                           use_container_width=True)
    os.unlink(map_path)

# ── 탭3: Excel ──────────────────────────────────────────────────────────
with tab3:
    st.markdown("출원번호, 출원인, 발명자, IPC, 초록 등 전체 서지정보 + 요약 통계 차트 포함")
    if st.button("📊 Excel 파일 생성", use_container_width=True):
        with st.spinner("Excel 생성 중..."):
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                xl_path = f.name
            create_patent_excel(patents, xl_path)
        with open(xl_path, "rb") as f:
            st.download_button("⬇️ 특허_서지정보.xlsx 다운로드", data=f.read(),
                               file_name="특허_서지정보.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        os.unlink(xl_path)

# ── 탭4: 보고서 ────────────────────────────────────────────────────────
with tab4:
    st.markdown("조사 개요, 국가별·출원인별 현황 표, 특허 상세 서지정보, 분석 의견 포함")
    if st.button("📄 보고서 생성", use_container_width=True):
        with st.spinner("보고서 생성 중..."):
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                doc_path = f.name
            create_patent_report(patents, keyword, assignee, doc_path)
        with open(doc_path, "rb") as f:
            st.download_button("⬇️ 특허_조사보고서.docx 다운로드", data=f.read(),
                               file_name="특허_조사보고서.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)
        os.unlink(doc_path)
