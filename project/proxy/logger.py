import logging
import json
from datetime import datetime
from typing import List
from db import get_db
import requests
import sys

class SlackHandler(logging.Handler):
    """슬랙으로 로그를 전송하는 핸들러"""
    def __init__(self, webhook_url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.webhook_url = webhook_url
        
    def emit(self, record):
        try:
            # 로그 레벨이 WARNING 이상인 경우만 전송
            if record.levelno >= logging.WARNING:
                # 메시지에서 정보 추출
                msg_parts = record.msg.split(' | ')
                if len(msg_parts) >= 4:
                    src_dest = msg_parts[0].split(' -> ')
                    src = src_dest[0]
                    dest = src_dest[1].split(' (')[0]
                    method = msg_parts[2]
                    reasons = msg_parts[-1].strip('[]').split(', ')
                    reason_text = reasons[0].strip("'") if reasons else "알 수 없는 이유"
                else:
                    # 기본 메시지 포맷이 아닌 경우
                    src = "N/A"
                    dest = "N/A"
                    method = "N/A"
                    reason_text = record.msg
                
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 슬랙 메시지 포맷
                message = {
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"🚨 접근 차단 알림"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*시간*\n{current_time}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*차단 이유*\n{reason_text}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*출발지*\n{src}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*목적지*\n{dest}"
                                }
                            ]
                        }
                    ]
                }
                
                # 슬랙으로 전송
                response = requests.post(
                    self.webhook_url,
                    json=message,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                
        except Exception as e:
            print(f"Failed to send log to Slack: {str(e)}")

class ColoredFormatter(logging.Formatter):
    """컬러 로깅을 위한 커스텀 포매터"""
    
    COLORS = {
        'DEBUG': '\033[94m',     # 파란색
        'INFO': '\033[92m',      # 초록색
        'WARNING': '\033[93m',   # 노란색
        'ERROR': '\033[91m',     # 빨간색
        'CRITICAL': '\033[91m',  # 빨간색
        'RESET': '\033[0m'       # 리셋
    }

    def format(self, record):
        # 로그 레벨에 따른 컬러 적용
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        # 시간 형식 변경 (밀리초 제거)
        record.asctime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        return super().format(record)

def _setup():
    """로거 설정"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not logger.hasHandlers():  # 핸들러 중복 추가 방지
        # 콘솔 출력 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = ColoredFormatter('%(levelname)s | %(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 슬랙 핸들러
        slack_handler = SlackHandler('https://hooks.slack.com/services/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')
        slack_handler.setLevel(logging.WARNING)
        slack_handler.setFormatter(formatter)
        logger.addHandler(slack_handler)

    return logger

# 전역 로거 인스턴스 생성
logger = _setup()

class RequestLogger:
    """요청 로그를 저장하는 클래스"""
    def __init__(self):
        self.db = get_db()

    def save(self, src: str, dest: str, method: str, decision: str, score: float = 0.0, reasons: List[str] = None, dest_ip: str = None, dest_port: int = None):
        """요청 정보를 MySQL에 저장"""
        try:
            with self.db.get_cursor() as cursor:
                query = """
                    INSERT INTO logs (src, dest, dest_ip, dest_port, method, list_type, score, reason, time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                # reasons가 None이거나 빈 리스트면 NULL 저장
                reason_value = None if reasons is None or len(reasons) == 0 else json.dumps(reasons)
                
                values = (
                    src,        # src
                    dest,      # dest
                    dest_ip,   # dest_ip
                    dest_port, # dest_port
                    method,    # method
                    decision,  # list_type
                    score,     # score
                    reason_value,  # reason
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # time
                )
                
                cursor.execute(query, values)
                
        except Exception as e:
            logger.error(f"로그 저장 실패: {e}")
