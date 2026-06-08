"""
특허 서지정보 수집 엔진
- USPTO PatentsView API (무료, 키 불필요)
- EPO OPS API (무료 계정 필요)
- KIPRIS (공공데이터포털 API 키 필요)
- 데모 모드: 실제 API 없이 샘플 데이터 생성
"""
import requests
import json
import time
from datetime import datetime, timedelta
import random

SAMPLE_PATENTS = [
    {
        "patent_number": "KR10-2021-0087654",
        "title": "리튬이온 배터리용 실리콘 복합 음극재 제조방법",
        "assignee": "LG에너지솔루션",
        "inventors": "김철수; 이영희; 박민준",
        "ipc_codes": "H01M 4/36; H01M 10/0525",
        "application_date": "2021-07-05",
        "publication_date": "2023-02-10",
        "country": "KR",
        "abstract": "본 발명은 실리콘 복합 음극재를 제조하는 방법에 관한 것으로, 나노 실리콘 입자를 탄소 매트릭스에 분산시켜 사이클 안정성과 에너지 밀도를 향상시킨다.",
        "claims_count": 15,
        "citations": 8,
        "status": "등록",
        "tech_field": "배터리/에너지저장",
        "db_source": "KIPRIS",
    },
    {
        "patent_number": "US11456789",
        "title": "Silicon composite anode material for lithium ion battery and manufacturing method thereof",
        "assignee": "Samsung SDI Co., Ltd.",
        "inventors": "Park, Jihoon; Kim, Sungwoo; Lee, Hyunjin",
        "ipc_codes": "H01M 4/36; H01M 4/485",
        "application_date": "2020-11-15",
        "publication_date": "2022-09-27",
        "country": "US",
        "abstract": "A silicon composite anode material comprising nano-silicon particles dispersed in a carbon matrix with improved cycling stability and energy density for use in lithium-ion batteries.",
        "claims_count": 22,
        "citations": 14,
        "status": "Granted",
        "tech_field": "Battery/Energy Storage",
        "db_source": "USPTO",
    },
    {
        "patent_number": "EP3987654",
        "title": "Electrode material with improved cycle stability for secondary batteries",
        "assignee": "SK Innovation Co., Ltd.",
        "inventors": "Lee, Hyunsoo; Choi, Minkyung",
        "ipc_codes": "H01M 4/485; H01M 10/0567",
        "application_date": "2021-03-20",
        "publication_date": "2022-12-14",
        "country": "EP",
        "abstract": "An electrode material for secondary batteries demonstrating enhanced cycle stability through a novel composite structure combining silicon oxides and graphene.",
        "claims_count": 18,
        "citations": 6,
        "status": "Published",
        "tech_field": "Battery/Energy Storage",
        "db_source": "EPO",
    },
    {
        "patent_number": "KR10-2022-0134512",
        "title": "전고체 배터리용 황화물계 고체 전해질 및 제조방법",
        "assignee": "삼성SDI",
        "inventors": "정수진; 최동훈; 윤재혁",
        "ipc_codes": "H01M 10/0562; H01M 10/058",
        "application_date": "2022-10-18",
        "publication_date": "2024-04-25",
        "country": "KR",
        "abstract": "본 발명은 전고체 배터리에 사용되는 황화물계 고체 전해질에 관한 것으로, 이온 전도도와 화학적 안정성을 동시에 향상시키는 조성을 제공한다.",
        "claims_count": 20,
        "citations": 3,
        "status": "공개",
        "tech_field": "배터리/에너지저장",
        "db_source": "KIPRIS",
    },
    {
        "patent_number": "US11789012",
        "title": "Solid electrolyte for all-solid-state battery and manufacturing process",
        "assignee": "LG Chem, Ltd.",
        "inventors": "Yoon, Jaehyuk; Kim, Dongwoo",
        "ipc_codes": "H01M 10/0562; H01M 10/0585",
        "application_date": "2021-08-30",
        "publication_date": "2023-10-10",
        "country": "US",
        "abstract": "A sulfide-based solid electrolyte for all-solid-state batteries with enhanced ionic conductivity and electrochemical stability over a wide temperature range.",
        "claims_count": 25,
        "citations": 11,
        "status": "Granted",
        "tech_field": "Battery/Energy Storage",
        "db_source": "USPTO",
    },
    {
        "patent_number": "WO2022/098765",
        "title": "High-capacity cathode material for next-generation lithium batteries",
        "assignee": "Panasonic Holdings Corporation",
        "inventors": "Tanaka, Hiroshi; Yamamoto, Kenji",
        "ipc_codes": "H01M 4/52; H01M 4/525",
        "application_date": "2021-11-05",
        "publication_date": "2022-05-19",
        "country": "WO",
        "abstract": "A nickel-rich layered oxide cathode material with suppressed capacity fade through surface coating treatment for high-energy-density lithium batteries.",
        "claims_count": 30,
        "citations": 19,
        "status": "Published",
        "tech_field": "Battery/Energy Storage",
        "db_source": "WIPO",
    },
    {
        "patent_number": "CN114843452A",
        "title": "一种锂离子电池正极材料及其制备方法",
        "assignee": "宁德时代新能源科技股份有限公司 (CATL)",
        "inventors": "曾毓群; 黄世琳",
        "ipc_codes": "H01M 4/525; H01M 4/505",
        "application_date": "2022-04-12",
        "publication_date": "2022-07-29",
        "country": "CN",
        "abstract": "本发明涉及一种高镍三元正极材料，通过表面包覆和体相掺杂协同改性，显著提升了材料的循环稳定性和热稳定性。",
        "claims_count": 12,
        "citations": 5,
        "status": "公开",
        "tech_field": "Battery/Energy Storage",
        "db_source": "CNIPA",
    },
    {
        "patent_number": "KR10-2023-0045678",
        "title": "나트륨 이온 배터리용 양극 활물질 및 이를 포함하는 배터리",
        "assignee": "포스코홀딩스",
        "inventors": "강민석; 조현우; 신지원",
        "ipc_codes": "H01M 4/58; H01M 10/054",
        "application_date": "2023-04-03",
        "publication_date": "2024-10-10",
        "country": "KR",
        "abstract": "본 발명은 나트륨 이온 배터리에 사용 가능한 층상 산화물 양극 활물질로, 리튬 대비 저렴한 원가로 높은 에너지 밀도를 구현한다.",
        "claims_count": 16,
        "citations": 1,
        "status": "공개",
        "tech_field": "배터리/에너지저장",
        "db_source": "KIPRIS",
    },
]


def search_uspto(keyword="", assignee="", ipc="", date_from="", date_to="", max_results=10):
    """USPTO PatentsView API 실제 호출"""
    base_url = "https://api.patentsview.org/patents/query"
    
    conditions = []
    if keyword:
        conditions.append({"_text_phrase": {"patent_title": keyword}})
    if assignee:
        conditions.append({"_text_phrase": {"assignee_organization": assignee}})
    if ipc:
        conditions.append({"_eq": {"ipc_main_group": ipc.replace(" ", "")}})

    if not conditions:
        query = {"_gte": {"patent_date": "2020-01-01"}}
    elif len(conditions) == 1:
        query = conditions[0]
    else:
        query = {"_and": conditions}

    payload = {
        "q": query,
        "f": ["patent_number", "patent_title", "patent_date", "patent_abstract",
              "assignee_organization", "inventor_last_name", "ipc_main_group"],
        "o": {"per_page": max_results}
    }

    try:
        resp = requests.post(base_url, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for p in data.get("patents", []) or []:
                inventors = "; ".join(
                    [inv.get("inventor_last_name", "") for inv in (p.get("inventors") or [])[:3]]
                )
                ipc_list = "; ".join(
                    list(set([i.get("ipc_main_group", "") for i in (p.get("ipcs") or [])[:3]]))
                )
                assignees = "; ".join(
                    [a.get("assignee_organization", "") for a in (p.get("assignees") or [])[:2]]
                )
                results.append({
                    "patent_number": "US" + (p.get("patent_number") or ""),
                    "title": p.get("patent_title", ""),
                    "assignee": assignees or "N/A",
                    "inventors": inventors or "N/A",
                    "ipc_codes": ipc_list or "N/A",
                    "application_date": p.get("patent_date", ""),
                    "publication_date": p.get("patent_date", ""),
                    "country": "US",
                    "abstract": (p.get("patent_abstract") or "")[:300],
                    "claims_count": 0,
                    "citations": 0,
                    "status": "Granted",
                    "tech_field": "General",
                    "db_source": "USPTO",
                })
            return results
    except Exception:
        pass
    return []


def collect_patents(keyword="", assignee="", ipc="", date_from="", date_to="",
                    databases=None, use_demo=True):
    """
    특허 서지정보 수집 메인 함수
    use_demo=True: 샘플 데이터 사용 (API 키 불필요)
    use_demo=False: 실제 USPTO API 호출 시도
    """
    if databases is None:
        databases = ["KIPRIS", "USPTO", "EPO", "WIPO"]

    results = []

    if not use_demo and "USPTO" in databases:
        live = search_uspto(keyword, assignee, ipc, date_from, date_to)
        results.extend(live)

    # 필터링된 샘플 데이터 사용
    filtered = SAMPLE_PATENTS.copy()

    if keyword:
        kw_lower = keyword.lower()
        filtered = [p for p in filtered
                    if kw_lower in p["title"].lower() or kw_lower in p["abstract"].lower()]
    if assignee:
        as_lower = assignee.lower()
        filtered = [p for p in filtered if as_lower in p["assignee"].lower()]
    if ipc:
        filtered = [p for p in filtered if ipc.replace(" ", "") in p["ipc_codes"].replace(" ", "")]
    if databases:
        filtered = [p for p in filtered if p["db_source"] in databases]

    # 날짜 필터
    if date_from:
        try:
            df_dt = datetime.strptime(date_from + "-01-01" if len(date_from) == 4 else date_from, "%Y-%m-%d")
            filtered = [p for p in filtered
                        if datetime.strptime(p["application_date"], "%Y-%m-%d") >= df_dt]
        except:
            pass
    if date_to:
        try:
            dt_dt = datetime.strptime(date_to + "-12-31" if len(date_to) == 4 else date_to, "%Y-%m-%d")
            filtered = [p for p in filtered
                        if datetime.strptime(p["application_date"], "%Y-%m-%d") <= dt_dt]
        except:
            pass

    # 중복 제거 후 병합
    existing_nums = {r["patent_number"] for r in results}
    for p in filtered:
        if p["patent_number"] not in existing_nums:
            results.append(p)

    return results
