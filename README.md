# 🌐 Web Proxy

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

안전한 웹 브라우징을 위한 프록시 서버와 피싱 탐지 시스템

## 🚀 시작하기

### 도커 실행
```bash
docker-compose up --build
```

### 호스트 실행
```bash
# 프록시 서버 실행
python3 project/proxy/main.py

# 웹 서버 실행
cd project/web && python3 main.py
```

> ❗ 사전에 mysql 설치 및 init.sql을 실행해야 합니다.


## 🔧 프록시 설정 방법
> ⚠️ 프록시에 접속하는 클라이언트는 `127.0.0.1` 대신 프록시 호스트의 사설 주소로 대체 가능합니다.

### 브라우저 설정

#### Firefox (권장)
1. 설정 → 일반
2. 네트워크 설정 → 설정
3. 수동 프록시 설정
   - HTTP/HTTPS 프록시: `127.0.0.1`
   - 포트: `8080`
   - ✅ HTTPS에 이 프록시를 사용

### 시스템 프록시 설정

#### MacOS
```bash
# HTTP 프록시 설정 (Wi-Fi)
networksetup -setwebproxy "Wi-Fi" 127.0.0.1 8080

# HTTPS 프록시 설정
networksetup -setsecurewebproxy "Wi-Fi" 127.0.0.1 8080

# 프록시 활성화
networksetup -setwebproxystate "Wi-Fi" on
networksetup -setsecurewebproxystate "Wi-Fi" on
```

```bash
# 프록시 비활성화
networksetup -setwebproxystate "Wi-Fi" off
networksetup -setsecurewebproxystate "Wi-Fi" off
```

#### Windows
1. 설정 → 프록시 설정
2. 수동 프록시 설정
   - 프록시 서버 사용: `켬`
   - 주소: `127.0.0.1`
   - 포트: `8080`

## 🔍 프록시 테스트
```bash
curl -x http://127.0.0.1:8080 [URL]
```

## 💻 관리자 페이지
```
http://127.0.0.1:8000
```

## 🔒 HTTPS 터널링 구현 방법

HTTPS 연결은 SSL/TLS 암호화를 사용하여 클라이언트와 서버 간의 보안 통신을 제공합니다. 프록시 서버는 이를 위해 다음과 같은 터널링 메커니즘을 구현합니다:

### 전체 흐름도
```
[클라이언트]                                   [프록시 서버]                             [웹 서버]
    │                                           │                                     │
    │                                           │                                     │
    │────────────── CONNECT 요청 ─────────────▶  │                                     │
    │           CONNECT example.com:443         │                                     │
    │           Host: example.com               │                                     │
    │                                           │                                     │
    │                                           │                                     │
    │                                           │                                     │
    │                                           │                                     │
    │                                           │────────────────────────────────────▶│
    │                                           │           TCP 3-way 핸드셰이크         │
    │                                           │           SYN → SYN-ACK → ACK       │
    │                                           │◀────────────────────────────────────│
    │                                           │                                     │
    │                                           │◀── 연결 성공 시                        │
    │◀───────── 200 Connection Established ─────│                                     │
    │       (터널이 성공적으로 열림)                  │                                     │
    │                                           │                                     │
    │────────────────────[ TLS Handshake ]───────────────────────────────────────────▶│
    │              (프록시는 암호화 내용 모름)        │                                     │
    │◀────────────────────[ TLS Handshake ]◀──────────────────────────────────────────│
    │                                           │                                     │
    │═══════════════════[암호화된 HTTPS 데이터 교환]══════════════════════════════════════▶│
    │           (ex. GET /, POST, 쿠키, 인증 등)   │                                     │
    │◀════════════════════════════════════════════════════════════════════════════════│

```