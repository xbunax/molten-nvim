import json
import time
import uuid
from queue import Empty as EmptyQueueException
from queue import Queue
from threading import Thread
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from molten.runtime_state import RuntimeState


class JupyterAPIClient:
    def __init__(self,
                 url: str,
                 kernel_info: Dict[str, Any],
                 headers: Dict[str, str],
                 verify_ssl: bool = False,
                 api_path: str = "/api/kernels"):
        self._base_url = url
        self._kernel_info = kernel_info
        self._headers = headers
        self._verify_ssl = verify_ssl
        self._api_path = api_path

        self._recv_queue: Queue[Dict[str, Any]] = Queue()

        import requests
        self.requests = requests

    def get_stdin_msg(self, **kwargs):
        return None

    def wait_for_ready(self, timeout: float = 0.):
        start = time.time()
        while True:
            response = self.requests.get(self._kernel_api_base,
                                    headers=self._headers,
                                    verify=self._verify_ssl)
            response = json.loads(response.text)

            if response["execution_state"] != "idle" and time.time() - start > timeout:
                raise RuntimeError

            # Discard unnecessary messages.
            while True:
                try:
                    response = self.get_iopub_msg()
                except EmptyQueueException:
                    return


    def start_channels(self) -> None:
        import websocket
        import ssl

        parsed_url = urlparse(self._base_url)
        
        # 根据HTTP协议自动选择WebSocket协议
        ws_scheme = "wss" if parsed_url.scheme == "https" else "ws"
        
        # 构建WebSocket URL，使用检测到的API路径
        port_str = f":{parsed_url.port}" if parsed_url.port else ""
        ws_url = f"{ws_scheme}://{parsed_url.hostname}{port_str}{self._api_path}/{self._kernel_info['id']}/channels"
        
        # SSL配置（用于HTTPS连接）
        sslopt = None
        if ws_scheme == "wss":
            sslopt = {
                "cert_reqs": ssl.CERT_NONE,  # 允许自签名证书
                "check_hostname": False,
            }
        
        
        self._socket = websocket.create_connection(
            ws_url,
            header=self._headers,
            sslopt=sslopt
        )
        self._kernel_api_base = f"{self._base_url}{self._api_path}/{self._kernel_info['id']}"

        self._iopub_recv_thread = Thread(target=self._recv_message)
        self._iopub_recv_thread.start()

    def _recv_message(self) -> None:
        while True:
            try:
                response = json.loads(self._socket.recv())
                self._recv_queue.put(response)
            except Exception as e:
                # 连接关闭或其他错误时退出线程
                break

    def get_iopub_msg(self, **kwargs):
        if self._recv_queue.empty():
            raise EmptyQueueException

        response = self._recv_queue.get()

        return response

    def execute(self, code: str):
        header = {
            'msg_type': 'execute_request',
            'msg_id': uuid.uuid1().hex,
            'session': uuid.uuid1().hex
        }

        message = json.dumps({
            'header': header,
            'parent_header': header,
            'metadata': {},
            'content': {
                'code': code,
                'silent': False
            }
        })
        self._socket.send(message)

    def shutdown(self):
        self.requests.delete(self._kernel_api_base,
                        headers=self._headers,
                        verify=self._verify_ssl)

    def cleanup_connection_file(self):
        pass

class JupyterAPIManager:
    def __init__(self,
                 url: str,
                 verify_ssl: bool = False
                 ):
        parsed_url = urlparse(url)
        self._original_url = url
        self._verify_ssl = verify_ssl

        # 提取token
        token = parse_qs(parsed_url.query).get("token")
        if token:
            self._headers = {'Authorization': f'token {token[0]}'}
        else:
            # Run notebook with --NotebookApp.disable_check_xsrf="True".
            self._headers = {}

        # 智能检测API端点
        self._base_url, self._api_path = self._detect_api_endpoint(parsed_url)

        import requests
        self.requests = requests
    
    def _detect_api_endpoint(self, parsed_url):
        """智能检测正确的API端点"""
        import requests
        
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # 可能的API路径模式
        possible_patterns = [
            # 标准Jupyter Server
            ("", "/api/kernels"),
            # JupyterHub用户空间
            ("", "/user/anonymous/api/kernels"),
            # 自定义路径结构（如当前这个服务）
            ("", f"{parsed_url.path}/api/kernels"),
            # 去掉最后一段路径
            ("", f"{'/'.join(parsed_url.path.split('/')[:-1])}/api/kernels") if parsed_url.path.count('/') > 1 else ("", "/api/kernels"),
        ]
        
        # 测试每个可能的端点
        for base_suffix, api_path in possible_patterns:
            test_base = base_domain + base_suffix
            test_url = test_base + api_path
            
            try:
                response = requests.get(test_url, headers=self._headers, verify=self._verify_ssl, timeout=5)
                if response.status_code == 200:
                    return test_base, api_path
            except Exception as e:
                continue
        
        # 如果都失败了，使用标准路径
        return base_domain, "/api/kernels"

    def start_kernel(self) -> None:
        url = f"{self._base_url}{self._api_path}"
        try:
            response = self.requests.post(url,
                                     headers=self._headers,
                                     verify=self._verify_ssl)
            
            # 检查HTTP状态码
            if response.status_code != 200 and response.status_code != 201:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
            
            
            self._kernel_info = json.loads(response.text)
            assert "id" in self._kernel_info, f"Could not connect to Jupyter Server API. Response: {response.text}"
            self._kernel_api_base = f"{url}/{self._kernel_info['id']}"
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from server: {response.text[:200]}. Error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to start kernel: {e}")

    def client(self) -> JupyterAPIClient:
        return JupyterAPIClient(url=self._base_url,
                                kernel_info=self._kernel_info,
                                headers=self._headers,
                                verify_ssl=self._verify_ssl,
                                api_path=self._api_path)

    def interrupt_kernel(self) -> None:
        self.requests.post(f"{self._kernel_api_base}/interrupt",
                      headers=self._headers,
                      verify=self._verify_ssl)

    def restart_kernel(self) -> None:
        self.state = RuntimeState.STARTING
        self.requests.post(f"{self._kernel_api_base}/restart",
                      headers=self._headers,
                      verify=self._verify_ssl)
