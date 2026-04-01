import os
import sqlite3
import uuid
import json
from datetime import datetime

# 懒加载 chromadb 避免影响其他脚本启动速度
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/memory_engine'))
DB_PATH = os.path.join(BASE_DIR, 'memory_main.db')
CHROMA_PATH = os.path.join(BASE_DIR, 'chroma_db')
MD_DIR = os.path.join(BASE_DIR, 'markdowns')

def init_db():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(MD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL;')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            scope TEXT,
            l0_summary TEXT,
            l1_summary TEXT,
            l2_path TEXT,
            sync_status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id TEXT,
            to_id TEXT,
            relation TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

def store_memory(scope: str, l0_summary: str, l1_summary: str, l2_content: str, edges: list = None) -> str:
    init_db()
    memory_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    l2_path = os.path.join(MD_DIR, f"{memory_id}.md")
    
    with open(l2_path, 'w', encoding='utf-8') as f:
        f.write(l2_content)
        
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute('''
            INSERT INTO memories (id, scope, l0_summary, l1_summary, l2_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (memory_id, scope, l0_summary, l1_summary, l2_path, now))
        
        if edges:
            for edge in edges:
                cursor.execute('INSERT INTO memory_edges (from_id, to_id, relation) VALUES (?, ?, ?)',
                               (memory_id, edge['to_id'], edge['relation']))
                
        cursor.execute('INSERT INTO sync_jobs (memory_id) VALUES (?)', (memory_id,))
        conn.commit()
        return memory_id
    except Exception as e:
        conn.rollback()
        if os.path.exists(l2_path):
            os.remove(l2_path)
        raise e
    finally:
        conn.close()

def sync_embeddings():
    if not CHROMA_AVAILABLE:
        print("ChromaDB not installed. Skipping sync.")
        return
        
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="agent_memories")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT memory_id FROM sync_jobs WHERE status = 'pending'")
    jobs = cursor.fetchall()
    
    synced_count = 0
    for (mem_id,) in jobs:
        cursor.execute("SELECT l0_summary FROM memories WHERE id = ?", (mem_id,))
        row = cursor.fetchone()
        if not row:
            continue
        l0_summary = row[0]
        
        # 写入 ChromaDB (它会自动下载并使用默认的 sentence-transformers 模型提取向量)
        collection.add(ids=[mem_id], documents=[l0_summary])
        
        cursor.execute("UPDATE sync_jobs SET status = 'completed' WHERE memory_id = ?", (mem_id,))
        cursor.execute("UPDATE memories SET sync_status = 'synced' WHERE id = ?", (mem_id,))
        synced_count += 1
        
    conn.commit()
    conn.close()
    return synced_count

def recall_memory(query: str, n_results=3):
    if not CHROMA_AVAILABLE:
        return {"error": "ChromaDB not installed"}
        
    init_db()
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="agent_memories")
    
    if collection.count() == 0:
        return {"results": []}
        
    # 1. 向量召回 (ChromaDB)
    chroma_res = collection.query(query_texts=[query], n_results=n_results)
    if not chroma_res['ids'] or not chroma_res['ids'][0]:
        return {"results": []}
        
    matched_ids = chroma_res['ids'][0]
    
    # 2. 图谱与详情召回 (SQLite)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    results = []
    for mem_id in matched_ids:
        cursor.execute("SELECT scope, l0_summary, l1_summary, l2_path FROM memories WHERE id=?", (mem_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute("SELECT to_id, relation FROM memory_edges WHERE from_id=?", (mem_id,))
            edges = [{"to_id": r[0], "relation": r[1]} for r in cursor.fetchall()]
            
            results.append({
                "memory_id": mem_id,
                "scope": row[0],
                "l0_summary": row[1],
                "l1_summary": row[2],
                "l2_path": row[3],
                "edges": edges
            })
            
    conn.close()
    return {"results": results}

# =====================================================================
# Quant Trading System Interface: News Embeddings
# =====================================================================

def store_news_embedding(news_id: str, text_content: str, metadata: dict = None) -> bool:
    if not CHROMA_AVAILABLE:
        print('ChromaDB not installed. Cannot store news.')
        return False
        
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name='news_embeddings')
    
    collection.add(
        ids=[str(news_id)], 
        documents=[text_content], 
        metadatas=[metadata] if metadata else None
    )
    print(f'News {news_id} successfully embedded and stored.')
    return True

def search_news_vector(query: str, n_results: int = 3) -> dict:
    if not CHROMA_AVAILABLE:
        return {'error': 'ChromaDB not installed'}
        
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name='news_embeddings')
    
    if collection.count() == 0:
        return {'results': []}
        
    res = collection.query(query_texts=[query], n_results=n_results)
    
    results = []
    if res['ids'] and res['ids'][0]:
        for i in range(len(res['ids'][0])):
            results.append({
                'news_id': res['ids'][0][i],
                'document': res['documents'][0][i] if res['documents'] else '',
                'metadata': res['metadatas'][0][i] if res['metadatas'] else {}
            })
            
    return {'results': results}
