import asyncio
import logging
from .server import ProxyServer

async def main():
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 프록시 서버 인스턴스 생성
    proxy = ProxyServer(host='0.0.0.0', port=8080)
    
    try:
        # 서버 시작
        await proxy.start()
    except KeyboardInterrupt:
        logging.info("Shutting down proxy server...")
    except Exception as e:
        logging.error(f"Error running proxy server: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 