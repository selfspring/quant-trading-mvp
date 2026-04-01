"""
自动因子发现脚本 - 用 Claude API 设计新因子
每次运行设计并测试 3 个新因子，由 Windows 定时任务每 30 分钟触发
"""
import io
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, 'E:/quant-trading-mvp')
os.chdir('E:/quant-trading-mvp')

# Windows GBK 编码兼容
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 日志
log_dir = Path('E:/quant-trading-mvp/logs')
log_dir.mkdir(exist_ok=True)

_stream_handler = logging.StreamHandler()
_stream_handler.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'factor_auto_{datetime.now().strftime("%Y-%m-%d")}.log', encoding='utf-8'),
        _stream_handler
    ],
    force=True
)
logger = logging.getLogger(__name__)

# Claude API 配置
API_KEY = os.getenv('CLAUDE_API_KEY', 'cr_805e6ed2aa161a3513e9efc6f779057bd14217241ef3fd0f3459b66214085afc')
BASE_URL = os.getenv('CLAUDE_BASE_URL', 'https://cursor.scihub.edu.kg/api')
MODEL = 'claude-opus-4-6'

FACTOR_DIRECTIONS = [
    '持仓量衍生因子（OI变化率、OI动量、OI与价格背离）',
    '量价关系因子（成交量异常、量价背离、成交量冲击）',
    '波动率结构因子（波动率锥、波动率偏斜、Realized Vol）',
    '跨周期因子（长周期趋势映射到短周期）',
    '微观结构因子（K线形态、影线分析）',
    '季节性因子（月份效应、周内效应、时段效应）',
    '资金流因子（主力行为、大单方向）',
    '均值回归因子（超买超卖、偏离均值）',
]


def get_existing_factor_names():
    """获取已有因子名称列表"""
    names = set()
    log_file = Path('E:/quant-trading-mvp/data/factor_discovery_log.jsonl')
    if log_file.exists():
        with open(log_file, encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                    names.add(r['name'])
                except Exception:
                    pass
    return names


def call_claude(prompt):
    """调用 Claude API"""
    headers = {
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    body = {
        'model': MODEL,
        'max_tokens': 2000,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    r = requests.post(f'{BASE_URL}/v1/messages', headers=headers, json=body, timeout=60,
                       proxies={'http': None, 'https': None})
    r.raise_for_status()
    data = r.json()
    # 兼容 thinking model: content 可能有 thinking block 在前面
    for block in data['content']:
        if block.get('type') == 'text' and 'text' in block:
            return block['text']
    raise ValueError(f"No text block in response: {json.dumps(data['content'][:2], ensure_ascii=False)[:300]}")


def design_factor(direction, existing_names):
    """让 Claude 设计一个新因子"""
    existing_sample = ', '.join(list(existing_names)[:30])
    prompt = f"""你是量化因子研究员，专注于黄金期货（SHFE au2606）的30分钟K线因子挖掘。

请设计一个新的量化因子，方向：{direction}

已有因子（不要重复）：{existing_sample}...（共{len(existing_names)}个）

要求：
1. 因子名称：英文，snake_case，简洁有意义
2. 有明确的金融逻辑
3. 输入：DataFrame，列有 open, high, low, close, volume, open_interest
4. 输出：pd.Series
5. 代码必须能直接运行（只用 numpy 和 pandas）

请严格按以下格式回复，不要有其他内容：
NAME: factor_name_here
DESC: 一句话描述因子的金融逻辑
CODE:
def compute_factor(df):
    import numpy as np
    import pandas as pd
    # 你的代码
    return factor_series
"""
    return call_claude(prompt)


def parse_factor_response(response):
    """解析 Claude 返回的因子"""
    lines = response.strip().split('\n')
    name = None
    desc = None
    code_lines = []
    in_code = False

    for line in lines:
        if line.startswith('NAME:'):
            name = line.replace('NAME:', '').strip()
        elif line.startswith('DESC:'):
            desc = line.replace('DESC:', '').strip()
        elif line.startswith('CODE:'):
            in_code = True
        elif in_code:
            code_lines.append(line)

    code = '\n'.join(code_lines).strip()
    return name, desc, code


def evaluate_and_log(name, desc, code, source):
    """执行因子代码并评估 IC"""
    from quant.common.config import config
    from quant.common.db import db_engine
    from quant.factors.factor_evaluator import evaluate_factor

    # 加载数据
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, open, high, low, close, volume, open_interest
            FROM kline_data WHERE symbol='au_main' AND interval='30m'
            ORDER BY time
        """, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 执行因子代码
    local_ns = {'df': df, 'np': np, 'pd': pd}
    exec(code, local_ns)
    factor_values = local_ns['compute_factor'](df)

    # 评估多 horizon IC
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        label = f"{h*30//60}h"
        results[label] = r
        logger.info(f"  {label}: IC={r.get('rank_ic',0):.4f}, IR={r.get('ir',0):.4f}")

    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results if results[k].get('valid', True)])
    effective = avg_ic > 0.02

    # 记录
    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name,
        'description': desc,
        'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: {kk: bool(vv) if isinstance(vv, (bool, np.bool_)) else float(vv) if isinstance(vv, (int, float, np.floating, np.integer)) else vv
                       for kk, vv in v.items()}
                   for k, v in results.items()},
        'effective': bool(effective),
        'code': code,
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # 如果有效，追加到 discovered_factors.py
    if effective:
        factor_file = Path('E:/quant-trading-mvp/quant/factors/discovered_factors.py')
        with open(factor_file, 'a', encoding='utf-8') as f:
            f.write(f'\n\ndef {name}(df):\n')
            f.write(f'    """{ desc }\n    avg |IC| = {avg_ic:.4f}\n    """\n')
            # 把 compute_factor 的函数体写进去
            body = '\n'.join('    ' + line if line.strip() else line for line in code.split('\n')[1:])
            f.write(body + '\n')
            f.write(f"\nDISCOVERED_FACTORS['{name}'] = {name}\n")
        logger.info('  ✅ 有效因子已追加到 discovered_factors.py')

    return avg_ic, effective


def main():
    import random
    logger.info('=' * 50)
    logger.info('自动因子发现开始')

    existing_names = get_existing_factor_names()
    logger.info(f'已有因子: {len(existing_names)} 个')

    success = 0
    effective_count = 0

    # 每次随机选 3 个方向，各设计一个因子
    directions = random.sample(FACTOR_DIRECTIONS, min(3, len(FACTOR_DIRECTIONS)))

    for direction in directions:
        logger.info(f'\n方向: {direction}')
        try:
            response = design_factor(direction, existing_names)
            name, desc, code = parse_factor_response(response)

            if not name or not code:
                logger.warning('解析失败，跳过')
                continue

            if name in existing_names:
                logger.warning(f'因子 {name} 已存在，跳过')
                continue

            logger.info(f'因子名: {name} | {desc}')
            avg_ic, effective = evaluate_and_log(name, desc, code, direction)
            logger.info(f'avg |IC| = {avg_ic:.4f} {"✅ 有效" if effective else ""}')

            existing_names.add(name)
            success += 1
            if effective:
                effective_count += 1

        except Exception as e:
            logger.error(f'因子设计/评估失败: {e}', exc_info=True)

    logger.info(f'\n完成: 成功 {success}/3 个，有效 {effective_count} 个')
    logger.info('=' * 50)
    return 0


if __name__ == '__main__':
    sys.exit(main())
