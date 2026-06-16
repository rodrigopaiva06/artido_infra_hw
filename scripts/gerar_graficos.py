#!/usr/bin/env python3
"""Geração de gráficos para o artigo: benchmarking WSL2 (fio, mbw, sysbench)."""

import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

REPO = Path(__file__).parent.parent
RAW = REPO / "dados" / "raw"
OUT = REPO / "graficos"
OUT.mkdir(exist_ok=True)

DPI = 300
PAL = sns.color_palette("muted")
T29 = 2.045  # t de Student, 29 g.l., 95 %


# ── Utilitários ──────────────────────────────────────────────────────────────

def _stats(vals):
    n = len(vals)
    m = sum(vals) / n
    s = math.sqrt(sum((x - m) ** 2 for x in vals) / (n - 1))
    ci = T29 * s / math.sqrt(n)
    return m, s, ci


def _read_col(path, col):
    vals = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                v = float(row[col].replace("k", "000").replace("K", "000"))
                if v > 0:
                    vals.append(v)
            except (ValueError, KeyError):
                pass
    return vals


def _read_filtered(path, filter_col, filter_val, data_col):
    vals = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                if int(row[filter_col]) == filter_val:
                    vals.append(float(row[data_col]))
            except (ValueError, KeyError):
                pass
    return vals


# ── Figura 1: IOPS aleatório 4K com IC 95% ───────────────────────────────────

def fig1_iops():
    iops = _read_col(RAW / "fio_aleatorio.csv", "iops")
    m, s, ci = _stats(iops)
    m_k, ci_k = m / 1000, ci / 1000

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(6, 5))

    ax.bar(
        ["4K Random Read\n(iodepth=64)"],
        [m_k],
        yerr=[ci_k],
        color=PAL[0],
        width=0.35,
        capsize=12,
        error_kw=dict(elinewidth=2, ecolor="#333333"),
    )

    ax.set_ylabel("IOPS (×1 000)", fontsize=12)
    ax.set_title(
        "IOPS de Leitura Aleatória 4K — fio\n"
        "WSL2 / NVMe PCIe 4.0 ×4  |  n = 30 repetições",
        fontsize=11,
    )
    ax.set_ylim(0, (m_k + ci_k) * 1.35)

    ax.annotate(
        f"μ = {m_k:.1f}k\nIC 95 %: [{m_k - ci_k:.1f}k – {m_k + ci_k:.1f}k]\n"
        f"DP = {s/1000:.1f}k  |  CV = {s/m*100:.1f} %",
        xy=(0, m_k + ci_k),
        xytext=(0, m_k + ci_k + m_k * 0.06),
        ha="center",
        fontsize=9,
        color="#444444",
    )

    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x)}k")
    )

    sns.despine(left=False, bottom=False)
    plt.tight_layout()
    dest = OUT / "fig1_iops_fio.png"
    fig.savefig(dest, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {dest.name}")


# ── Figura 2: Largura de banda de memória (mbw) ───────────────────────────────

def fig2_mbw():
    sizes = [16, 128, 1024]
    means, cis = [], []
    for s in sizes:
        vals = _read_filtered(RAW / "mbw.csv", "array_mib", s, "vazao_mibs")
        m, _, ci = _stats(vals)
        means.append(m)
        cis.append(ci)

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(7, 5))

    ax.errorbar(
        sizes,
        means,
        yerr=cis,
        marker="o",
        linewidth=2.5,
        markersize=9,
        capsize=8,
        color=PAL[1],
        ecolor="#555555",
        elinewidth=2,
        label="Medido (WSL2)",
    )

    ax.set_xscale("log", base=2)
    ax.set_xticks(sizes)
    ax.set_xticklabels([f"{s} MiB" for s in sizes])
    ax.set_xlabel("Tamanho do Array de Cópia", fontsize=12)
    ax.set_ylabel("Vazão (MiB/s)", fontsize=12)
    ax.set_title(
        "Largura de Banda de Memória — mbw MEMCPY\n"
        "WSL2 / LPDDR4x-4266  |  n = 30 por ponto",
        fontsize=11,
    )

    for x, m, ci in zip(sizes, means, cis):
        ax.annotate(
            f"{m:.0f}",
            xy=(x, m),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="#333333",
        )

    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
    )

    sns.despine()
    plt.tight_layout()
    dest = OUT / "fig2_mbw_banda.png"
    fig.savefig(dest, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {dest.name}")


# ── Figura 3: Speedup do sysbench vs. ideal ───────────────────────────────────

def fig3_speedup():
    threads = [1, 2, 4, 6, 12]

    base_vals = _read_filtered(RAW / "sysbench_cpu.csv", "threads", 1, "eventos_por_segundo")
    base = sum(base_vals) / len(base_vals)

    speedups, cis_sp = [], []
    for t in threads:
        vals = _read_filtered(RAW / "sysbench_cpu.csv", "threads", t, "eventos_por_segundo")
        m, _, ci = _stats(vals)
        speedups.append(m / base)
        cis_sp.append(ci / base)

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(7, 5))

    ax.plot(
        threads,
        threads,
        "--",
        color="#aaaaaa",
        linewidth=1.8,
        label="Speedup Ideal (linear)",
        zorder=1,
    )
    ax.errorbar(
        threads,
        speedups,
        yerr=cis_sp,
        marker="s",
        linewidth=2.5,
        markersize=9,
        capsize=8,
        color=PAL[2],
        ecolor="#555555",
        elinewidth=2,
        label="Speedup Real (WSL2)",
        zorder=2,
    )

    for t, sp in zip(threads, speedups):
        ax.annotate(
            f"{sp:.2f}×",
            xy=(t, sp),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=9,
            color="#333333",
        )

    ax.set_xticks(threads)
    ax.set_xlabel("Número de Threads", fontsize=12)
    ax.set_ylabel("Speedup (relativo a 1 thread)", fontsize=12)
    ax.set_title(
        "Speedup de CPU: Observado vs. Ideal — sysbench prime\n"
        "WSL2 / i5-1235U (2P + 8E)  |  n = 30 por ponto",
        fontsize=11,
    )
    ax.legend(fontsize=10)

    sns.despine()
    plt.tight_layout()
    dest = OUT / "fig3_speedup_cpu.png"
    fig.savefig(dest, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {dest.name}")


# ── Figura 4: Eficiência (%) por número de threads ────────────────────────────

def fig4_eficiencia():
    threads = [1, 2, 4, 6, 12]

    base_vals = _read_filtered(RAW / "sysbench_cpu.csv", "threads", 1, "eventos_por_segundo")
    base = sum(base_vals) / len(base_vals)

    efics = []
    for t in threads:
        vals = _read_filtered(RAW / "sysbench_cpu.csv", "threads", t, "eventos_por_segundo")
        m = sum(vals) / len(vals)
        efics.append((m / base) / t * 100)

    colors = [PAL[0] if e >= 80 else PAL[3] for e in efics]

    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(7, 5))

    bars = ax.bar(
        [str(t) for t in threads],
        efics,
        color=colors,
        width=0.5,
        edgecolor="white",
        linewidth=0.8,
    )
    ax.axhline(
        100,
        linestyle="--",
        color="#aaaaaa",
        linewidth=1.8,
        label="Eficiência Ideal (100 %)",
    )

    ax.set_ylim(0, 118)
    ax.set_xlabel("Número de Threads", fontsize=12)
    ax.set_ylabel("Eficiência (%)", fontsize=12)
    ax.set_title(
        "Eficiência de Paralelismo — sysbench prime\n"
        "Eficiência = Speedup Real ÷ Speedup Ideal × 100",
        fontsize=11,
    )
    ax.legend(fontsize=10)

    for bar, e in zip(bars, efics):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            e + 2,
            f"{e:.1f} %",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
        )

    sns.despine()
    plt.tight_layout()
    dest = OUT / "fig4_eficiencia_cpu.png"
    fig.savefig(dest, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {dest.name}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Gerando gráficos em {OUT} ...")
    fig1_iops()
    fig2_mbw()
    fig3_speedup()
    fig4_eficiencia()
    print(f"\n4 figuras salvas em 300 DPI → {OUT}")
