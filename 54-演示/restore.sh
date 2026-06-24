#!/usr/bin/env bash
#
# restore.sh — 一键还原被拆分的视频文件
#
# 用法: bash restore.sh
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR ]${NC} $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 读取元信息 ──
if [[ ! -f "metadata.txt" ]]; then
    err "未找到 metadata.txt，请确保在正确的目录中运行"
    exit 1
fi

ORIGINAL_FILENAME=$(grep '^original_filename=' metadata.txt | cut -d= -f2)
ORIGINAL_SIZE=$(grep '^original_size=' metadata.txt | cut -d= -f2)
ORIGINAL_HASH=$(grep '^original_sha256=' metadata.txt | cut -d= -f2)
TOTAL_CHUNKS=$(grep '^total_chunks=' metadata.txt | cut -d= -f2)

ORIGINAL_SIZE_MB=$((ORIGINAL_SIZE / 1024 / 1024))

echo ""
info "========================================="
info "  视频文件一键还原"
info "========================================="
echo ""
info "原始文件:   $ORIGINAL_FILENAME"
info "原始大小:   ${ORIGINAL_SIZE_MB}MB ($ORIGINAL_SIZE bytes)"
info "总块数:     $TOTAL_CHUNKS"
echo ""

# ── 检查所有块是否存在 ──
BASENAME="${ORIGINAL_FILENAME%.*}"
MISSING=0
for i in $(seq -w 0 $((TOTAL_CHUNKS - 1))); do
    # 补齐为3位
    PADDED=$(printf "%03d" "$((10#$i))")
    CHUNK_NAME="${BASENAME}.part_${PADDED}"
    if [[ ! -f "$CHUNK_NAME" ]]; then
        err "缺失块: $CHUNK_NAME"
        MISSING=$((MISSING + 1))
    fi
done

if [[ $MISSING -gt 0 ]]; then
    err "共缺失 $MISSING 个块，无法还原"
    exit 1
fi
ok "所有 $TOTAL_CHUNKS 个块均已找到"
echo ""

# ── 验证各块校验和 ──
if [[ -f "checksums.sha256" ]]; then
    info "正在验证各块校验和..."
    HASH_OK=true
    if command -v sha256sum &>/dev/null; then
        if ! sha256sum -c checksums.sha256 --quiet 2>/dev/null; then
            HASH_OK=false
        fi
    elif command -v shasum &>/dev/null; then
        if ! shasum -a 256 -c checksums.sha256 --quiet 2>/dev/null; then
            HASH_OK=false
        fi
    else
        warn "未找到校验工具，跳过块校验"
    fi

    if [[ "$HASH_OK" == true ]]; then
        ok "所有块校验和验证通过"
    else
        err "块校验和验证失败！文件可能已损坏"
        read -rp "是否继续还原？(y/N): " CONTINUE
        if [[ "$CONTINUE" != "y" && "$CONTINUE" != "Y" ]]; then
            exit 1
        fi
    fi
else
    warn "未找到 checksums.sha256，跳过块校验"
fi
echo ""

# ── 合并文件 ──
OUTPUT_FILE="../$ORIGINAL_FILENAME"

# 如果目标文件已存在，询问是否覆盖
if [[ -f "$OUTPUT_FILE" ]]; then
    warn "文件已存在: $OUTPUT_FILE"
    read -rp "是否覆盖？(y/N): " OVERWRITE
    if [[ "$OVERWRITE" != "y" && "$OVERWRITE" != "Y" ]]; then
        info "操作取消"
        exit 0
    fi
fi

info "正在合并文件..."
cat $(ls -1 "${BASENAME}.part_"* | sort) > "$OUTPUT_FILE"
ok "文件合并完成: $OUTPUT_FILE"
echo ""

# ── 验证还原后文件 ──
info "正在验证还原后文件..."

# 检查文件大小
RESTORED_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
if [[ "$RESTORED_SIZE" -eq "$ORIGINAL_SIZE" ]]; then
    ok "文件大小匹配: ${ORIGINAL_SIZE_MB}MB"
else
    err "文件大小不匹配！期望 $ORIGINAL_SIZE，实际 $RESTORED_SIZE"
    exit 1
fi

# 检查 SHA-256
if command -v sha256sum &>/dev/null; then
    RESTORED_HASH=$(sha256sum "$OUTPUT_FILE" | awk '{print $1}')
elif command -v shasum &>/dev/null; then
    RESTORED_HASH=$(shasum -a 256 "$OUTPUT_FILE" | awk '{print $1}')
else
    warn "无法计算校验和，跳过最终验证"
    RESTORED_HASH=""
fi

if [[ -n "$RESTORED_HASH" ]]; then
    if [[ "$RESTORED_HASH" == "$ORIGINAL_HASH" ]]; then
        ok "SHA-256 校验通过 ✓"
    else
        err "SHA-256 校验失败！"
        err "  期望: $ORIGINAL_HASH"
        err "  实际: $RESTORED_HASH"
        exit 1
    fi
fi

echo ""
info "========================================="
ok "  还原成功！🎉"
info "========================================="
info "文件位置: $OUTPUT_FILE"
echo ""
