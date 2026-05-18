"""
实时任务监控：聚合任务状态、主键对齐对比快照、结构化日志与最近操作。
"""
import re
from typing import Any, Dict, List, Optional

from django.utils import timezone

from .models import MigrationTask, MigrationTaskLog

# 从任务日志中识别「最近操作」的关键词
_OPERATION_KEYWORDS = (
    '启动', '取消', '删除', '完成', '失败', '主键对齐', '用户取消', '定时', 'Beat',
)


def _light_view_progress(view_progress: Any) -> Dict[str, Any]:
    """精简 view_progress，供监控页展示行数/进度。"""
    if not view_progress:
        return {}
    if isinstance(view_progress, str):
        import json
        try:
            view_progress = json.loads(view_progress)
        except (json.JSONDecodeError, TypeError):
            return {}
    if not isinstance(view_progress, dict):
        return {}
    if 'current' in view_progress and 'total' in view_progress:
        slim = {
            k: view_progress[k]
            for k in ('current_table', 'current', 'total', 'failed_count')
            if k in view_progress
        }
        ct = view_progress.get('current_table')
        if ct and isinstance(view_progress.get(ct), dict):
            slim[ct] = {
                kk: vv for kk, vv in view_progress[ct].items()
                if kk in ('progress', 'total_rows', 'migrated_rows')
            }
        return slim
    slim: Dict[str, Any] = {}
    for key, val in view_progress.items():
        if isinstance(val, dict):
            slim[key] = {
                kk: vv for kk, vv in val.items()
                if kk in ('progress', 'total_rows', 'migrated_rows')
            }
    return slim


def parse_pk_compare_snapshot(task: MigrationTask) -> Optional[Dict[str, Any]]:
    """
    从任务日志解析最近一次主键对齐对比信息（源/目标行数、待删待插）。
    """
    log = task.log or ''
    lines = [ln.strip() for ln in log.split('\n') if '【主键对齐】' in ln]
    if not lines:
        return None

    snapshot: Dict[str, Any] = {
        'task_id': task.id,
        'task_name': task.name,
        'source_object': task.source_object or (task.source_objects or '')[:120],
        'source_schema': task.source_schema,
        'target_schema': task.target_schema,
        'incremental_mode': task.incremental_mode,
        'schedule_enabled': task.schedule_enabled,
        'last_schedule_run': task.last_schedule_run.isoformat() if task.last_schedule_run else None,
        'status': task.status,
    }

    for line in reversed(lines[-15:]):
        m_rows = re.search(r'源\s*(\d+)\s*行\s*/\s*目标\s*(\d+)\s*行', line)
        if m_rows and 'source_rows' not in snapshot:
            snapshot['source_rows'] = int(m_rows.group(1))
            snapshot['target_rows'] = int(m_rows.group(2))
            snapshot['row_diff'] = snapshot['source_rows'] - snapshot['target_rows']

        m_delta = re.search(r'待删除\s*(\d+)\s*行[，,]\s*待插入\s*(\d+)\s*行', line)
        if m_delta and 'to_delete' not in snapshot:
            snapshot['to_delete'] = int(m_delta.group(1))
            snapshot['to_insert'] = int(m_delta.group(2))

        if '主键列' in line and 'pk_columns' not in snapshot:
            m_pk = re.search(r'主键列\s+([^；;]+)', line)
            if m_pk:
                snapshot['pk_columns'] = m_pk.group(1).strip()

    if 'source_rows' not in snapshot and 'to_delete' not in snapshot:
        return None

    snapshot['summary_line'] = lines[-1][:500]
    snapshot['is_consistent'] = (
        snapshot.get('row_diff') == 0
        and snapshot.get('to_delete', 0) == 0
        and snapshot.get('to_insert', 0) == 0
    )
    return snapshot


def _task_monitor_item(task: MigrationTask, include_log_tail: bool = False) -> Dict[str, Any]:
    """单条任务监控摘要。"""
    item = {
        'id': task.id,
        'name': task.name,
        'task_type': task.task_type,
        'status': task.status,
        'progress': task.progress,
        'source_db': task.source_db,
        'target_db': task.target_db,
        'source_schema': task.source_schema,
        'source_object': task.source_object,
        'incremental_mode': task.incremental_mode,
        'schedule_enabled': task.schedule_enabled,
        'schedule_interval_minutes': task.schedule_interval_minutes,
        'last_schedule_run': task.last_schedule_run.isoformat() if task.last_schedule_run else None,
        'cancel_requested': task.cancel_requested,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'view_progress': _light_view_progress(task.view_progress),
    }
    if include_log_tail and task.log:
        item['log_tail'] = task.log[-1200:]
    if task.incremental_mode == 'pk_mirror':
        snap = parse_pk_compare_snapshot(task)
        if snap:
            item['compare'] = snap
    return item


def build_monitor_payload(
    task_limit: int = 40,
    log_limit: int = 60,
    compare_limit: int = 25,
) -> Dict[str, Any]:
    """构建监控页聚合数据：仅包含 status=running 的实时任务及其日志。"""
    task_limit = min(max(task_limit, 5), 100)
    log_limit = min(max(log_limit, 10), 200)
    compare_limit = min(max(compare_limit, 5), 50)

    from .task_lifecycle import reconcile_orphan_running_task

    running_qs = MigrationTask.objects.filter(status='running').order_by('-started_at', '-id')[:task_limit]
    running_list = []
    for t in running_qs:
        if reconcile_orphan_running_task(t):
            continue
        running_list.append(t)
    running_ids = [t.id for t in running_list]

    running_count = len(running_list)
    summary = {
        'running': running_count,
        # 兼容旧字段，实时页仅展示执行中任务，其余恒为 0
        'total': running_count,
        'pending': 0,
        'completed': 0,
        'failed': 0,
        'partial': 0,
        'canceled': 0,
    }

    running_tasks = [_task_monitor_item(t, include_log_tail=True) for t in running_list]
    # tasks 与 running_tasks 一致，仅供前端统一读取
    recent_tasks = running_tasks

    # 数据对比：仅执行中的主键对齐任务
    compare_snapshots: List[Dict[str, Any]] = []
    for t in running_list:
        if t.incremental_mode != 'pk_mirror':
            continue
        if len(compare_snapshots) >= compare_limit:
            break
        snap = parse_pk_compare_snapshot(t)
        if snap:
            compare_snapshots.append(snap)

    # 结构化日志：仅执行中任务
    log_qs = MigrationTaskLog.objects.select_related('task').filter(task_id__in=running_ids).order_by('-id')
    if not running_ids:
        log_qs = MigrationTaskLog.objects.none()
    log_rows = list(log_qs[:log_limit])
    recent_logs = [
        {
            'id': row.id,
            'task_id': row.task_id,
            'task_name': row.task.name if row.task_id else '',
            'level': row.level,
            'message': row.message,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }
        for row in log_rows
    ]

    # 最近操作：从结构化日志中筛选含操作关键词的记录
    recent_operations: List[Dict[str, Any]] = []
    for row in log_rows:
        msg = row.message or ''
        if any(kw in msg for kw in _OPERATION_KEYWORDS):
            recent_operations.append({
                'id': row.id,
                'task_id': row.task_id,
                'task_name': row.task.name if row.task_id else '',
                'level': row.level,
                'message': msg,
                'created_at': row.created_at.isoformat() if row.created_at else None,
            })
        if len(recent_operations) >= 30:
            break

    return {
        'status': 'success',
        'server_time': timezone.now().isoformat(),
        'summary': summary,
        'running_tasks': running_tasks,
        'tasks': recent_tasks,
        'compare_snapshots': compare_snapshots,
        'recent_logs': recent_logs,
        'recent_operations': recent_operations,
    }
