#!/usr/bin/env bash
set -euo pipefail

# Open Concert Network - venue reconstruction POC
# Input: phone/360 video or image directory
# Output: browser-ready venue.sog

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <video-or-image-directory> <work-directory>"
  exit 1
fi

INPUT="$1"
WORK_DIR="$2"
DATA_DIR="$WORK_DIR/processed"
TRAIN_DIR="$WORK_DIR/training"
EXPORT_DIR="$WORK_DIR/export"
WEB_DIR="$WORK_DIR/web"

for cmd in ns-process-data ns-train ns-export splat-transform; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Missing dependency: $cmd"
    exit 2
  }
done

mkdir -p "$DATA_DIR" "$TRAIN_DIR" "$EXPORT_DIR" "$WEB_DIR"

if [[ -d "$INPUT" ]]; then
  echo "[1/4] Processing still images with COLMAP..."
  ns-process-data images --data "$INPUT" --output-dir "$DATA_DIR"
else
  echo "[1/4] Processing video with COLMAP..."
  ns-process-data video --data "$INPUT" --output-dir "$DATA_DIR"
fi

echo "[2/4] Training Gaussian splat..."
ns-train splatfacto \
  --data "$DATA_DIR" \
  --output-dir "$TRAIN_DIR" \
  --pipeline.model.use-scale-regularization True

CONFIG="$(find "$TRAIN_DIR" -type f -name config.yml -print0 | xargs -0 ls -1t | head -n 1)"
if [[ -z "$CONFIG" ]]; then
  echo "Could not find Nerfstudio config.yml after training."
  exit 3
fi

echo "[3/4] Exporting PLY from $CONFIG..."
ns-export gaussian-splat --load-config "$CONFIG" --output-dir "$EXPORT_DIR"

PLY="$(find "$EXPORT_DIR" -type f -name '*.ply' | head -n 1)"
if [[ -z "$PLY" ]]; then
  echo "Could not find exported Gaussian-splat PLY."
  exit 4
fi

echo "[4/4] Compressing for web delivery..."
splat-transform "$PLY" "$WEB_DIR/venue.sog"

cat <<DONE

POC asset ready:
  $WEB_DIR/venue.sog

Next:
  1. Copy venue.sog into this POC folder.
  2. In splat.html change the venue asset src to ./venue.sog.
  3. Serve the folder over HTTP and open splat.html.
DONE
