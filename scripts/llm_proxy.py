"""
本地 LLM 代理服务：接收 Anthropic Messages API 请求，通过 OpenClaw sessions_spawn 完成调用。
监听 http://localhost:18800/v1/messages

用法：python llm_proxy.py
然后把 .env 中的 CLAUDE_BASE_URL 改成 http://localhost:18800
"""
import sys
import io
import json
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GATEWAY_URL = "http://localhost:18789"
GATEWAY_TOKEN = None  # 从 openclaw.json 读取

def get_gateway_token():
    """从 openclaw.json 读取 gateway auth token"""
    config_path = os.path.expanduser(r"~\.openclaw\openclaw.json")
    try:
        # 用 node 解析 JSONC
        result = subprocess.run(
            ["node", "-e", f"const fs=require('fs'); const j=require('{config_path.replace(chr(92), '/')}'); console.log(j.gateway?.auth?.token || '')"],
            capture_output=True, text=True, timeout=5
        )
        token = result.stdout.strip()
        if token and token != '__OPENCLAW_REDACTED__':
            return token
    except Exception:
        pass
    return None


class LLMProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            request = json.loads(body)
            messages = request.get('messages', [])
            model = request.get('model', 'claude-sonnet-4-20250514')
            max_tokens = request.get('max_tokens', 1024)

            # 构造 prompt
            prompt_parts = []
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if isinstance(content, list):
                    content = ' '.join(c.get('text', '') for c in content if c.get('type') == 'text')
                prompt_parts.append(f"[{role}]: {content}")
            prompt = '\n'.join(prompt_parts)

            # 通过 OpenClaw Gateway API 发送
            import requests as req
            headers = {"Content-Type": "application/json"}
            if GATEWAY_TOKEN:
                headers["Authorization"] = f"Bearer {GATEWAY_TOKEN}"

            spawn_payload = {
                "task": prompt,
                "mode": "run",
                "runtime": "subagent",
                "timeoutSeconds": 120,
                "model": "1/claude-opus-4-6"
            }

            resp = req.post(
                f"{GATEWAY_URL}/api/sessions/spawn",
                headers=headers,
                json=spawn_payload,
                timeout=120,
                proxies={"http": None, "https": None}
            )

            if resp.status_code == 200:
                result = resp.json()
                text_content = result.get('result', str(result))

                # 返回 Anthropic Messages 格式
                response = {
                    "id": "msg_proxy_001",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": text_content}],
                    "model": model,
                    "stop_reason": "end_turn"
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                self.send_response(resp.status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(resp.content)

        except Exception as e:
            error_resp = {"error": {"type": "server_error", "message": str(e)}}
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_resp).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[LLM Proxy] {args[0]}")


if __name__ == '__main__':
    GATEWAY_TOKEN = get_gateway_token()
    port = 18800
    server = HTTPServer(('127.0.0.1', port), LLMProxyHandler)
    print(f"LLM Proxy listening on http://localhost:{port}")
    print(f"Gateway token: {'found' if GATEWAY_TOKEN else 'not found (will try without auth)'}")
    server.serve_forever()
