import sys
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
已停用的旧版 LLM 新闻分析入口。

说明：
- baseline 唯一主入口已统一为 `scripts/batch_llm_analysis.py`
- 本脚本不再作为主链路入口，也不应继续被定时任务或人工主流程调用
- 保留此文件仅用于显式阻断旧调用路径，并给出迁移提示
"""
import logging
import sys
from pathlib import Path

# 日志配置
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "llm_analysis_deprecated.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)

DEPRECATION_MESSAGE = (
    "run_llm_analysis.py 已停用，不再作为 LLM 新闻分析主入口。\n"
    "baseline 唯一入口: python scripts/batch_llm_analysis.py [--limit N]\n"
    "原因: 旧入口通过 LLMNewsAnalyzer 走另一套读取/保存/验证路径，会继续制造双入口歧义。"
)


def main() -> int:
    logger.error(DEPRECATION_MESSAGE)
    return 1


if __name__ == "__main__":
    sys.exit(main())
