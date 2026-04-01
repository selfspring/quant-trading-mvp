import sys
import os
import io
import json

# Fix Windows GBK encoding issue: force UTF-8 stdout
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 引入我们写好的底层 Python 引擎
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src/memory_engine')))
from memory_engine import store_memory, sync_embeddings, recall_memory


def run_store():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='?')
    parser.add_argument('--file', help='Path to JSON file with parameters')
    args, unknown = parser.parse_known_args(sys.argv)

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            input_data = f.read()
    else:
        input_data = sys.stdin.read()

    if not input_data:
        print(json.dumps({"error": "No input provided"}))
        return

    try:
        params = json.loads(input_data)
        scope = params.get('scope', 'general')
        l0_summary = params.get('l0_summary', '')
        l1_summary = params.get('l1_summary', '')
        l2_content = params.get('l2_content', '')
        edges = params.get('edges', [])

        mem_id = store_memory(scope, l0_summary, l1_summary, l2_content, edges)
        synced_count = sync_embeddings()

        print(json.dumps({
            "status": "success",
            "memory_id": mem_id,
            "synced_count": synced_count,
            "message": "Memory successfully tiered and persisted into SQLite + ChromaDB + Local FS."
        }))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))


def run_recall():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='?')
    parser.add_argument('--query', help='Search query string')
    parser.add_argument('--n_results', type=int, default=3)
    args, unknown = parser.parse_known_args(sys.argv)

    try:
        if args.query:
            query = args.query
            n_results = args.n_results
        else:
            input_data = sys.stdin.read()
            if not input_data:
                print(json.dumps({"error": "No input provided"}))
                return
            params = json.loads(input_data)
            query = params.get('query', '')
            n_results = int(params.get('n_results', 3))

        results = recall_memory(query, n_results=n_results)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else None
    if command == 'store':
        run_store()
    elif command == 'recall':
        run_recall()
    else:
        print(json.dumps({"error": "Unknown command. Use 'store' or 'recall'."}))
