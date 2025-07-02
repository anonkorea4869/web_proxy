from fastapi import FastAPI, Request, HTTPException, Form, Body
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from typing import Optional, Dict
from db import get_db
import uvicorn

# 환경 변수 로드
load_dotenv()

app = FastAPI(title="프록시 로그 관리")

# 데이터베이스 연결 초기화
db = get_db()

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        return templates.TemplateResponse("index.html", {
            "request": request
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"서버 오류: {str(e)}"
        }) 
    
@app.get("/api/logs")
async def get_logs():
    try:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    l.idx,
                    l.src as client_ip,
                    CONCAT(
                        SUBSTRING_INDEX(SUBSTRING_INDEX(l.dest, '://', -1), '/', 1),
                        ':', 
                        l.dest_port
                    ) as url,
                    l.method,
                    l.list_type as decision,
                    l.score,
                    l.reason,
                    l.time as timestamp
                FROM logs l
                LEFT JOIN hide h ON l.dest LIKE CONCAT(h.domain, '%') AND h.is_active = 1
                WHERE h.domain IS NULL
                ORDER BY l.time DESC 
                LIMIT 1000
            """)
            
            logs = cursor.fetchall()
            
            # JSON 형식으로 변환
            for log in logs:
                log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                
                # reason이 None이면 기본값 설정
                if log['reason'] is None:
                    log['reason'] = '사유 없음'
                # reason이 문자열이면 그대로 사용
                elif isinstance(log['reason'], str):
                    log['reason'] = log['reason']
                # 다른 형식이면 문자열로 변환
                else:
                    log['reason'] = str(log['reason'])
            
            return {"status": "success", "data": logs}
            
    except Exception as e:
        print(f"로그 처리 중 에러: {str(e)}")  # 디버그용
        return JSONResponse({
            "status": "error",
            "message": f"로그 읽기 실패: {str(e)}"
        }, status_code=500)

@app.get("/{filename}.html", response_class=HTMLResponse)
async def read_html(request: Request, filename: str):
    try:
        return templates.TemplateResponse(f"{filename}.html", {
            "request": request
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"서버 오류: {str(e)}"
        })

# Domain CRUD
@app.get("/api/domains")
async def get_domains():
    with db.get_cursor() as cursor:
        cursor.execute("SELECT * FROM domain ORDER BY created_at DESC")
        domains = cursor.fetchall()
        return {"status": "success", "data": domains}

@app.post("/api/domains")
async def create_domain(list_type: str = Form(...), domain: str = Form(...), description: Optional[str] = Form(None)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO domain (list_type, domain, description, is_active) VALUES (%s, %s, %s, 1)",
                (list_type, domain, description)
            )
            return {"status": "success", "message": "도메인이 추가되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.put("/api/domains/{idx}")
async def update_domain(idx: int, list_type: str = Form(...), domain: str = Form(...), description: Optional[str] = Form(None)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE domain SET list_type = %s, domain = %s, description = %s WHERE idx = %s",
                (list_type, domain, description, idx)
            )
            return {"status": "success", "message": "도메인이 수정되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.put("/api/domains/{idx}/toggle")
async def toggle_domain(idx: int, data: Dict = Body(...)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE domain SET is_active = %s WHERE idx = %s",
                (data.get('is_active'), idx)
            )
            return {"status": "success", "message": "도메인 상태가 변경되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.delete("/api/domains/{idx}")
async def delete_domain(idx: int):
    try:
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM domain WHERE idx = %s", (idx,))
            return {"status": "success", "message": "도메인이 삭제되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

# CIDR CRUD
@app.get("/api/cidrs")
async def get_cidrs():
    with db.get_cursor() as cursor:
        cursor.execute("SELECT * FROM cidr ORDER BY created_at DESC")
        cidrs = cursor.fetchall()
        return {"status": "success", "data": cidrs}

@app.post("/api/cidrs")
async def create_cidr(list_type: str = Form(...), cidr: str = Form(...), description: Optional[str] = Form(None)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO cidr (list_type, cidr, description) VALUES (%s, %s, %s)",
                (list_type, cidr, description)
            )
            return {"status": "success", "message": "CIDR이 추가되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.put("/api/cidrs/{idx}")
async def update_cidr(idx: int, list_type: str = Form(...), cidr: str = Form(...), description: Optional[str] = Form(None)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE cidr SET list_type = %s, cidr = %s, description = %s WHERE idx = %s",
                (list_type, cidr, description, idx)
            )
            return {"status": "success", "message": "CIDR이 수정되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.delete("/api/cidrs/{idx}")
async def delete_cidr(idx: int):
    try:
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM cidr WHERE idx = %s", (idx,))
            return {"status": "success", "message": "CIDR이 삭제되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.put("/api/cidrs/{idx}/toggle")
async def toggle_cidr(idx: int, data: Dict = Body(...)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE cidr SET is_active = %s WHERE idx = %s",
                (data.get('is_active'), idx)
            )
            return {"status": "success", "message": "CIDR 상태가 변경되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

# Hide CRUD
@app.get("/api/hides")
async def get_hides():
    with db.get_cursor() as cursor:
        cursor.execute("SELECT * FROM hide ORDER BY created_at DESC")
        hides = cursor.fetchall()
        return {"status": "success", "data": hides}

@app.post("/api/hides")
async def create_hide(domain: str = Form(...), description: Optional[str] = Form(None)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO hide (domain, description, is_active) VALUES (%s, %s, 1)",
                (domain, description)
            )
            return {"status": "success", "message": "도메인이 추가되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.put("/api/hides/{idx}")
async def update_hide(idx: int, domain: str = Form(...), description: Optional[str] = Form(None)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE hide SET domain = %s, description = %s WHERE idx = %s",
                (domain, description, idx)
            )
            return {"status": "success", "message": "도메인이 수정되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.put("/api/hides/{idx}/toggle")
async def toggle_hide(idx: int, data: Dict = Body(...)):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE hide SET is_active = %s WHERE idx = %s",
                (data.get('is_active'), idx)
            )
            return {"status": "success", "message": "숨김 도메인 상태가 변경되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.delete("/api/hides/{idx}")
async def delete_hide(idx: int):
    try:
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM hide WHERE idx = %s", (idx,))
            return {"status": "success", "message": "도메인이 삭제되었습니다."}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))
    
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)