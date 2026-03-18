"""Test basicConfig called twice"""
import logging
from pathlib import Path
from datetime import datetime
import time

log_dir = Path(r"E:\quant-trading-mvp\logs")

# First call - simulating what might happen in an imported module
log_file1 = log_dir / "test_first.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] FIRST %(message)s',
    handlers=[
        logging.FileHandler(log_file1, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("Message from first config")

# Second call - like run_single_cycle.py
log_file2 = log_dir / "test_second.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] SECOND %(message)s',
    handlers=[
        logging.FileHandler(log_file2, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger.info("Message from second config")

# Check files
time.sleep(0.5)
print("\n=== File 1 ===")
print(f"Size: {log_file1.stat().st_size}")
print(log_file1.read_text())

print("\n=== File 2 ===")
if log_file2.exists():
    print(f"Size: {log_file2.stat().st_size}")
    print(log_file2.read_text())
else:
    print("File 2 does not exist!")
