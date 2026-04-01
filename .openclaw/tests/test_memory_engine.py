import os
import sys
import json
import sqlite3
import unittest
from unittest.mock import patch, MagicMock

# 确保能找到 src 目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.memory_engine.memory_engine import init_db, store_memory, _mock_sync_embeddings, recall_memory, DB_PATH

class TestMemoryEngine(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """测试前准备：使用一个测试专用的 SQLite 数据库路径"""
        # 修改 DB_PATH 指向测试库，防止污染真实数据
        cls.test_db_path = os.path.join(os.path.dirname(DB_PATH), 'test_memory_main.db')
        cls.test_md_dir = os.path.join(os.path.dirname(cls.test_db_path), 'test_markdowns')
        
        # 覆盖全局变量 (这在简单的脚本里有效，如果在真实架构里最好用依赖注入)
        global DB_PATH
        cls.original_db_path = DB_PATH
        import src.memory_engine.memory_engine as engine
        engine.DB_PATH = cls.test_db_path
        
        # 清理可能存在的旧测试文件
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
            
        # 初始化测试数据库
        init_db()

    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        import src.memory_engine.memory_engine as engine
        engine.DB_PATH = cls.original_db_path
        
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except PermissionError:
                pass # 忽略 Windows 下可能的锁定问题

    def test_01_store_memory_transaction(self):
        """测试写入逻辑：原子事务与多表插入是否成功"""
        edges = [{'to_id': 'mock-node-1', 'relation': 'depends_on'}]
        store_memory(
            scope="test",
            l0_summary="Test L0 Summary",
            l1_summary="Test L1 Details",
            l2_content="# Test Markdown Content",
            edges=edges
        )
        
        # 验证 SQLite
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # 查 memories
        cursor.execute("SELECT id, l0_summary, l1_summary, l2_path FROM memories WHERE scope='test'")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        mem_id, l0, l1, l2_path = row
        self.assertEqual(l0, "Test L0 Summary")
        self.assertEqual(l1, "Test L1 Details")
        
        # 查 sync_jobs
        cursor.execute("SELECT status FROM sync_jobs WHERE memory_id=?", (mem_id,))
        job_status = cursor.fetchone()[0]
        self.assertEqual(job_status, 'pending')
        
        # 查 memory_edges
        cursor.execute("SELECT to_id, relation FROM memory_edges WHERE from_id=?", (mem_id,))
        edge_row = cursor.fetchone()
        self.assertEqual(edge_row[0], 'mock-node-1')
        self.assertEqual(edge_row[1], 'depends_on')
        
        conn.close()
        
        # 验证 Markdown 物理文件
        self.assertTrue(os.path.exists(l2_path))
        with open(l2_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, "# Test Markdown Content")

    @patch('src.memory_engine.memory_engine.sqlite3.connect')
    def test_02_store_memory_rollback(self, mock_connect):
        """测试回滚逻辑：如果插入中途报错，是否能保持数据一致性"""
        # 设置 Mock 让数据库操作抛出异常
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Simulated DB Insert Error")
        
        # 记录执行前的目录内容
        md_dir = os.path.join(os.path.dirname(self.test_db_path), 'markdowns')
        if not os.path.exists(md_dir):
            os.makedirs(md_dir)
        files_before = set(os.listdir(md_dir))
        
        # 尝试存储，应该被捕获并回滚
        store_memory(
            scope="test_fail",
            l0_summary="Fail L0",
            l1_summary="Fail L1",
            l2_content="Fail Content"
        )
        
        # 验证事务回滚被调用
        mock_conn.rollback.assert_called_once()
        
        # 验证孤儿 Markdown 文件是否被清理
        files_after = set(os.listdir(md_dir))
        self.assertEqual(files_before, files_after, "Failed insertion left an orphan Markdown file behind.")

if __name__ == '__main__':
    unittest.main()
