#!/bin/bash
# Script de coleta de dados - 30 repeticoes por experimento
# Infraestrutura de Hardware - Rodrigo Paiva

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="$REPO_ROOT/dados/raw"
mkdir -p "$OUTDIR"

REPETICOES=30
WARMUP=3  # primeiras execucoes descartadas

echo "============================================"
echo "COLETA DE DADOS - 30 repeticoes"
echo "Iniciado em: $(date)"
echo "============================================"

echo "Configurando estado do sistema..."
sudo swapoff -a 2>/dev/null || true
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
sleep 2

# ----------------------------
# EXPERIMENTO 1: fio sequencial (leitura 1M)
# ----------------------------
echo ""
echo "[1/4] fio - leitura sequencial 1M..."
FIO_SEQ="$OUTDIR/fio_sequencial.csv"
echo "run,throughput_mbs" > "$FIO_SEQ"

TOTAL=$((REPETICOES + WARMUP))
for i in $(seq 1 $TOTAL); do
  VAL=$(fio --name=seqread --rw=read --bs=1M --filename=/tmp/fio-test \
    --direct=1 --ioengine=libaio --iodepth=32 --size=1G \
    --time_based --runtime=5 --group_reporting 2>/dev/null \
    | grep "READ:" | grep -oP 'BW=\K[0-9.]+(?=MiB/s)')
  if [ $i -gt $WARMUP ]; then
    RUN=$((i - WARMUP))
    echo "$RUN,$VAL" >> "$FIO_SEQ"
    echo "  seq run $RUN/$REPETICOES: $VAL MiB/s"
  else
    echo "  warmup $i/$WARMUP descartado"
  fi
done

# ----------------------------
# EXPERIMENTO 2: fio aleatorio 4k
# ----------------------------
echo ""
echo "[2/4] fio - leitura aleatoria 4k..."
FIO_RAND="$OUTDIR/fio_aleatorio.csv"
echo "run,iops,latencia_us" > "$FIO_RAND"

for i in $(seq 1 $TOTAL); do
  OUTPUT=$(fio --name=randread --rw=randread --bs=4k --filename=/tmp/fio-test \
    --direct=1 --ioengine=libaio --iodepth=64 \
    --time_based --runtime=5 --group_reporting 2>/dev/null)
  IOPS=$(echo "$OUTPUT" | grep "read:" | grep -oP 'IOPS=\K[0-9.k]+' | head -1)
  LAT=$(echo "$OUTPUT" | grep "lat (usec)" | grep -oP 'avg=\K[0-9.]+' | head -1)
  if [ $i -gt $WARMUP ]; then
    RUN=$((i - WARMUP))
    echo "$RUN,$IOPS,$LAT" >> "$FIO_RAND"
    echo "  rand run $RUN/$REPETICOES: $IOPS IOPS / $LAT us"
  else
    echo "  warmup $i/$WARMUP descartado"
  fi
done

# ----------------------------
# EXPERIMENTO 3: mbw - largura de banda de memoria
# ----------------------------
echo ""
echo "[3/4] mbw - largura de banda de memoria..."
MBW_FILE="$OUTDIR/mbw.csv"
echo "run,array_mib,vazao_mibs" > "$MBW_FILE"

for TAMANHO in 16 128 1024; do
  echo "  array: ${TAMANHO} MiB"
  for i in $(seq 1 $TOTAL); do
    VAL=$(mbw -t0 -n 1 $TAMANHO 2>/dev/null | grep "AVG" | grep -oP 'Copy:\s+\K[0-9.]+')
    if [ $i -gt $WARMUP ]; then
      RUN=$((i - WARMUP))
      echo "$RUN,$TAMANHO,$VAL" >> "$MBW_FILE"
    fi
  done
done
echo "  mbw concluido"

# ----------------------------
# EXPERIMENTO 4: paralelismo (sysbench)
# ----------------------------
echo ""
echo "[4/4] sysbench - CPU paralelismo..."
SYS_FILE="$OUTDIR/sysbench_cpu.csv"
echo "run,threads,eventos_por_segundo" > "$SYS_FILE"

for THREADS in 1 2 4 6 12; do
  echo "  threads: $THREADS"
  for i in $(seq 1 $TOTAL); do
    VAL=$(sysbench cpu --threads=$THREADS --time=5 run 2>/dev/null \
      | grep "events per second" | grep -oP '[0-9.]+$')
    if [ $i -gt $WARMUP ]; then
      RUN=$((i - WARMUP))
      echo "$RUN,$THREADS,$VAL" >> "$SYS_FILE"
    fi
  done
done

echo ""
echo "============================================"
echo "Coleta concluida em: $(date)"
echo "Arquivos salvos em: $OUTDIR"
ls -lh "$OUTDIR"
echo "============================================"

sudo swapon -a 2>/dev/null || true
