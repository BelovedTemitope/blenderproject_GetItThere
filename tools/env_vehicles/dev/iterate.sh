#!/bin/bash
# One iteration loop for the background vehicles. Usage (from repo root):
#   tools/env_vehicles/dev/iterate.sh <work_dir> [keys...]       e.g. iterate.sh /tmp/ev A B C D
# 1) build all four into <work_dir>/ev.blend   2) dump triangles + per-triangle colour classes
# 3) render the flat-colour concept-camera view per key   4) landmark scores + zoomed blend images
# Concept masks must exist in <work_dir> (python tools/env_vehicles/ev_concept_mask.py <concept> <work_dir>).
set -e
WD=$1; shift
KEYS=${@:-A B C D}
R=$(cd "$(dirname "$0")/../../.." && pwd)
T=$R/tools/env_vehicles
PY=${PY:-/opt/bpyenv/bin/python}
CON=$R/EnvVehicles/reference/Env_Vehicles_People_Concept.webp
CAMS=${EV_CAMS:-$T/concept_cams.json}
mkdir -p $WD/r
$PY $T/ev_build.py -- $WD/ev.blend A B C D 2>&1 | grep -E "STATS|rror" || true
$PY $T/ev_dump_tris.py -- $WD/ev.blend $WD >/dev/null 2>&1
for k in $KEYS; do
  (cd $T && EV_CAMS=$CAMS $PY ev_render.py -- $WD/ev.blend $WD/r/alb $k concept --albedo 2>&1 | grep -i error || true)
  (cd $T && $PY ev_landmarks.py $CON $WD/r/alb_${k}_concept.png $WD/mask_$k.npy $CAMS $k $WD/lm_$k.png | grep -E "LANDMARK|silhouette")
  (cd $T && $PY ev_blend.py $CON $WD/r/alb_${k}_concept.png $CAMS $k $WD/bl_$k.png 3)
done
echo "landmark blends: $WD/bl_<key>.png  (left: 50/50 render over concept, right: model edges in magenta)"
