"""Test logging directly"""
import logging
import os
from pathlib import Path
from datetime import datetime

log_dir = Path(r"E:\quant-trading-mvp\logs")
log_file = log_dir / f"test_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

print(f"Log file path: {log_file}")
print(f"Log dir exists: {log_dir.exists()}")
print(f"Log dir writable: {os.access(log_dir, os.W_OK)}")

import os
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True  # Force reconfiguration
)

logger = logging.getLogger(__name__)
logger.info("Test message 1")
logger.info("Test message 2")

print("\nChecking file...")
import time
time.sleep(1)  # Give it a moment to flush

if log_file.exists():
    print(f"File exists: {log_file.stat().st_size} bytes")
    print(f"Content: {log_file.read_text()}")
else:
    print("File does not exist!")
