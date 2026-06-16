# Avaliação de Desempenho de Subsistemas de I/O, Memória e CPU em Ambiente Virtualizado (WSL2)

**Autor:** Rodrigo Paiva  
**Disciplina:** Infraestrutura de Hardware  
**Instituição:** [Nome da Instituição]

---

## Pergunta de Pesquisa

> O ambiente de virtualização WSL2 (Windows Subsystem for Linux 2) impõe overhead mensurável no desempenho dos subsistemas de armazenamento (I/O aleatório), largura de banda de memória e capacidade de processamento paralelo da CPU, em comparação com as especificações nominais do hardware bare-metal?

---

## Hipóteses

| # | Hipótese | Métrica | Ferramenta |
|---|----------|---------|------------|
| H1 | O I/O aleatório 4K em WSL2 apresentará IOPS médios abaixo de 250 000 e alta variabilidade (CV > 10 %), refletindo overhead da camada de virtualização | IOPS e latência média (µs) | `fio` |
| H2 | A largura de banda de memória será semelhante entre arrays de 128 MiB e 1 024 MiB, indicando que o subsistema de cache não beneficia acessos maiores que a LLC em WSL2 | Vazão em MiB/s | `mbw` |
| H3 | O ganho de desempenho da CPU escala de forma sub-linear a partir de 6 threads, sugerindo saturação dos núcleos físicos antes do limite de hyperthreading | Eventos/segundo | `sysbench` |

---

## Hardware e Ambiente

| Componente | Especificação |
|------------|---------------|
| CPU | Intel Core i5 (6 núcleos / 12 threads) |
| Memória RAM | 16 GB DDR4 |
| Armazenamento | SSD NVMe (PCIe) |
| Sistema Operacional Host | Windows 11 |
| Ambiente de Execução | WSL2 (Ubuntu 22.04) |
| Kernel WSL2 | 5.15.x |

---

## Resultados Resumidos (n = 30 repetições, IC 95 %)

### I/O Aleatório — `fio` (4K randread, iodepth=64)

| Métrica | Média | DP | IC 95 % |
|---------|-------|----|---------|
| IOPS | 191 733 | 26 333 | [181 901 — 201 565] |
| Latência (µs) | 337,51 | 58,44 | [315,69 — 359,33] |

### Largura de Banda de Memória — `mbw` (MEMCPY)

| Array | Média (MiB/s) | DP | IC 95 % |
|-------|---------------|----|---------|
| 16 MiB | 3 536,23 | 311,05 | [3 420,10 — 3 652,37] |
| 128 MiB | 4 171,61 | 540,68 | [3 969,74 — 4 373,49] |
| 1 024 MiB | 4 142,94 | 983,91 | [3 775,59 — 4 510,30] |

### Paralelismo de CPU — `sysbench` (prime, 5 s)

| Threads | Média (eventos/s) | DP | IC 95 % |
|---------|-------------------|----|---------|
| 1 | 2 029,30 | 86,18 | [1 997,13 — 2 061,48] |
| 2 | 3 507,81 | 163,18 | [3 446,89 — 3 568,74] |
| 4 | 6 929,24 | 565,22 | [6 718,21 — 7 140,28] |
| 6 | 10 358,77 | 529,78 | [10 160,97 — 10 556,57] |
| 12 | 16 079,19 | 696,45 | [15 819,17 — 16 339,22] |

---

## Como Reproduzir

### Pré-requisitos

```bash
# Ubuntu/Debian (WSL2 ou bare-metal)
sudo apt update
sudo apt install -y fio mbw sysbench python3
```

### 1. Clonar o repositório

```bash
git clone https://github.com/rodrigopaiva06/artido_infra_hw.git
cd artido_infra_hw
```

### 2. Executar a coleta (≈ 2 h)

```bash
chmod +x scripts/coleta_30x.sh
sudo scripts/coleta_30x.sh
```

Os CSVs são salvos automaticamente em `dados/raw/`.

### 3. Calcular as estatísticas

```bash
python3 scripts/analise_estatistica.py
```

O resultado é salvo em `dados/processado/estatisticas.json` e impresso no terminal.

---

## Estrutura do Repositório

```
artido_infra_hw/
├── artigo/                        # Texto do artigo (PDF / LaTeX)
├── dados/
│   ├── raw/                       # Dados brutos coletados
│   │   ├── fio_aleatorio.csv      # IOPS e latência (30 repetições)
│   │   ├── mbw.csv                # Largura de banda de memória (3 tamanhos × 30)
│   │   └── sysbench_cpu.csv       # CPU paralelismo (5 configs × 30)
│   └── processado/
│       └── estatisticas.json      # Média, DP e IC 95 % por experimento
├── scripts/
│   ├── coleta_30x.sh              # Coleta automatizada com warmup de 3 runs
│   └── analise_estatistica.py     # Análise estatística (Python puro, sem dependências)
└── README.md
```

---

## Metodologia

- **Repetições:** 30 por configuração, precedidas de 3 execuções de aquecimento (descartadas).
- **Controle de estado:** swap desativado (`swapoff -a`), governor de CPU fixado em `performance` durante toda a coleta.
- **Intervalo de confiança:** t de Student com 29 graus de liberdade (t = 2,045 para 95 %).
- **Análise:** implementada em Python puro (sem NumPy/SciPy) para máxima reprodutibilidade.
