"""
특허 서지정보 수집 엔진 v2
- KIPRIS Plus 한국특허 검색 + 상세정보
- KIPRIS Plus 해외특허 검색 + 상세정보
- USPTO PatentsView (보조, 키 불필요)
- 데모 모드 지원
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

KIPRIS_BASE   = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice"
FOREIGN_SEARCH = "http://plus.kipris.or.kr/openapi/rest/ForeignPatentGeneralSearchService/advancedSearch"
FOREIGN_DETAIL = "http://plus.kipris.or.kr/openapi/rest/ForeignPatentBibliographicService/bibliographicInfo"

FOREIGN_COUNTRIES = ["US", "EP", "WO", "JP", "CN"]

# ── 샘플 데이터 ────────────────────────────────────────────────────────────
SAMPLE_PATENTS = [
    {"patent_number":"KR10-2021-0087654","title":"리튬이온 배터리용 실리콘 복합 음극재 제조방법",
     "assignee":"LG에너지솔루션","inventors":"김철수; 이영희; 박민준",
     "ipc_codes":"H01M 4/36; H01M 10/0525","application_date":"2021-07-05",
     "publication_date":"2023-02-10","country":"KR",
     "abstract":"본 발명은 실리콘 복합 음극재를 제조하는 방법에 관한 것으로, 나노 실리콘 입자를 탄소 매트릭스에 분산시켜 사이클 안정성과 에너지 밀도를 향상시킨다.",
     "claims_count":15,"citations":8,"status":"등록","tech_field":"배터리/에너지저장","db_source":"KIPRIS"},
    {"patent_number":"US11456789","title":"Silicon composite anode material for lithium ion battery",
     "assignee":"Samsung SDI Co., Ltd.","inventors":"Park, Jihoon; Kim, Sungwoo",
     "ipc_codes":"H01M 4/36; H01M 4/485","application_date":"2020-11-15",
     "publication_date":"2022-09-27","country":"US",
     "abstract":"A silicon composite anode material comprising nano-silicon particles dispersed in a carbon matrix with improved cycling stability.",
     "claims_count":22,"citations":14,"status":"Granted","tech_field":"Battery/Energy Storage","db_source":"KIPRIS_FOREIGN"},
    {"patent_number":"EP3987654","title":"Electrode material with improved cycle stability",
     "assignee":"SK Innovation Co., Ltd.","inventors":"Lee, Hyunsoo; Choi, Minkyung",
     "ipc_codes":"H01M 4/485; H01M 10/0567","application_date":"2021-03-20",
     "publication_date":"2022-12-14","country":"EP",
     "abstract":"An electrode material for secondary batteries with enhanced cycle stability through silicon oxides and graphene composite structure.",
     "claims_count":18,"citations":6,"status":"Published","tech_field":"Battery/Energy Storage","db_source":"KIPRIS_FOREIGN"},
    {"patent_number":"KR10-2022-0134512","title":"전고체 배터리용 황화물계 고체 전해질 및 제조방법",
     "assignee":"삼성SDI","inventors":"정수진; 최동훈; 윤재혁",
     "ipc_codes":"H01M 10/0562; H01M 10/058","application_date":"2022-10-18",
     "publication_date":"2024-04-25","country":"KR",
     "abstract":"전고체 배터리에 사용되는 황화물계 고체 전해질로 이온 전도도와 화학적 안정성을 동시에 향상시킨다.",
     "claims_count":20,"citations":3,"status":"공개","tech_field":"배터리/에너지저장","db_source":"KIPRIS"},
    {"patent_number":"JP2022-543210","title":"リチウムイオン電池用負極材料",
     "assignee":"Panasonic Holdings","inventors":"Tanaka, Hiroshi",
     "ipc_codes":"H01M 4/36","application_date":"2021-08-10",
     "publication_date":"2022-11-15","country":"JP",
     "abstract":"A negative electrode material for lithium-ion batteries with improved cycle stability using silicon-carbon composite.",
     "claims_count":12,"citations":9,"status":"Published","tech_field":"Battery/Energy Storage","db_source":"KIPRIS_FOREIGN"},
    {"patent_number":"CN114843452A","title":"一种锂离子电池正极材料及其制备方法",
     "assignee":"宁德时代 (CATL)","inventors":"曾毓群; 黄世琳",
     "ipc_codes":"H01M 4/525; H01M 4/505","application_date":"2022-04-12",
     "publication_date":"2022-07-29","country":"CN",
     "abstract":"高镍三元正极材料，通过表面包覆和体相掺杂协同改性，显著提升循环稳定性和热稳定性。",
     "claims_count":12,"citations":5,"status":"公开","tech_field":"Battery/Energy Storage","db_source":"KIPRIS_FOREIGN"},
    {"patent_number":"WO2022/098765","title":"High-capacity cathode material for next-generation lithium batteries",
     "assignee":"LG Chem, Ltd.","inventors":"Yoon, Jaehyuk; Kim, Dongwoo",
     "ipc_codes":"H01M 4/52; H01M 4/525","application_date":"2021-11-05",
     "publication_date":"2022-05-19","country":"WO",
     "abstract":"A nickel-rich layered oxide cathode material with suppressed capacity fade through surface coating treatment.",
     "claims_count":30,"citations":19,"status":"Published","tech_field":"Battery/Energy Storage","db_source":"KIPRIS_FOREIGN"},
    {"patent_number":"KR10-2023-0045678","title":"나트륨 이온 배터리용 양극 활물질",
     "assignee":"포스코홀딩스","inventors":"강민석; 조현우; 신지원",
     "ipc_codes":"H01M 4/58; H01M 10/054","application_date":"2023-04-03",
     "publication_date":"2024-10-10","country":"KR",
     "abstract":"나트륨 이온 배터리용 층상 산화물 양극 활물질로 저렴한 원가로 높은 에너지 밀도를 구현한다.",
     "claims_count":16,"citations":1,"status":"공개","tech_field":"배터리/에너지저장","db_source":"KIPRIS"},
]

# ── 유틸 함수 ───────────────────────────────────────────────────────────────
def _fmt_date(s):
    d = (s or "").replace("-","").replace(".","").strip()
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d)==8 else (s or "")

def _g(el, tag):
    e = el.find(tag)
    return e.text.strip() if e is not None and e.text else ""

def _parse_status(s):
    return {"A":"공개","C":"취하","F":"소멸","G":"포기","I":"무효","J":"거절","R":"등록"}.get(s, s or "공개")

# ── 한국특허 검색 ────────────────────────────────────────────────────────────
def search_kipris_kr(keyword="", assignee="", ipc="", date_from="", date_to="",
                     service_key="", page=1, num_rows=100):
    if not service_key:
        return [], 0
    params = {
        "ServiceKey": service_key,
        "patent": "true", "utility": "true",
        "numOfRows": num_rows, "pageNo": page,
        "descSort": "true", "sortSpec": "AD",
    }
    if keyword:  params["word"] = keyword
    if assignee: params["applicant"] = assignee
    if ipc:      params["ipcNumber"] = ipc
    if date_from and date_to:
        df = date_from.replace("-","") if "-" in date_from else f"{date_from}0101"
        dt = date_to.replace("-","")   if "-" in date_to   else f"{date_to}1231"
        params["applicationDate"] = f"{df}~{dt}"
    elif date_from:
        df = date_from.replace("-","") if "-" in date_from else f"{date_from}0101"
        params["applicationDate"] = f"{df}~99991231"
    try:
        resp = requests.get(f"{KIPRIS_BASE}/getAdvancedSearch", params=params, timeout=20)
        if resp.status_code != 200:
            return [], 0
        root = ET.fromstring(resp.text)
        total = int(_g(root, ".//totalCount") or "0")
        results = []
        for item in root.findall(".//item"):
            results.append({
                "patent_number": _g(item, "applicationNumber"),
                "title":         _g(item, "inventionTitle"),
                "assignee":      _g(item, "applicantName"),
                "inventors":     "",
                "ipc_codes":     _g(item, "ipcNumber"),
                "application_date": _fmt_date(_g(item, "applicationDate")),
                "publication_date": _fmt_date(_g(item, "openDate") or _g(item, "registerDate")),
                "country": "KR",
                "abstract": _g(item, "astrtCont"),
                "claims_count": 0, "citations": 0,
                "status": _parse_status(_g(item, "registerStatus")),
                "tech_field": "", "db_source": "KIPRIS",
            })
        return results, total
    except Exception:
        return [], 0

# ── 한국특허 상세정보 ────────────────────────────────────────────────────────
def get_kipris_detail(app_no, service_key):
    if not service_key or not app_no:
        return {}
    try:
        resp = requests.get(f"{KIPRIS_BASE}/getBibliographyDetailInfoSearch",
                            params={"applicationNumber": app_no, "ServiceKey": service_key},
                            timeout=15)
        if resp.status_code != 200:
            return {}
        root = ET.fromstring(resp.text)
        # 발명자
        inventors = "; ".join([
            _g(inv, "name") or _g(inv, "engName")
            for inv in root.findall(".//inventorInfo")
        ])
        # IPC
        ipc_codes = "; ".join(list(set([
            _g(i, "ipcNumber") for i in root.findall(".//ipcInfo") if _g(i, "ipcNumber")
        ])))
        # 청구항 수
        claims = root.findall(".//claimInfo")
        # 초록
        abstract = _g(root, ".//astrtCont")
        # 패밀리
        families = [_g(f, "familyApplicationNumber") for f in root.findall(".//familyInfo")]
        return {
            "inventors":    inventors,
            "ipc_codes":    ipc_codes,
            "abstract":     abstract,
            "claims_count": len(claims),
            "family":       "; ".join(families),
        }
    except Exception:
        return {}

# ── 해외특허 검색 ────────────────────────────────────────────────────────────
def search_kipris_foreign(keyword="", assignee="", ipc="", date_from="", date_to="",
                          countries=None, service_key="", page=1, num_rows=100):
    if not service_key:
        return [], 0
    if countries is None:
        countries = FOREIGN_COUNTRIES

    all_results, total = [], 0
    per_country = max(10, num_rows // len(countries))

    for country in countries:
        params = {
            "accessKey":    service_key,
            "collectionValues": country,
            "currentPage":  page,
            "numOfRows":    per_country,
            "sortField":    "AD",
            "sortState":    "true",
        }
        if keyword:  params["free"] = keyword
        if assignee: params["applicant"] = assignee
        if ipc:      params["ipc"] = ipc
        if date_from:
            params["applicationdate"] = date_from.replace("-","") if "-" in date_from else f"{date_from}0101"
        if date_to:
            end = date_to.replace("-","") if "-" in date_to else f"{date_to}1231"
            params["applicationdate"] = params.get("applicationdate","") + f"~{end}"
        try:
            resp = requests.get(FOREIGN_SEARCH, params=params, timeout=20)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.text)
            total += int(_g(root, ".//totalCount") or "0")
            for item in root.findall(".//item"):
                all_results.append({
                    "patent_number":    _g(item, "applicationNumber") or _g(item, "openNumber"),
                    "title":            _g(item, "inventionTitle"),
                    "assignee":         _g(item, "applicantName"),
                    "inventors":        "",
                    "ipc_codes":        _g(item, "ipcNumber"),
                    "application_date": _fmt_date(_g(item, "applicationDate")),
                    "publication_date": _fmt_date(_g(item, "openDate") or _g(item, "registerDate")),
                    "country":          country,
                    "abstract":         _g(item, "astrtCont"),
                    "claims_count": 0, "citations": 0,
                    "status":    _g(item, "registerStatus") or "Published",
                    "tech_field": "", "db_source": "KIPRIS_FOREIGN",
                })
        except Exception:
            continue
    return all_results, total

# ── 해외특허 상세정보 ────────────────────────────────────────────────────────
def get_foreign_detail(lit_no, country_code, service_key):
    if not service_key or not lit_no:
        return {}
    try:
        resp = requests.get(FOREIGN_DETAIL,
                            params={"literatureNumber": lit_no,
                                    "countryCode": country_code,
                                    "accessKey": service_key},
                            timeout=15)
        if resp.status_code != 200:
            return {}
        root = ET.fromstring(resp.text)
        inventors = "; ".join([
            _g(inv, "inventorName") for inv in root.findall(".//inventorsInfo")
        ])
        ipc_codes = "; ".join(list(set([
            _g(i, "ipcCd") for i in root.findall(".//ipcInfo") if _g(i, "ipcCd")
        ])))
        abstract = _g(root, ".//astrtCont")
        return {
            "inventors": inventors,
            "ipc_codes": ipc_codes or None,
            "abstract":  abstract,
        }
    except Exception:
        return {}

# ── 메인 수집 함수 ───────────────────────────────────────────────────────────
def collect_patents(keyword="", assignee="", ipc="", date_from="", date_to="",
                    databases=None, use_demo=True, kipris_key="",
                    page=1, num_rows=100, countries=None):
    if databases is None:
        databases = ["KIPRIS", "KIPRIS_FOREIGN"]
    if countries is None:
        countries = FOREIGN_COUNTRIES

    results, total_kr, total_foreign = [], 0, 0

    if not use_demo and kipris_key:
        # 한국특허
        if "KIPRIS" in databases:
            kr_list, total_kr = search_kipris_kr(
                keyword, assignee, ipc, date_from, date_to,
                service_key=kipris_key, page=page, num_rows=num_rows)
            # 상세정보 보완 (최대 50건)
            for p in kr_list[:50]:
                detail = get_kipris_detail(p["patent_number"], kipris_key)
                if detail:
                    if detail.get("inventors"):  p["inventors"]  = detail["inventors"]
                    if detail.get("ipc_codes"):  p["ipc_codes"]  = detail["ipc_codes"]
                    if detail.get("abstract"):   p["abstract"]   = detail["abstract"]
                    if detail.get("claims_count"): p["claims_count"] = detail["claims_count"]
            results.extend(kr_list)

        # 해외특허
        if "KIPRIS_FOREIGN" in databases:
            fo_list, total_foreign = search_kipris_foreign(
                keyword, assignee, ipc, date_from, date_to,
                countries=countries, service_key=kipris_key,
                page=page, num_rows=num_rows)
            # 상세정보 보완 (최대 50건)
            for p in fo_list[:50]:
                detail = get_foreign_detail(p["patent_number"], p["country"], kipris_key)
                if detail:
                    if detail.get("inventors"): p["inventors"] = detail["inventors"]
                    if detail.get("ipc_codes"): p["ipc_codes"] = detail["ipc_codes"]
                    if detail.get("abstract"):  p["abstract"]  = detail["abstract"]
            results.extend(fo_list)

        if not results:
            use_demo = True  # API 결과 없으면 데모로 폴백

    if use_demo:
        filtered = SAMPLE_PATENTS.copy()
        if keyword:
            kw = keyword.lower()
            filtered = [p for p in filtered
                        if kw in p["title"].lower() or kw in p["abstract"].lower()]
        if assignee:
            al = assignee.lower()
            filtered = [p for p in filtered if al in p["assignee"].lower()]
        if ipc:
            filtered = [p for p in filtered
                        if ipc.replace(" ","") in p["ipc_codes"].replace(" ","")]
        if databases:
            filtered = [p for p in filtered if p["db_source"] in databases]
        if date_from:
            try:
                df_dt = datetime.strptime(
                    date_from+"-01-01" if len(date_from)==4 else date_from, "%Y-%m-%d")
                filtered = [p for p in filtered
                            if datetime.strptime(p["application_date"],"%Y-%m-%d") >= df_dt]
            except: pass
        if date_to:
            try:
                dt_dt = datetime.strptime(
                    date_to+"-12-31" if len(date_to)==4 else date_to, "%Y-%m-%d")
                filtered = [p for p in filtered
                            if datetime.strptime(p["application_date"],"%Y-%m-%d") <= dt_dt]
            except: pass
        existing = {r["patent_number"] for r in results}
        for p in filtered:
            if p["patent_number"] not in existing:
                results.append(p)
        total_kr = len([p for p in results if p["country"]=="KR"])
        total_foreign = len([p for p in results if p["country"]!="KR"])

    return results, total_kr, total_foreign
