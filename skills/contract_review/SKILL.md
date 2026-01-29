---
name: contract-review
description: 审查合同文件，识别风险点并提供修改建议。Use when reviewing contracts, checking for risks, or when user mentions "审查合同"、"合同审核"、"review contract".
argument-hint: "[file-path]"
allowed-tools: read_doc, read_file
---

# 合同审查技能

审查 $ARGUMENTS 合同文件，识别风险点并提供专业的修改建议。

## 审查流程

**重要：请严格按以下步骤执行**

1. **读取专家经验文件**：首先使用 `read_file` 工具读取 `skills/contract_review/resources/expert_experience.md`，获取合同审查的专业知识和审查要点

2. **读取合同文件**：使用 `read_doc` 工具读取用户指定的合同文件 `$ARGUMENTS`

3. **按专家经验审查**：根据步骤1中读取到的专家经验，逐项审查合同内容

4. **输出审查报告**：按照下方指定格式输出结果

## 可用资源

- 专家经验文件：`skills/contract_review/resources/expert_experience.md`（必须先读取）
- 辅助脚本：`skills/contract_review/scripts/` 目录

## 输出格式

请按以下格式输出审查结果：

```
## 合同概要
- 合同名称：
- 合同双方：
- 合同标的：
- 合同金额：
- 合同期限：

## 风险点分析

### 高风险
1. [风险点描述]
   - 原条款：[引用原文]
   - 风险说明：[具体风险]
   - 修改建议：[具体建议]

### 中风险
...

### 低风险
...

## 修改建议汇总
[按重要性排序的修改建议清单]

## 总体评价
[对合同整体风险水平的评价和签署建议]
```
