"""
合同加载与拆分（非 LLM 工具）

由命令「审核合同 <路径>」直接调用，用于读取文件并拆分章节，写入审核状态。
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple

from state import ReviewState


def _read_docx(path: str) -> str:
    """读取 Word 文档。优先 python-docx，否则用 zipfile 解析 XML。"""
    try:
        from docx import Document
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        pass
    except Exception:
        pass
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(path, "r") as z:
            xml_content = z.read("word/document.xml")
            root = ET.fromstring(xml_content)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in root.findall(".//w:p", ns):
                text = "".join(t.text for t in p.findall(".//w:t", ns) if t.text)
                if text.strip():
                    paragraphs.append(text)
            return "\n".join(paragraphs)
    except Exception:
        return ""


def _read_file(path: str) -> str:
    """读取文件内容"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return _read_docx(path)
    if ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _split_sections(content: str) -> List[Tuple[str, str]]:
    """
    拆分合同章节：合同基本信息、主合同条文、附件。
    附件作为完整单元，内部不再拆章。
    """
    sections = []
    appendix_pattern = r"(?:^|\n)(附[件录][一二三四五六七八九十\d]+)[、：:\s]"
    appendix_matches = list(re.finditer(appendix_pattern, content, re.MULTILINE))
    main_content_end = appendix_matches[0].start() if appendix_matches else len(content)
    main_content = content[:main_content_end]

    main_section_pattern = r"(?:^|\n)(第[一二三四五六七八九十百千零〇]+[条章])\s*([^\n]*)"
    main_matches = list(re.finditer(main_section_pattern, main_content, re.MULTILINE))
    if not main_matches:
        main_section_pattern = r"(?:^|\n)(第\s*\d+\s*[条章])\s*([^\n]*)"
        main_matches = list(re.finditer(main_section_pattern, main_content, re.MULTILINE))

    if main_matches:
        first_match = main_matches[0]
        if first_match.start() > 0:
            header_content = main_content[:first_match.start()].strip()
            if header_content and len(header_content) > 50:
                sections.append(("合同基本信息", header_content))
    for i, match in enumerate(main_matches):
        title_text = (match.group(1) + " " + match.group(2)).strip()
        content_start = match.end()
        content_end = main_matches[i + 1].start() if i + 1 < len(main_matches) else main_content_end
        section_content = main_content[content_start:content_end].strip()
        sections.append((title_text, section_content))

    processed_appendix_ids = set()
    for i, match in enumerate(appendix_matches):
        appendix_id = match.group(1)
        title_start = match.start() + 1 if content[match.start()] == "\n" else match.start()
        line_end = content.find("\n", match.end())
        if line_end == -1:
            line_end = len(content)
        full_title = content[title_start:line_end].strip()
        content_start = line_end + 1 if line_end < len(content) else line_end
        content_end = appendix_matches[i + 1].start() if i + 1 < len(appendix_matches) else len(content)
        appendix_content = content[content_start:content_end].strip()
        full_title = re.sub(r"[、：:]\s*$", "", full_title)
        if appendix_id in processed_appendix_ids:
            for j, (existing_title, existing_content) in enumerate(sections):
                if existing_title.startswith(appendix_id):
                    if len(appendix_content) > len(existing_content):
                        sections[j] = (full_title, appendix_content)
                    break
        else:
            processed_appendix_ids.add(appendix_id)
            sections.append((full_title, appendix_content))

    if not sections:
        return [("全文", content.strip())]
    return sections


def load_and_split_contract(state: ReviewState, path: str) -> str:
    """
    加载并拆分合同文档，更新 state。
    由命令「审核合同 <路径>」直接调用，不作为 Agent 工具。
    """
    if not os.path.exists(path):
        return f"错误：文件不存在 '{path}'"
    content = _read_file(path)
    if not content:
        return "错误：无法读取文件内容"
    sections = _split_sections(content)
    if not sections:
        return "错误：未能识别出章节结构"
    state.reset()
    state.contract_name = os.path.basename(path)
    state.contract_path = path
    for title, sec_content in sections:
        state.add_section(title, sec_content)
    lines = [
        f"成功拆分合同 '{state.contract_name}'",
        f"共 {len(sections)} 个章节：",
        "",
    ]
    for i, (title, _) in enumerate(sections):
        lines.append(f"  {i + 1}. {title}")
    lines.append("")
    lines.append("请输入「开始审核」或「下一章」开始审核。")
    return "\n".join(lines)
