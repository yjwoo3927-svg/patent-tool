"""
특허지도 생성 모듈
- 연도별 출원 추이 차트
- 출원인별 기술 분포 버블차트
- IPC 코드 기반 기술 분류 히트맵
- 출원인-IPC 네트워크 맵
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.patheffects as pe
import numpy as np
from collections import Counter, defaultdict
import os

# 한글 폰트 설정
import glob
import matplotlib.font_manager as _fm
_ko_fonts = glob.glob("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc") + \
            glob.glob("/usr/share/fonts/opentype/noto/NotoSansCJK*.ttc")
if _ko_fonts:
    _fm._load_fontmanager(try_read_cache=False)
    _fm.fontManager.addfont(_ko_fonts[0])
    _prop = _fm.FontProperties(fname=_ko_fonts[0])
    plt.rcParams["font.family"] = _prop.get_name()
else:
    plt.rcParams["font.family"] = "DejaVu Sans"

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "#F8FAFB"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.4
plt.rcParams["grid.linestyle"] = "--"
plt.rcParams["grid.color"] = "#CCCCCC"

PALETTE = ["#1D9E75", "#378ADD", "#7F77DD", "#D85A30", "#BA7517",
           "#D4537E", "#639922", "#1A3A5C", "#E24B4A", "#0F6E56"]

COUNTRY_FULL = {
    "KR": "한국", "US": "미국", "EP": "유럽", "WO": "국제(PCT)",
    "CN": "중국", "JP": "일본"
}


def _year(date_str):
    try:
        return int(date_str[:4])
    except:
        return None


def create_patent_map(patents: list, output_path: str) -> str:
    fig = plt.figure(figsize=(20, 24))
    fig.patch.set_facecolor("white")
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35,
                           top=0.93, bottom=0.05, left=0.08, right=0.97)

    # 제목
    fig.text(0.5, 0.965, "특허 · 선행기술 기술 지도 (Patent Map)",
             ha="center", va="center", fontsize=20, fontweight="bold",
             color="#1A3A5C")
    fig.text(0.5, 0.948, f"수집 특허 수: {len(patents)}건  |  분석 기준: 출원일, 출원인, IPC 코드",
             ha="center", va="center", fontsize=11, color="#556677")

    # ── 차트 1: 연도별 출원 추이 (국가별 스택) ───────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    years_all = sorted(set(y for p in patents if (y := _year(p["application_date"]))))
    countries = sorted(set(p["country"] for p in patents))

    year_country = defaultdict(Counter)
    for p in patents:
        yr = _year(p["application_date"])
        if yr:
            year_country[yr][p["country"]] += 1

    if years_all:
        x = np.arange(len(years_all))
        bottom = np.zeros(len(years_all))
        for ci, country in enumerate(countries):
            vals = [year_country[y].get(country, 0) for y in years_all]
            bars = ax1.bar(x, vals, bottom=bottom, label=COUNTRY_FULL.get(country, country),
                           color=PALETTE[ci % len(PALETTE)], alpha=0.88, width=0.65,
                           edgecolor="white", linewidth=0.8)
            for bar, val in zip(bars, vals):
                if val > 0:
                    ax1.text(bar.get_x() + bar.get_width() / 2,
                             bar.get_y() + bar.get_height() / 2,
                             str(val), ha="center", va="center",
                             fontsize=9, color="white", fontweight="bold")
            bottom += np.array(vals)

        ax1.set_xticks(x)
        ax1.set_xticklabels([str(y) for y in years_all], fontsize=10)
        ax1.set_xlabel("출원 연도", fontsize=11, labelpad=8)
        ax1.set_ylabel("출원 건수", fontsize=11, labelpad=8)
        ax1.set_title("① 연도별 특허 출원 추이 (국가별)", fontsize=13, fontweight="bold",
                       color="#1A3A5C", pad=12)
        ax1.legend(loc="upper left", fontsize=9, framealpha=0.9)
        ax1.set_facecolor("#F8FAFB")

    # ── 차트 2: 출원인별 버블 차트 ───────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    assignee_cnt = Counter(p["assignee"] for p in patents)
    assignee_cite = defaultdict(int)
    for p in patents:
        assignee_cite[p["assignee"]] += p.get("citations", 0)

    top_assignees = [a for a, _ in assignee_cnt.most_common(10)]
    x_vals = [assignee_cnt[a] for a in top_assignees]
    y_vals = [assignee_cite[a] for a in top_assignees]
    sizes = [max(200, x * 180) for x in x_vals]

    sc = ax2.scatter(x_vals, y_vals, s=sizes, c=PALETTE[:len(top_assignees)],
                     alpha=0.75, edgecolors="white", linewidths=1.5, zorder=3)

    for i, name in enumerate(top_assignees):
        short = name[:12] + "…" if len(name) > 12 else name
        ax2.annotate(short, (x_vals[i], y_vals[i]),
                     textcoords="offset points", xytext=(8, 4),
                     fontsize=8, color="#334455", zorder=4)

    ax2.set_xlabel("보유 특허 수", fontsize=10, labelpad=6)
    ax2.set_ylabel("총 피인용 수", fontsize=10, labelpad=6)
    ax2.set_title("② 출원인별 특허 포트폴리오\n(버블 크기 = 특허 수)", fontsize=12,
                   fontweight="bold", color="#1A3A5C", pad=10)
    ax2.set_facecolor("#F8FAFB")

    # ── 차트 3: IPC 코드 분포 ──────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    ipc_cnt = Counter()
    for p in patents:
        for code in p.get("ipc_codes", "").split(";"):
            main = code.strip()[:7]
            if main:
                ipc_cnt[main] += 1

    if ipc_cnt:
        top_ipc = ipc_cnt.most_common(10)
        labels = [c for c, _ in top_ipc]
        values = [v for _, v in top_ipc]

        bars = ax3.barh(range(len(labels)), values, color=PALETTE[:len(labels)],
                        alpha=0.85, edgecolor="white", height=0.65)
        ax3.set_yticks(range(len(labels)))
        ax3.set_yticklabels(labels, fontsize=9)
        ax3.set_xlabel("특허 건수", fontsize=10, labelpad=6)
        ax3.set_title("③ IPC 코드별 기술 분류 분포 (Top 10)", fontsize=12,
                       fontweight="bold", color="#1A3A5C", pad=10)
        ax3.invert_yaxis()
        ax3.set_facecolor("#F8FAFB")

        for bar, val in zip(bars, values):
            ax3.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                     str(val), va="center", fontsize=9, color="#334455")

    # ── 차트 4: 출원인 × IPC 히트맵 ──────────────────────────────────────
    ax4 = fig.add_subplot(gs[2, :])
    top5_assignees = [a for a, _ in assignee_cnt.most_common(8)]
    top5_ipc = [c for c, _ in ipc_cnt.most_common(8)] if ipc_cnt else []

    if top5_assignees and top5_ipc:
        matrix = np.zeros((len(top5_assignees), len(top5_ipc)))
        for p in patents:
            if p["assignee"] in top5_assignees:
                ai = top5_assignees.index(p["assignee"])
                for code in p.get("ipc_codes", "").split(";"):
                    main = code.strip()[:7]
                    if main in top5_ipc:
                        ci = top5_ipc.index(main)
                        matrix[ai, ci] += 1

        im = ax4.imshow(matrix, aspect="auto", cmap="YlGn", alpha=0.9)
        ax4.set_xticks(range(len(top5_ipc)))
        ax4.set_xticklabels(top5_ipc, fontsize=9, rotation=30, ha="right")
        ax4.set_yticks(range(len(top5_assignees)))

        short_names = [a[:15] + "…" if len(a) > 15 else a for a in top5_assignees]
        ax4.set_yticklabels(short_names, fontsize=9)
        ax4.set_title("④ 출원인 × IPC 코드 기술 분포 히트맵", fontsize=13,
                       fontweight="bold", color="#1A3A5C", pad=12)
        ax4.set_xlabel("IPC 코드", fontsize=10, labelpad=6)
        ax4.set_ylabel("출원인", fontsize=10, labelpad=6)

        for i in range(len(top5_assignees)):
            for j in range(len(top5_ipc)):
                val = int(matrix[i, j])
                if val > 0:
                    ax4.text(j, i, str(val), ha="center", va="center",
                             fontsize=11, fontweight="bold",
                             color="white" if val >= matrix.max() * 0.6 else "#1A3A5C")

        plt.colorbar(im, ax=ax4, shrink=0.6, label="특허 건수")
        ax4.set_facecolor("#F8FAFB")

    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    return output_path
