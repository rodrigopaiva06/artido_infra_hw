#!/usr/bin/env python3
"""
Analise estatistica dos dados coletados.
Calcula media, desvio-padrao, IC 95% e teste de hipotese.
"""

import csv
import math
import os
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RAW_DIR = REPO_ROOT / "dados" / "raw"
PROC_DIR = REPO_ROOT / "dados" / "processado"
PROC_DIR.mkdir(parents=True, exist_ok=True)

def media(valores):
    return sum(valores) / len(valores)

def desvio_padrao(valores):
    m = media(valores)
    return math.sqrt(sum((x - m)**2 for x in valores) / (len(valores) - 1))

def ic95(valores):
    n = len(valores)
    m = media(valores)
    s = desvio_padrao(valores)
    # t critico para 95% com n-1 graus de liberdade (aproximado para n>=30)
    t = 2.045  # t para 29 graus de liberdade, 95%
    margem = t * s / math.sqrt(n)
    return m - margem, m + margem

def teste_t_uma_amostra(valores, mu0):
    """Teste t de Student para uma amostra contra valor esperado mu0."""
    n = len(valores)
    m = media(valores)
    s = desvio_padrao(valores)
    t_stat = (m - mu0) / (s / math.sqrt(n))
    return t_stat

def carregar_csv_coluna(arquivo, coluna):
    valores = []
    with open(arquivo) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                v = float(row[coluna].replace('k', '000').replace('K', '000'))
                if v > 0:
                    valores.append(v)
            except:
                pass
    return valores

def analisar():
    resultados = {}

    # fio sequencial
    arq = RAW_DIR / "fio_sequencial.csv"
    if arq.exists():
        vals = carregar_csv_coluna(arq, "throughput_mbs")
        if vals:
            ic = ic95(vals)
            t = teste_t_uma_amostra(vals, 3500)
            resultados["fio_sequencial"] = {
                "n": len(vals),
                "media": round(media(vals), 2),
                "dp": round(desvio_padrao(vals), 2),
                "ic95_inferior": round(ic[0], 2),
                "ic95_superior": round(ic[1], 2),
                "t_stat": round(t, 3),
                "unidade": "MiB/s",
                "mu0_baremetal": 3500
            }

    # fio aleatorio IOPS
    arq = RAW_DIR / "fio_aleatorio.csv"
    if arq.exists():
        vals_iops = carregar_csv_coluna(arq, "iops")
        vals_lat = carregar_csv_coluna(arq, "latencia_us")
        if vals_iops:
            ic = ic95(vals_iops)
            resultados["fio_aleatorio_iops"] = {
                "n": len(vals_iops),
                "media": round(media(vals_iops), 2),
                "dp": round(desvio_padrao(vals_iops), 2),
                "ic95_inferior": round(ic[0], 2),
                "ic95_superior": round(ic[1], 2),
                "unidade": "IOPS"
            }
        if vals_lat:
            ic = ic95(vals_lat)
            resultados["fio_aleatorio_latencia"] = {
                "n": len(vals_lat),
                "media": round(media(vals_lat), 2),
                "dp": round(desvio_padrao(vals_lat), 2),
                "ic95_inferior": round(ic[0], 2),
                "ic95_superior": round(ic[1], 2),
                "unidade": "us"
            }

    # mbw por tamanho
    arq = RAW_DIR / "mbw.csv"
    if arq.exists():
        for tamanho in [16, 128, 1024]:
            vals = []
            with open(arq) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if int(row["array_mib"]) == tamanho:
                        try:
                            vals.append(float(row["vazao_mibs"]))
                        except:
                            pass
            if vals:
                ic = ic95(vals)
                resultados[f"mbw_{tamanho}mib"] = {
                    "n": len(vals),
                    "media": round(media(vals), 2),
                    "dp": round(desvio_padrao(vals), 2),
                    "ic95_inferior": round(ic[0], 2),
                    "ic95_superior": round(ic[1], 2),
                    "unidade": "MiB/s"
                }

    # sysbench por numero de threads
    arq = RAW_DIR / "sysbench_cpu.csv"
    if arq.exists():
        for threads in [1, 2, 4, 6, 12]:
            vals = []
            with open(arq) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if int(row["threads"]) == threads:
                        try:
                            vals.append(float(row["eventos_por_segundo"]))
                        except:
                            pass
            if vals:
                ic = ic95(vals)
                resultados[f"sysbench_{threads}t"] = {
                    "n": len(vals),
                    "media": round(media(vals), 2),
                    "dp": round(desvio_padrao(vals), 2),
                    "ic95_inferior": round(ic[0], 2),
                    "ic95_superior": round(ic[1], 2),
                    "unidade": "eventos/s"
                }

    saida = PROC_DIR / "estatisticas.json"
    with open(saida, "w") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print("=== RESULTADOS ESTATISTICOS ===")
    for nome, r in resultados.items():
        ic_str = f"[{r['ic95_inferior']}, {r['ic95_superior']}]"
        t_str = f"  t={r['t_stat']}" if 't_stat' in r else ""
        print(f"\n{nome} (n={r['n']})")
        print(f"  media={r['media']} {r['unidade']}")
        print(f"  dp={r['dp']}")
        print(f"  IC 95%: {ic_str}{t_str}")

    print(f"\nSalvo em: {saida}")
    return resultados

if __name__ == "__main__":
    analisar()
