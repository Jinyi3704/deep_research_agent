#!/bin/bash
# 验证合同文件是否存在且可读
# 用法: ./validate.sh <file-path>

if [ -z "$1" ]; then
    echo "Usage: ./validate.sh <file-path>"
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "Error: File not found: $1"
    exit 1
fi

# 检查文件扩展名
ext="${1##*.}"
if [[ "$ext" != "doc" && "$ext" != "docx" ]]; then
    echo "Warning: File is not a .doc or .docx file"
fi

echo "File validated: $1"
echo "Size: $(stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null) bytes"
