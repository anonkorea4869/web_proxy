from typing import List, Tuple
from urllib.parse import urlparse
import time
from logger import logger
import ipaddress
from db import get_db
import requests

class PhishingDetector:
    # 싱글톤 인스턴스
    _instance = None
    
    # 클래스 변수
    safe_domain_cache = {}  # 안전한 도메인 캐시
    cache_duration = 600  # 캐시 유효 시간 (10분)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db = get_db()
            cls._instance.blacklist_domains = set()
            cls._instance.blacklist_cidrs = set()
            cls._instance.last_refresh_time = 0
            cls._instance.refresh_interval = 10
            cls._instance._init_blacklist()
            
        return cls._instance

    def __init__(self):
        """이미 초기화된 인스턴스를 반환"""
        pass

    def _init_blacklist(self):
        """블랙리스트 초기 로드"""
        self._refresh_blacklist()

    def _should_refresh(self):
        """블랙리스트 갱신이 필요한지 확인"""
        current_time = time.time()
        if current_time - self.last_refresh_time >= self.refresh_interval:
            return True
        return False

    def _refresh_blacklist(self):
        """블랙리스트를 데이터베이스에서 다시 로드"""
        try:
            with self.db.get_cursor() as cursor:
                # 차단 도메인 로드
                cursor.execute("""
                    SELECT domain 
                    FROM domain 
                    WHERE list_type = 'deny' AND is_active = 1
                """)
                new_blacklist_domains = {row['domain'] for row in cursor.fetchall()}
                
                # 차단 CIDR 로드
                cursor.execute("""
                    SELECT cidr 
                    FROM cidr 
                    WHERE list_type = 'deny' AND is_active = 1
                """)
                cidr_rows = cursor.fetchall()
                new_blacklist_cidrs = set()
                for row in cidr_rows:
                    try:
                        cidr_network = ipaddress.ip_network(row['cidr'])
                        new_blacklist_cidrs.add(cidr_network)
                    except ValueError as e:
                        logger.error(f"잘못된 CIDR 형식: {row['cidr']}, 오류: {str(e)}")

                # 변경 사항 확인
                domains_added = new_blacklist_domains - self.blacklist_domains
                domains_removed = self.blacklist_domains - new_blacklist_domains
                cidrs_added = new_blacklist_cidrs - self.blacklist_cidrs
                cidrs_removed = self.blacklist_cidrs - new_blacklist_cidrs

                # 블랙리스트 업데이트
                self.blacklist_domains = new_blacklist_domains
                self.blacklist_cidrs = new_blacklist_cidrs
                self.last_refresh_time = time.time()

                # 변경 사항 로깅
                if domains_added:
                    logger.debug(f"새로 추가된 차단 도메인: {domains_added}")
                if domains_removed:
                    logger.debug(f"제거된 차단 도메인: {domains_removed}")
                if cidrs_added:
                    logger.debug(f"새로 추가된 차단 CIDR: {cidrs_added}")
                if cidrs_removed:
                    logger.debug(f"제거된 차단 CIDR: {cidrs_removed}")

        except Exception as e:
            logger.error(f"블랙리스트 갱신 실패: {str(e)}")

    def _extract_domain(self, host: str) -> str:
        """URL에서 도메인을 추출 (서브도메인 포함)"""
        try:
            # 포트 제거
            if ':' in host:
                host = host.split(':')[0]
            
            # IP 주소인 경우 그대로 반환
            parts = host.split('.')
            if all(part.isdigit() for part in parts):
                return host
                
            return host
            
        except Exception as e:
            logger.error(f"도메인 추출 실패: {str(e)}")
            return host

    def _check_tld(self, domain: str, method: str) -> Tuple[float, str]:
        """TLD 검사를 수행하고 점수와 이유를 반환"""
        tld = domain.split('.')[-1]

        suspicious_tlds = {
            'xyz', 'tk', 'ml', 'ga', 'cf', 'gq',  # 무료 도메인
            'info', 'top', 'club', 'pw',           # 스팸/피싱에 자주 사용
            'zip', 'review', 'country', 'kim',     # 비정상적인 TLD
            'work', 'party', 'click', 'loan',      # 악의적 사용 빈도 높음
            'download', 'racing', 'science'         # 의심스러운 용도
        }
        
        if tld in suspicious_tlds:
            return 0.3, f"의심스러운 TLD: {tld}"
        return 0.0, ""

    def _check_subdomains(self, domain: str, method: str) -> Tuple[float, str]:
        """서브도메인 수를 검사하고 점수와 이유를 반환"""
        subdomains = domain.split('.')
        if len(subdomains) > 5:
            count = len(subdomains) - 2
            return 0.3, f"과도한 서브도메인 수: {count}"
        return 0.0, ""

    def _check_hyphens(self, domain: str, method: str) -> Tuple[float, str]:
        """하이픈 수를 검사하고 점수와 이유를 반환"""
        hyphen_count = domain.count('-')
        if hyphen_count > 2:
            return 0.3, f"과도한 하이픈 수: {hyphen_count}"
        return 0.0, ""

    def _check_typosquatting(self, domain: str, method: str) -> Tuple[float, str]:
        """Jaro-Winkler 기반 타이포스쿼팅 검사를 수행"""
        common_brands = {'google', 'facebook', 'amazon', 'apple', 'microsoft', 'naver', 'kakao', 'daum'}
        domain_base = domain.split('.')[0]

        for brand in common_brands:
            similarity = self._jaro_winkler_similarity(domain_base, brand)
            if similarity >= 0.9:
                return 0.3, f"타이포스쿼팅 가능성 발견: {brand}와 유사 (유사도 {similarity:.2f})"
        return 0.0, ""

    def _jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Jaro-Winkler 유사도 계산 함수"""
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        max_dist = int(max(len1, len2) / 2) - 1

        match = 0
        hash_s1 = [0] * len1
        hash_s2 = [0] * len2

        # Matching characters
        for i in range(len1):
            for j in range(max(0, i - max_dist), min(len2, i + max_dist + 1)):
                if s1[i] == s2[j] and hash_s2[j] == 0:
                    hash_s1[i] = 1
                    hash_s2[j] = 1
                    match += 1
                    break

        if match == 0:
            return 0.0

        # Transpositions
        t = 0
        point = 0
        for i in range(len1):
            if hash_s1[i]:
                while hash_s2[point] == 0:
                    point += 1
                if s1[i] != s2[point]:
                    t += 1
                point += 1
        t /= 2

        jaro = (match / len1 + match / len2 + (match - t) / match) / 3.0

        # Winkler boost
        prefix = 0
        for i in range(min(len1, len2)):
            if s1[i] == s2[i]:
                prefix += 1
            else:
                break
        prefix = min(4, prefix)

        return jaro + 0.1 * prefix * (1 - jaro)
    
    def _is_cached_domain_safe(self, domain: str) -> Tuple[bool, float, List[str]]:
        """캐시된 도메인 정보 조회 (10분 유효)"""
        cache_entry = PhishingDetector.safe_domain_cache.get(domain)
        if cache_entry:
            cached_time, score, reasons = cache_entry
            if time.time() - cached_time < PhishingDetector.cache_duration:
                return True, score, reasons
            else:
                # 캐시 만료 시 삭제
                del PhishingDetector.safe_domain_cache[domain]
        return False, 0.0, []

    def _check_google_safe_browsing(self, domain: str, method: str) -> Tuple[float, str]:
        api_key = "AIzaSyCVnNUDyZvbgC-Z2wpO2ZnfzaEPHP-XUzY"
        api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"

        logger.debug(f"Google Safe Browsing 검사 시작: {domain}")

        payload = {
            "client": {
                "clientId": "secret",
                "clientVersion": "1.5.2"
            },
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION"
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": domain}]
            }
        }

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Google Safe Browsing 응답: {result}")

            if result.get("matches"):
                matches = result["matches"]
                threats = []
                for match in matches:
                    threat_type = match.get("threatType", "알 수 없는 위협")
                    threat_url = match.get("threat", {}).get("url", url)
                    threats.append(f"{threat_type} ({threat_url})")

                threat_info = "; ".join(threats)
                logger.debug(f"Google Safe Browsing 위험 감지: {threat_info}")
                return 1.0, f"Google Safe Browsing 위험 감지: {threat_info}"

            logger.debug("Google Safe Browsing 안전 판정")
            return 0.0, ""

        except Exception as e:
            logger.debug(f"Google Safe Browsing API 오류: {str(e)}")
            return 0.0, ""
        
    def _check_ip_host(self, domain: str, method: str) -> Tuple[float, str]:
        """IP 주소 호스트 검사"""
        try:
            # IPv4 또는 IPv6 주소인지 확인
            ipaddress.ip_address(domain)
            return 0.6, "IP 주소 호스트"
        except ValueError:
            return 0.0, ""
        except Exception as e:
            logger.error(f"IP 주소 호스트 검사 오류: {str(e)}")
            return 0.0, ""
    
    def _check_https_to_http_redirect(self, domain: str, method: str) -> Tuple[float, str]:
        """HTTPS -> HTTP 리다이렉트 검사"""
        # CONNECT 메소드가 아닌 경우 검사하지 않음
        if method != 'CONNECT':
            return 0.0, ""

        try:
            # HTTPS로 요청 보내기
            test_url = f"https://{domain}"
            logger.debug(f"HTTPS 리다이렉트 검사 시작: {test_url}")

            response = requests.get(
                test_url,
                allow_redirects=False,
                timeout=5,
                verify=True
            )

            # 리다이렉트 응답인 경우
            if 300 <= response.status_code < 400:
                redirect_url = response.headers.get('Location', '')
                logger.debug(f"리다이렉트 발견: {redirect_url}")

                # HTTP로의 리다이렉트 확인
                if redirect_url.lower().startswith('http://'):
                    logger.debug(f"HTTPS에서 HTTP로의 리다이렉트 감지")
                    return 0.3, f"안전하지 않은 리다이렉트 감지"

            return 0.0, ""

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL 인증서 검증 실패: {domain}")
            return 1.0, f"SSL 인증서 검증 실패"
        except requests.exceptions.RequestException as e:
            logger.error(f"리다이렉트 검사 실패: {domain}, 오류: {str(e)}")
            return 0.0, ""
    
    def check_domain(self, domain: str, ip: str = None, method: str = None) -> Tuple[float, List[str]]:
        """도메인 검사를 수행하고 피싱 점수와 이유를 반환"""
        # 블랙리스트 검사 먼저 수행
        is_blacklisted, blacklist_reason = self._check_blacklist(domain, ip)
        if is_blacklisted:
            return 1.0, [blacklist_reason]

        # 블랙리스트 통과 후 캐시 확인
        is_cached, cached_score, cached_reasons = self._is_cached_domain_safe(domain)
        logger.debug(f"캐시 확인: {domain}, 결과: {is_cached}, 점수: {cached_score}, 이유: {cached_reasons}")
        if is_cached:
            logger.debug(f"캐시 통과: {domain}, 점수: {cached_score}, 이유: {cached_reasons}")
            return cached_score, cached_reasons

        score = 0.0
        reasons = []

        # 나머지 검사 수행
        checks = [
            self._check_google_safe_browsing,
            self._check_tld,
            self._check_subdomains,
            self._check_hyphens,
            self._check_typosquatting,
            self._check_ip_host,
            self._check_https_to_http_redirect
        ]

        for check in checks:
            check_score, reason = check(domain, method)    
            score += check_score
            if reason:
                reasons.append(reason)
            
            # 점수가 1을 넘으면 1로 조정
            if score >= 1.0:
                score = 1.0
                break

        # 캐시에 저장
        if not is_cached:
            logger.debug(f"캐시에 저장: {domain}, 점수: {score}, 이유: {reasons}")
            PhishingDetector.safe_domain_cache[domain] = (time.time(), score, reasons)

        return score, reasons

    def _check_blacklist(self, domain: str, ip: str = None) -> Tuple[bool, str]:
        """블랙리스트 검사를 수행하고 결과와 이유를 반환"""
        try:
            # 갱신이 필요한지 확인
            if self._should_refresh():
                self._refresh_blacklist()

            # 도메인 검사
            domain = domain.lower()  # 소문자로 변환
            logger.debug(f"도메인 검사: {domain}")
            
            # 도메인과 그 부모 도메인들을 검사
            domain_parts = domain.split('.')
            for i in range(len(domain_parts) - 1):
                check_domain = '.'.join(domain_parts[i:])
                if check_domain in self.blacklist_domains:
                    logger.debug(f"도메인 차단: {domain} (매칭된 블랙리스트 도메인: {check_domain})")
                    return True, "블랙리스트에 등록된 도메인"

            # IP 주소 검사
            if ip:
                logger.debug(f"IP 검사 시작: {ip}")
                try:
                    ip_obj = ipaddress.ip_address(ip)
                    logger.debug(f"IP 주소 파싱 성공: {ip_obj}")
                    for cidr in self.blacklist_cidrs:
                        if ip_obj in cidr:
                            logger.debug(f"CIDR 차단: {ip} (매칭된 CIDR: {cidr})")
                            return True, "블랙리스트에 등록된 IP 대역"
                except ValueError as e:
                    logger.error(f"IP 주소 파싱 실패: {ip}, 오류: {str(e)}")

            logger.debug(f"도메인/IP 허용: {domain}, {ip}")
            return False, ""
            
        except Exception as e:
            logger.error(f"블랙리스트 검사 중 오류: {str(e)}")
            return False, f"검사 오류: {str(e)}"

    def __del__(self):
        """소멸자: 데이터베이스 연결 정리"""
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'conn'):
                self.conn.close()
        except Exception as e:
            logger.error(f"데이터베이스 연결 종료 실패: {str(e)}")