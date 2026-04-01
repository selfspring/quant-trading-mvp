#!/usr/bin/env python3
"""
RALPH_PLAN.md parser and updater.

Usage:
    python plan_utils.py status <plan_path>          # Show task counts
    python plan_utils.py next <plan_path>             # Show next unchecked task
    python plan_utils.py mark <plan_path> <n> done    # Mark task n as done
    python plan_utils.py mark <plan_path> <n> stuck   # Mark task n as stuck
    python plan_utils.py config <plan_path>            # Show config section
"""
import io
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TASK_RE = re.compile(r'^- \[([ x!])\] (\d+)\. (.+?)(?:\n  - AC: (.+))?', re.MULTILINE)
CONFIG_RE = re.compile(r'^- (\w+): (.+)$', re.MULTILINE)


def parse_plan(path: str) -> dict:
    text = Path(path).read_text(encoding='utf-8')

    # Parse config
    config_section = re.search(r'## Config\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    config = {}
    if config_section:
        for m in CONFIG_RE.finditer(config_section.group(1)):
            config[m.group(1)] = m.group(2).strip()

    # Parse tasks
    tasks = []
    for m in re.finditer(r'^- \[([ x!])\] (\d+)\. (.+?)$', text, re.MULTILINE):
        status = {'x': 'done', '!': 'stuck', ' ': 'todo'}[m.group(1)]
        tasks.append({
            'number': int(m.group(2)),
            'description': m.group(3).strip(),
            'status': status,
            'line': m.group(0),
        })

    return {'config': config, 'tasks': tasks, 'text': text, 'path': path}


def next_task(plan: dict) -> dict | None:
    for t in plan['tasks']:
        if t['status'] == 'todo':
            return t
    return None


def mark_task(plan: dict, task_num: int, new_status: str) -> str:
    text = plan['text']
    for t in plan['tasks']:
        if t['number'] == task_num:
            old = t['line']
            if new_status == 'done':
                new = old.replace('- [ ]', '- [x]')
            elif new_status == 'stuck':
                new = old.replace('- [ ]', '- [!]')
                if 'STUCK' not in new:
                    new += ' (STUCK)'
            text = text.replace(old, new)
            break
    Path(plan['path']).write_text(text, encoding='utf-8')
    return text


def status_summary(plan: dict) -> str:
    total = len(plan['tasks'])
    done = sum(1 for t in plan['tasks'] if t['status'] == 'done')
    stuck = sum(1 for t in plan['tasks'] if t['status'] == 'stuck')
    todo = total - done - stuck
    return f"Total: {total} | Done: {done} | Todo: {todo} | Stuck: {stuck}"


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    plan_path = sys.argv[2]
    plan = parse_plan(plan_path)

    if cmd == 'status':
        print(status_summary(plan))
        for t in plan['tasks']:
            icon = {'done': '✅', 'stuck': '🚫', 'todo': '⬜'}[t['status']]
            print(f"  {icon} {t['number']}. {t['description']}")

    elif cmd == 'next':
        t = next_task(plan)
        if t:
            print(f"{t['number']}|{t['description']}")
        else:
            print("ALL_DONE")

    elif cmd == 'mark':
        task_num = int(sys.argv[3])
        new_status = sys.argv[4]
        mark_task(plan, task_num, new_status)
        print(f"Task {task_num} marked as {new_status}")

    elif cmd == 'config':
        for k, v in plan['config'].items():
            print(f"{k}: {v}")
