import socketserver
import socket
import threading
import select
import re
from typing import Tuple
from datetime import datetime
from detector import PhishingDetector
from logger import logger, RequestLogger
from urllib.parse import urlparse
from db import get_db
import os

class ProxyHandler(socketserver.BaseRequestHandler):
    """
    HTTP/HTTPS 프록시 핸들러
    """

    def setup(self):
        super().setup()
        self.db = get_db()
        self.detector = PhishingDetector()
        self.logger = RequestLogger()
        # 현재 스크립트의 디렉토리 경로 저장
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def _is_safe(self, host: str, method: str) -> tuple[str, float, list]:
        _, _, dest_ip = self._resolve_host(host)
        score, reasons = self.detector.check_domain(host, dest_ip, method)
        decision = 'allow' if score <= 0.5 else 'deny'
        return decision, score, reasons

    def _get_host(self, lines: list) -> str:
        for line in lines:
            if line.lower().startswith('host:'):
                return line.split(':', 1)[1].strip()
        return None

    def _403_response(self, host: str):
        try:
            # 스크립트 위치를 기준으로 상대 경로 계산
            template_path = os.path.join(self.base_dir, '403.html')
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
                # 이중 중괄호를 단일 중괄호로 변환하여 포맷팅
                body = template.replace('{{host}}', host)
        except Exception as e:
            # 파일을 읽지 못할 경우 기본 에러 메시지 사용
            logger.error(f"403.html 템플릿 로드 실패: {str(e)}")
            body = f"<html><body><h1>403 Forbidden</h1><p>Access to {host} is forbidden.</p></body></html>"
        
        response = (
            f"HTTP/1.1 403 Forbidden\r\n"
            f"Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )
        self.request.sendall(response.encode('utf-8'))
        self.request.close()

    def _resolve_host(self, host: str) -> Tuple[str, int, str]:
        try:
            if ':' in host:
                host, port = host.split(':')
                port = int(port)
            else:
                port = None
            try:
                ip_addr = socket.gethostbyname(host)
            except socket.gaierror:
                ip_addr = None
                logger.warning(f"호스트 {host}의 IP 주소를 찾을 수 없습니다.")
            return host, port, ip_addr
        except Exception as e:
            logger.error(f"호스트 해석 실패: {str(e)}")
            return host, None, None

    def handle(self):
        client_address = self.client_address[0]
        self.SOCKET_TIMEOUT = 10
        self.BUFFER_SIZE = 4096
        
        try:
            self.request.settimeout(self.SOCKET_TIMEOUT)
            data = self.request.recv(self.BUFFER_SIZE)

            if not data:
                logger.debug(f"[{client_address}] Preconnect or keepalive detected — skipping")
                self.request.close()
                return
            elif data.startswith(b'\x16\x03'):
                logger.debug(f"[{client_address}] TLS ClientHello without CONNECT — likely preconnect")
                self.request.close()
                return

            header = data.decode(errors='ignore')
            lines = header.split('\r\n')

            method_line = lines[0]
            method = method_line.split()[0]
            host = self._get_host(lines)

            host, port, ip_addr = self._resolve_host(host)
            if method == 'CONNECT' and not port:
                port = 443
            elif not port:
                port = 80

            decision, score, reasons = self._is_safe(host, method)
            if decision == 'deny':
                logger.warning(f"{client_address} -> {host} ({ip_addr}:{port}) | {method} | {decision}({score:.2f}) | {reasons}")
                self.logger.save(client_address, host, method, decision, score, reasons, ip_addr, port)
                self._403_response(host)
                return
            
            if method == 'CONNECT':
                if self._connect_https(host, client_address):
                    logger.info(f"{client_address} -> {host} ({ip_addr}:{port}) | {method} | {decision}({score:.2f})")
                    self.logger.save(client_address, host, method, decision, score, reasons, ip_addr, port)
            else:
                if self._connect_http(data, host, client_address):
                    logger.info(f"{client_address} -> {host} ({ip_addr}:{port}) | {method} | {decision}({score:.2f})")
                    self.logger.save(client_address, host, method, decision, score, reasons, ip_addr, port)
        except Exception as e:
            logger.error(f"[{client_address}] Failed to parse request: {str(e)}")
            self.request.close()

    def _connect_http(self, data: bytes, host: str, client_address: str) -> bool:
        try:
            host, port, ip_addr = self._resolve_host(host)
            if not port:
                port = 80

            remote = socket.create_connection((host, port), timeout=self.SOCKET_TIMEOUT)
            remote.settimeout(self.SOCKET_TIMEOUT)
            remote.sendall(data)
            logger.debug(f"[{client_address}] Forwarded request to {host} ({ip_addr}:{port})")

            response = remote.recv(self.BUFFER_SIZE)
            if response:
                self.request.sendall(response)
                logger.debug(f"[{client_address}] Received and forwarded response from {host}")
            remote.close()
            return True
            
        except socket.timeout:
            logger.error(f"[{client_address}] Connection timeout to {host}")
            self.request.sendall(b'HTTP/1.1 504 Gateway Timeout\r\n\r\n')
            return False
        except Exception as e:
            logger.error(f"[{client_address}] Failed to handle HTTP request: {str(e)}")
            self.request.sendall(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
            return False
        finally:
            self.request.close()

    def _connect_https(self, host: str, client_address: str) -> bool:
        try:
            host, port, ip_addr = self._resolve_host(host)
            if not port:
                port = 443

            try:
                remote = socket.create_connection((host, port), timeout=self.SOCKET_TIMEOUT)
                remote.settimeout(self.SOCKET_TIMEOUT)
                logger.debug(f"[{client_address}] Connected to {host} ({ip_addr}:{port})")
            except socket.timeout:
                logger.error(f"[{client_address}] Connection timeout to {host}:{port}")
                self.request.sendall(b'HTTP/1.1 504 Gateway Timeout\r\n\r\n')
                return False
            except Exception as e:
                logger.error(f"[{client_address}] Failed to connect to {host}:{port}: {str(e)}")
                self.request.sendall(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
                return False

            self.request.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            self._start_tunneling(self.request, remote)
            return True
        except Exception as e:
            logger.error(f"[{client_address}] HTTPS CONNECT failed: {str(e)}")
            return False

    def _start_tunneling(self, client_sock: socket.socket, remote_sock: socket.socket):
        """
        클라이언트와 원격 서버 간의 터널링 처리 (양방향 전달)
        """
        try:
            sockets = [client_sock, remote_sock]
            while True:
                rlist, _, _ = select.select(sockets, [], [], self.SOCKET_TIMEOUT)
                if not rlist:
                    break
                for sock in rlist:
                    try:
                        data = sock.recv(self.BUFFER_SIZE)
                        if not data:
                            return
                        target = remote_sock if sock is client_sock else client_sock
                        target.sendall(data)
                    except Exception as e:
                        logger.debug(f"터널링 중 오류: {str(e)}")
                        return
        finally:
            client_sock.close()
            remote_sock.close()

if __name__ == "__main__":
    server = socketserver.ThreadingTCPServer(('0.0.0.0', 8080), ProxyHandler)
    server.serve_forever()