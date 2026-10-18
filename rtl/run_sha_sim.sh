#!/bin/bash
# Bit-exact check of the SHA-256 cores against sha256_ref.py vectors. Run from WSL.
set -e
cd "$(dirname "$0")"
if command -v iverilog >/dev/null; then IV=iverilog; VVP=vvp; IVB=; VVM=
else
    R=~/iverilog-local/root; L=$R/usr/lib/x86_64-linux-gnu
    export LD_LIBRARY_PATH=$L
    IV=$R/usr/bin/iverilog; VVP=$R/usr/bin/vvp; IVB=-B$L/ivl; VVM=-M$L/ivl
fi
SW=../third_party/secworks_sha256/src/rtl
run() {  # core, vector file, extra sources
    echo "== $1 on $2"
    $IV $IVB -g2005 -DDUT=$1 -P tb_sha256.TEST_FILE=\"../out/$2\" -o /tmp/sim_$1 tb_sha256.v $1.v ${@:3}
    $VVP $VVM /tmp/sim_$1 | grep -E "vectors=|RESULT|MISMATCH"
}
run sha256_iter sha256_vectors.mem
run sha256_iter sha256_chain_vectors.mem
run sha256_lite sha256_vectors.mem
run sha256_lite sha256_chain_vectors.mem
run sha256_secworks sha256_chain_vectors.mem $SW/sha256_core.v $SW/sha256_k_constants.v $SW/sha256_w_mem.v
