from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import iflow, mapping, groovy, xslt, chat, documents, cpi_connect, settings

app = FastAPI(
    title="SAP CPI Assistant API",
    description="AI-powered assistant for SAP Cloud Platform Integration development",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
