"""Check logging configuration order"""
import logging
import sys

print("Before any imports:")
print(f"  root handlers: {logging.root.handlers}")
print(f"  root level: {logging.root.level}")

sys.path.insert(0, 'E:\\quant-trading-mvp')

print("\nImporting quant.common.config...")
from quant.common.config import config
print(f"  root handlers: {logging.root.handlers}")
print(f"  root level: {logging.root.level}")

print("\nImporting other modules...")
from quant.signal_generator.ml_predictor import MLPredictor
print(f"  root handlers: {logging.root.handlers}")
