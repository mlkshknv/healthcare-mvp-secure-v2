from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from app.database import engine, Base
from app.auth import router as auth_router
from app.medical import router as medical_router
from app.logging_config import logger
from app.init_db import init_db

load_dotenv()

# Создаём таблицы и начальные данные
Base.metadata.create_all(bind=engine)
init_db()

# 1. СОЗДАЁМ ПРИЛОЖЕНИЕ
app = FastAPI(title="Healthcare MVP")

# 2. MIDDLEWARE ДЛЯ ЗАЩИТЫ ОТ БОЛЬШИХ ЗАПРОСОВ
class SizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.headers.get("content-length"):
            size = int(request.headers["content-length"])
            if size > 1024 * 1024:  # 1 МБ
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        return await call_next(request)

app.add_middleware(SizeLimitMiddleware)

# 3. ПОДКЛЮЧАЕМ СТАТИКУ И ШАБЛОНЫ
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 4. ПОДКЛЮЧАЕМ РОУТЕРЫ API
app.include_router(auth_router)
app.include_router(medical_router)

# 5. ЭНДПОИНТЫ ДЛЯ WEB-СТРАНИЦ
@app.get("/")
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard")
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/appointments")
def appointments_page(request: Request):
    return templates.TemplateResponse("appointments.html", {"request": request})

@app.get("/records")
def records_page(request: Request):
    return templates.TemplateResponse("records.html", {"request": request})

@app.get("/report")
def report_page(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})

@app.get("/users")
def users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})

# 6. MIDDLEWARE ДЛЯ ЛОГИРОВАНИЯ ЗАПРОСОВ
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response