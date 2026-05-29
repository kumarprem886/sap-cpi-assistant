from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import iflow, mapping, groovy, xslt, chat, documents, cpi_connect, settings
from routers import auth as auth_router, users as users_router
from database import init_db

app = FastAPI(title="SAP CPI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware — protects all /api/* except login/register
OPEN_PATHS = {"/", "/health", "/api/auth/login", "/api/auth/register"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.url.path in OPEN_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    from services.auth_service import decode_token
    from jose import JWTError
    try:
        payload = decode_token(auth_header[7:])
        request.state.user_id = payload.get("sub")
    except JWTError:
        return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

    return await call_next(request)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(iflow.router)
app.include_router(mapping.router)
app.include_router(groovy.router)
app.include_router(xslt.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(cpi_connect.router)
app.include_router(settings.router)


@app.get("/")
def root():
    return {"status": "SAP CPI Assistant API is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
