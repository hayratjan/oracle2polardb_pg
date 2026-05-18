"""
迁移任务断点续传：解析已完成表、过滤待迁移列表、维护 view_progress。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Set

# 日志中识别已成功完成的表名
_RE_COMPLETE = re.compile(r'【完成】表\s+(\S+)\s+迁移成功')
_RE_COMPLETE_NODATA = re.compile(r'【完成】表\s+\w+\.(\S+)\s+无数据')
_RE_LEGACY_IMPORT = re.compile(r'^表\s+(\S+)\s+导入\s+\d+\s+行到')


def normalize_view_progress(view_progress: Any) -> Dict[str, Any]:
    """将 view_progress 统一为 dict。"""
    if view_progress is None:
        return {}
    if isinstance(view_progress, str):
        try:
            view_progress = json.loads(view_progress)
        except (json.JSONDecodeError, TypeError):
            return {}
    return dict(view_progress) if isinstance(view_progress, dict) else {}


def parse_completed_tables_from_log(log_text: str) -> Set[str]:
    """从任务日志解析已成功完成的表名。"""
    completed: Set[str] = set()
    if not log_text:
        return completed
    for line in log_text.split('\n'):
        line = line.strip()
        for pattern in (_RE_COMPLETE, _RE_LEGACY_IMPORT):
            m = pattern.search(line)
            if m:
                completed.add(m.group(1))
                break
        m = _RE_COMPLETE_NODATA.search(line)
        if m:
            completed.add(m.group(1))
    return completed


def get_completed_tables(task) -> Set[str]:
    """合并 view_progress.completed_tables 与日志解析结果。"""
    vp = normalize_view_progress(getattr(task, 'view_progress', None))
    completed: Set[str] = set()
    for name in vp.get('completed_tables') or []:
        if name:
            completed.add(str(name))
    completed |= parse_completed_tables_from_log(getattr(task, 'log', None) or '')
    return completed


def filter_pending_tables(all_tables: List[str], completed: Set[str]) -> List[str]:
    """按已完成集合过滤，保持原顺序。"""
    done_upper = {c.upper() for c in completed}
    return [t for t in all_tables if t.upper() not in done_upper]


def can_resume_task(task) -> bool:
    """是否允许断点续传（未正常结束的任务）。"""
    if task.status not in ('partial', 'aborted', 'canceled', 'failed'):
        return False
    return task.task_type in ('all_tables', 'table')


def mark_table_completed(completed: Set[str], table_name: str) -> List[str]:
    """记录单表完成，返回排序后的列表供写入 view_progress。"""
    completed.add(table_name)
    return sorted(completed)


def build_batch_view_progress(
    *,
    current_table: str,
    current_index: int,
    total_tables: int,
    failed_count: int,
    completed_tables: List[str],
    table_detail: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """构建「所有表/多表」任务的 view_progress。"""
    vp: Dict[str, Any] = {
        'current_table': current_table,
        'current': current_index,
        'total': total_tables,
        'failed_count': failed_count,
        'completed_tables': completed_tables,
    }
    if table_detail and current_table:
        vp[current_table] = table_detail
    return vp
