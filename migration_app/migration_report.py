"""
迁移任务完成后生成结构化报告（成功/失败对象、行数差异、需人工审查项）。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# 日志中需人工审查的关键词
_MANUAL_MARKERS = (
    '需人工审查',
    '需人工复核',
    '需人工处理',
    '需人工完成',
    '人工改写',
)


def _extract_manual_items_from_log(log_text: str) -> List[str]:
    """从任务日志提取人工审查条目。"""
    items: List[str] = []
    if not log_text:
        return items
    for line in log_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(m in stripped for m in _MANUAL_MARKERS):
            items.append(stripped)
    return items


def _summarize_view_progress(vp: Optional[dict]) -> Dict[str, Any]:
    """从 view_progress 汇总对象级结果。"""
    if not vp or not isinstance(vp, dict):
        return {}
    summary: Dict[str, Any] = {}
    if vp.get('failed_objects'):
        summary['failed_objects'] = vp['failed_objects']
    if vp.get('completed_objects'):
        summary['completed_objects'] = vp['completed_objects']
    if vp.get('failed_count') is not None:
        summary['failed_table_count'] = vp['failed_count']
    if vp.get('phase'):
        summary['last_phase'] = vp['phase']
    if vp.get('orchestration'):
        summary['orchestration'] = vp['orchestration']
    return summary


def build_migration_report(task) -> Dict[str, Any]:
    """
    根据任务当前状态构建迁移报告 JSON。
    可在任务完成/部分完成/失败时调用并写入 task.migration_report。
    """
    log_text = task.log or ''
    manual_items = _extract_manual_items_from_log(log_text)

    # 行数校验摘要
    row_checks: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'【校验(通过|失败)】([^:]+):\s*源端\s*(\d+)\s*行\s*[=≠<>]\s*目标端\s*(\d+)\s*行',
        log_text,
    ):
        ok = m.group(1) == '通过'
        row_checks.append({
            'object': m.group(2).strip(),
            'source_rows': int(m.group(3)),
            'target_rows': int(m.group(4)),
            'passed': ok,
            'row_diff': int(m.group(3)) - int(m.group(4)),
        })

    report: Dict[str, Any] = {
        'task_id': task.id,
        'task_name': task.name,
        'task_type': task.task_type,
        'status': task.status,
        'source_schema': task.source_schema,
        'target_schema': task.target_schema,
        'progress': task.progress,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'summary': {
            'manual_review_count': len(manual_items),
            'row_check_count': len(row_checks),
            'row_check_failed': sum(1 for r in row_checks if not r['passed']),
        },
        'manual_review_items': manual_items[:200],
        'row_checks': row_checks[:500],
        'view_progress_summary': _summarize_view_progress(task.view_progress),
    }
    return report


def persist_migration_report(task) -> Dict[str, Any]:
    """生成报告并保存到任务 migration_report 字段。"""
    report = build_migration_report(task)
    task.migration_report = report
    task.save(update_fields=['migration_report'])
    return report


def report_to_json_text(report: Dict[str, Any]) -> str:
    """导出为格式化 JSON 字符串。"""
    return json.dumps(report, ensure_ascii=False, indent=2)
