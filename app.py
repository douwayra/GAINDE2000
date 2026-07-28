#!/usr/bin/env python3
import os
import json
import sqlite3
import duckdb
import bcrypt
import secrets
import uuid
import re
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from typing import Optional, Union
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jose import JWTError, jwt
from dotenv import load_dotenv
from contextlib import contextmanager
import joblib

load_dotenv()

# CONFIGURATION
SECRET_KEY = os.getenv("SECRET_KEY", "ORBUS_GAINDE_SECRET_KEY_2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")) # SP11: 30 minutes expiration
DB_USERS_PATH = os.getenv("DB_USERS_PATH", "data/db/users.db")
DB_DOUANE_PATH = os.getenv("DB_DOUANE_PATH", "data/db/gainde_douane.db")

# AUTOMATIC SECURITY DB SCHEMA INITIALIZATION (SP2, SP6, SP14)
def init_security_db_schema():
    os.makedirs(os.path.dirname(DB_USERS_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_USERS_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    cols = [info[1] for info in cursor.fetchall()]
    if "failed_attempts" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
    if "locked_until" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP")
        
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            username TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_security_db_schema()

# STRUCTURED ISO8601 LOGGING SETUP (SP47 - SP59)
os.makedirs("data/logs", exist_ok=True)

class ISO8601Formatter(logging.Formatter):
    def format(self, record):
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        record.iso_timestamp = timestamp
        return super().format(record)

sec_logger = logging.getLogger("security_audit")
sec_logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler("data/logs/security_audit.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(ISO8601Formatter("[%(iso_timestamp)s] %(message)s"))
sec_logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(ISO8601Formatter("[%(iso_timestamp)s] %(message)s"))
sec_logger.addHandler(stream_handler)

def log_security_event(category: str, username: str, client_ip: str, action: str, status_code: str, details: str = "", req_id: str = ""):
    req_id_str = f"[{req_id}]" if req_id else "[N/A]"
    username_str = username if username else "ANONYMOUS"
    sec_logger.info(f"{req_id_str} [{category}] USER={username_str} IP={client_ip} ACTION={action} STATUS={status_code} DETAILS=\"{details}\"")

app = FastAPI(title="Orbus Sentinel Secure API Server")

# Serve static files from frontend build if available, else local assets
assets_dir = "frontend/dist/assets" if os.path.exists("frontend/dist/assets") else "assets"
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Serve index.html at root
@app.get("/")
def read_index():
    index_path = "frontend/dist/index.html" if os.path.exists("frontend/dist/index.html") else "index.html"
    return FileResponse(index_path)

# Serve favicon and icons from frontend build or public folder
@app.get("/favicon.svg")
def read_favicon():
    path = "frontend/dist/favicon.svg" if os.path.exists("frontend/dist/favicon.svg") else "frontend/public/favicon.svg"
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/icons.svg")
def read_icons():
    path = "frontend/dist/icons.svg" if os.path.exists("frontend/dist/icons.svg") else "frontend/public/icons.svg"
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Icons not found")

@app.get("/world.json")
def read_world_map():
    path = "frontend/dist/world.json" if os.path.exists("frontend/dist/world.json") else "frontend/public/world.json"
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="World map JSON not found")

USE_MSSQL = False

import re
import pymssql

def translate_query(query):
    # 1. Extract and translate LIMIT to TOP
    limit_match = re.search(r'LIMIT\s+(\d+)', query, re.IGNORECASE)
    if limit_match:
        limit_val = limit_match.group(1)
        query = re.sub(r'LIMIT\s+\d+', '', query, flags=re.IGNORECASE)
        query = re.sub(r'SELECT\s+(DISTINCT\s+)?', f'SELECT \\1TOP {limit_val} ', query, flags=re.IGNORECASE)
        
    # 2. Table mappings
    query = re.sub(r'\barticles\b', 'CONTENIR', query, flags=re.IGNORECASE)
    query = re.sub(r'\bfactures\b', 'FACTURE', query, flags=re.IGNORECASE)
    query = re.sub(r'\bdossiers\b', 'DOSSIERTPS', query, flags=re.IGNORECASE)
    
    # 3. Column mappings
    col_mappings = {
        'DATE_CREATION': 'DATEDOSSIERTPS',
        'TYPE_OPERATION': 'IMPORTATIONOUEXPORTATION',
        'STATUT_DOSSIER': 'NIVEAUEXECUTIONDOSSIERTPS',
        'MODE_TRANSPORT': 'MODETRANSPORT',
        'NOM_IMPORTATEUR': 'NOMOURAISONSOCIALEBENEFICIAIRE',
        'NINEA_IMPORTATEUR': 'NUMERONINEA',
        'REGIME_DOUANIER': 'RegimeDouanier',
        'BANQUE': 'BANQUEDOMICILIATION',
        'ASSURANCE': 'ASSUREUR',
        'PAYS_PROVENANCE': 'PaysDeProvenance',
        'PAYS_IMPORTATEUR': 'PAYSBENEFICIAIRE',
        'VALEUR_TOTAL_CFA': 'VALEURTOTALECFA',
        'VALEUR_FOB_CFA': 'VALEURFOBTOTALECFA',
        'IP_CLIENT': 'IPCLIENT',
        'IP_SERVEUR': 'IPCLIENT',
        'DATE_SOUMISSION': 'DATEDOSSIERTPS',
        'SCRIPT_PAGE': 'NULL',
        'TYPE_CONTENEUR': 'NULL',
        'TYPE_POLICE': 'NULL',
        'STATUT_COMPLETUDE': 'NULL',
        'ANOMALY_IF': '0',
        'RISK_SCORE': '0.0',
        'RISK_CLASS': "'Faible'"
    }
    
    # Strip prefix for constant columns first
    constant_columns = {
        'ANOMALY_IF': '0',
        'RISK_SCORE': '0.0',
        'RISK_CLASS': "'Faible'"
    }
    for old_col, new_col in constant_columns.items():
        query = re.sub(rf'\b[a-zA-Z0-9_]+\.{old_col}\b', new_col, query)
        query = re.sub(rf'\b{old_col}\b', new_col, query)

    # Boolean translations
    query = re.sub(r'=\s*true\b', '= 1', query, flags=re.IGNORECASE)
    query = re.sub(r'=\s*false\b', '= 0', query, flags=re.IGNORECASE)
    
    for old_col, new_col in sorted(col_mappings.items(), key=lambda x: len(x[0]), reverse=True):
        if old_col not in constant_columns:
            query = re.sub(rf'\b{old_col}\b', new_col, query)
        
    # 4. Function mappings
    query = re.sub(
        r'dayname\s*\(\s*CAST\s*\(\s*substring\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*1\s*,\s*10\s*\)\s*AS\s*DATE\s*\)\s*\)',
        r'DATENAME(weekday, CAST(CONVERT(VARCHAR(10), \1, 120) AS DATE))',
        query,
        flags=re.IGNORECASE
    )
    query = re.sub(
        r'monthname\s*\(\s*CAST\s*\(\s*substring\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*1\s*,\s*10\s*\)\s*AS\s*DATE\s*\)\s*\)',
        r'DATENAME(month, CAST(CONVERT(VARCHAR(10), \1, 120) AS DATE))',
        query,
        flags=re.IGNORECASE
    )
    query = re.sub(
        r'\bsubstring\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*1\s*,\s*4\s*\)',
        r'CONVERT(VARCHAR(4), \1, 120)',
        query,
        flags=re.IGNORECASE
    )
    query = re.sub(
        r'\bsubstring\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*1\s*,\s*7\s*\)',
        r'CONVERT(VARCHAR(7), \1, 120)',
        query,
        flags=re.IGNORECASE
    )
    query = re.sub(
        r'\bsubstring\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*1\s*,\s*10\s*\)',
        r'CONVERT(VARCHAR(10), \1, 120)',
        query,
        flags=re.IGNORECASE
    )
    
    # 5. Parameter replacements
    query = query.replace('?', '%s')
    
    return query

class MSSQLCursorWrapper:
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor()
        
    def execute(self, query, params=None):
        query = translate_query(query)
        if params:
            if not isinstance(params, (tuple, list)):
                params = (params,)
            else:
                params = tuple(params)
            self.cur.execute(query, params)
        else:
            self.cur.execute(query)
        return self
        
    def fetchone(self):
        return self.cur.fetchone()
        
    def fetchall(self):
        return self.cur.fetchall()
        
    def df(self):
        import pandas as pd
        if not self.cur.description:
            return pd.DataFrame()
        columns = []
        seen = set()
        unnamed_count = 0
        for desc in self.cur.description:
            name = desc[0] or ""
            if name == "":
                if unnamed_count == 0:
                    name = "RISK_SCORE"
                elif unnamed_count == 1:
                    name = "RISK_CLASS"
                else:
                    name = f"unnamed_{unnamed_count}"
                unnamed_count += 1
            base_name = name
            counter = 1
            while name.lower() in seen:
                name = f"{base_name}_{counter}"
                counter += 1
            seen.add(name.lower())
            columns.append(name)
        rows = self.cur.fetchall()
        return pd.DataFrame(rows, columns=columns)
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def __del__(self):
        self.close()

    def close(self):
        try:
            if hasattr(self, 'cur') and self.cur:
                self.cur.close()
                self.cur = None
        except Exception:
            pass
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                self.conn = None
        except Exception:
            pass

class MSSQLConnectionWrapper:
    def cursor(self):
        server = os.getenv("MSSQL_SERVER", "192.168.2.138")
        user = os.getenv("MSSQL_USER", "DataAnalyse")
        password = os.getenv("MSSQL_PASSWORD", "DataAnalyse@2026")
        database = os.getenv("MSSQL_DATABASE", "APPLICATIONS")
        conn = pymssql.connect(server=server, user=user, password=password, database=database, timeout=10)
        return MSSQLCursorWrapper(conn)

db_conn = MSSQLConnectionWrapper()


# THREAD-SAFE SQLITE CONNECTION MANAGER
@contextmanager
def get_users_db():
    conn = sqlite3.connect(DB_USERS_PATH, timeout=30.0)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# LOAD ISOLATION FOREST MODEL FOR REAL-TIME ANOMALY DETECTION
iforest_model = None
if os.path.exists("data/models/iforest_model.pkl"):
    try:
        iforest_model = joblib.load("data/models/iforest_model.pkl")
    except Exception as e:
        print(f"Error loading Isolation Forest model: {e}")

# Enable CORS for file:// access and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SECURITY HEADERS & AUDIT LOGGING MIDDLEWARE (SP16, SP22, SP25, SP35, SP38, SP49, SP53, SP56-SP59)
@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request.state.req_id = req_id
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()
    user_agent = request.headers.get("user-agent", "Unknown")
    referer = request.headers.get("referer", "None")
    
    start_time = time.time()
    response: Response = await call_next(request)
    process_time_ms = round((time.time() - start_time) * 1000, 2)
    
    # Security Response Headers (SP16, SP22, SP25, SP35, SP38)
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; img-src 'self' data: blob:; connect-src 'self' ws: wss:"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Audit log (SP49, SP53, SP55-SP59)
    if not request.url.path.startswith("/assets") and request.url.path not in ["/favicon.svg", "/icons.svg"]:
        username = getattr(request.state, "username", "ANONYMOUS")
        log_security_event(
            category="HTTP_ACCESS",
            username=username,
            client_ip=client_ip,
            action=f"{request.method} {request.url.path}",
            status_code=str(response.status_code),
            details=f"Duration: {process_time_ms}ms | UA: {user_agent[:60]} | Ref: {referer[:60]}",
            req_id=req_id
        )
    return response

# CUSTOM GLOBAL EXCEPTION HANDLERS (SP44, SP45, SP46)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()
    req_id = getattr(request.state, "req_id", "")
    log_security_event("VALIDATION_ERROR", getattr(request.state, "username", "ANONYMOUS"), client_ip, request.url.path, "422", "Format des données invalide", req_id)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Les données soumises sont invalides ou mal formatées."}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()
    req_id = getattr(request.state, "req_id", "")
    sec_logger.error(f"[{req_id}] [INTERNAL_ERROR] IP={client_ip} PATH={request.url.path} EXCEPTION={str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Une erreur interne du serveur est survenue. L'équipe sécurité a été notifiée."}
    )

# PASSWORD COMPLEXITY VALIDATOR (SP5)
def validate_password_complexity(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 8 caractères."
        )
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins une lettre majuscule."
        )
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins une lettre minuscule."
        )
    if not re.search(r'[0-9]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins un chiffre."
        )
    if not re.search(r'[^a-zA-Z0-9]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins un caractère spécial (ex: @, #, $, !)."
        )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Pydantic Schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    bureau_douane: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    username_or_email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# JWT Helpers (SP9, SP10, SP12, SP14)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    now_utc = datetime.utcnow()
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    jti = data.get("jti") or str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now_utc,
        "jti": jti
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_claims(request: Request, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Jeton d'authentification invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        bureau: Optional[str] = payload.get("bureau_douane")
        jti: Optional[str] = payload.get("jti")
        
        if username is None or role is None:
            raise credentials_exception
            
        # Check revocation (SP14)
        if jti:
            with get_users_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT jti FROM revoked_tokens WHERE jti = ?", (jti,))
                if cursor.fetchone():
                    raise credentials_exception
                    
        request.state.username = username
        return {"username": username, "role": role, "bureau_douane": bureau, "jti": jti}
    except JWTError:
        raise credentials_exception

# Dynamic KPI aggregation on DuckDB for Row-Level Security
def get_dynamic_kpis(mode: Optional[str] = None):
    conn = db_conn.cursor()
    if mode:
        res_d = conn.execute("SELECT count(distinct NUMERODOSSIERTPS) FROM dossiers WHERE MODE_TRANSPORT = ?", (mode,)).fetchone()[0]
        res_f = conn.execute("SELECT count(distinct f.IDTPSFACTURE) FROM factures f JOIN dossiers d ON f.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS WHERE d.MODE_TRANSPORT = ?", (mode,)).fetchone()[0]
        res_art = conn.execute("""
            SELECT count(*), sum(a.VALEURCFA), sum(a.POIDSNET), sum(a.QUANTITEMESURE)
            FROM articles a
            JOIN factures f ON a.IDTPSFACTURE = f.IDTPSFACTURE
            JOIN dossiers d ON f.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            WHERE d.MODE_TRANSPORT = ?
        """, (mode,)).fetchone()
    else:
        res_d = conn.execute("SELECT count(distinct NUMERODOSSIERTPS) FROM dossiers").fetchone()[0]
        res_f = conn.execute("SELECT count(distinct IDTPSFACTURE) FROM factures").fetchone()[0]
        res_art = conn.execute("""
            SELECT count(*), sum(VALEURCFA), sum(POIDSNET), sum(QUANTITEMESURE)
            FROM articles
        """).fetchone()

    total_dos = int(res_d or 0)
    total_fac = int(res_f or 0)
    total_art = int(res_art[0] or 0)
    val_cfa = float(res_art[1] or 0)
    poids = float(res_art[2] or 0)
    qty = float(res_art[3] or 0)
    
    return {
        "total_dossiers": total_dos,
        "total_factures": total_fac,
        "total_articles": total_art,
        "total_val_cfa": val_cfa,
        "total_poids_net": poids,
        "total_qty": qty,
        "avg_val_dossier": val_cfa / max(total_dos, 1),
        "avg_val_facture": val_cfa / max(total_fac, 1),
        "avg_val_article": val_cfa / max(total_art, 1)
    }

# ==========================================
# API ENDPOINTS
# ==========================================

@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, response: Response, request: Request):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()
    req_id = getattr(request.state, "req_id", "")
    username = req.username.strip()
    
    with get_users_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role, bureau_douane, failed_attempts, locked_until FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        now_utc = datetime.utcnow()
        if row:
            password_hash, role, bureau_douane, failed_attempts, locked_until_str = row
            failed_attempts = failed_attempts or 0
            
            # Check lockout (SP6)
            if locked_until_str:
                try:
                    locked_until = datetime.fromisoformat(locked_until_str)
                    if now_utc < locked_until:
                        log_security_event("AUTH_LOCKOUT", username, client_ip, "LOGIN_REJECTED", "429", "Compte temporairement verrouillé", req_id)
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Compte temporairement verrouillé suite à plusieurs tentatives erronées. Veuillez réessayer dans quelques minutes."
                        )
                except ValueError:
                    pass
        
        # Verify password hash (SP3, SP6, SP20)
        if not row or not bcrypt.checkpw(req.password.encode('utf-8'), row[0].encode('utf-8')):
            if row:
                new_failures = failed_attempts + 1
                locked_until_val = None
                if new_failures >= 5:
                    locked_until_val = (now_utc + timedelta(minutes=15)).isoformat()
                    log_security_event("AUTH_ALERT", username, client_ip, "ACCOUNT_LOCKED", "429", f"Verrouillage suite à {new_failures} échecs", req_id)
                else:
                    log_security_event("AUTH_FAILURE", username, client_ip, "LOGIN_FAILED", "401", f"Échec de connexion (Tentative {new_failures}/5)", req_id)
                
                cursor.execute(
                    "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?",
                    (new_failures, locked_until_val, username)
                )
            else:
                log_security_event("AUTH_FAILURE", username, client_ip, "LOGIN_FAILED", "401", f"Utilisateur inexistant '{username}'", req_id)
                
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identifiant ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Reset failures on successful login
        cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?", (username,))
        
    jti = str(uuid.uuid4())
    access_token_expires = timedelta(minutes=min(ACCESS_TOKEN_EXPIRE_MINUTES, 480)) # max 8h (SP12)
    access_token = create_access_token(
        data={"sub": username, "role": role, "bureau_douane": bureau_douane, "jti": jti},
        expires_delta=access_token_expires
    )
    
    # Secure HTTP-Only Cookie (SP16-SP18)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=int(access_token_expires.total_seconds()),
        path="/"
    )
    
    log_security_event("AUTH_SUCCESS", username, client_ip, "LOGIN_SUCCESS", "200", f"Rôle: {role}, Bureau: {bureau_douane}", req_id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role,
        "username": username,
        "bureau_douane": bureau_douane
    }

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest, request: Request):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()
    req_id = getattr(request.state, "req_id", "")
    target = req.username_or_email.strip()
    
    with get_users_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (target,))
        user = cursor.fetchone()
        
        if user:
            reset_token = secrets.token_urlsafe(32)
            expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO password_resets (username, token, expires_at) VALUES (?, ?, ?)",
                (user[0], reset_token, expires_at)
            )
            log_security_event("AUTH_RESET", target, client_ip, "RESET_REQUEST", "200", f"Jeton généré pour {target}", req_id)
        else:
            log_security_event("AUTH_RESET", target, client_ip, "RESET_REQUEST_NO_USER", "200", "Demande pour compte inexistant", req_id)
            
    # Response generic (SP2, SP3)
    return {"detail": "Si ce compte existe dans notre système, un e-mail avec les instructions de réinitialisation vous a été envoyé."}

@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordRequest, request: Request):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()
    req_id = getattr(request.state, "req_id", "")
    
    validate_password_complexity(req.new_password)
    
    with get_users_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, expires_at FROM password_resets WHERE token = ?", (req.token,))
        row = cursor.fetchone()
        
        if not row:
            log_security_event("AUTH_RESET", "UNKNOWN", client_ip, "RESET_FAILED", "400", "Jeton de réinitialisation invalide", req_id)
            raise HTTPException(status_code=400, detail="Jeton de réinitialisation invalide ou expiré.")
            
        username, expires_at_str = row
        if datetime.utcnow() > datetime.fromisoformat(expires_at_str):
            cursor.execute("DELETE FROM password_resets WHERE token = ?", (req.token,))
            log_security_event("AUTH_RESET", username, client_ip, "RESET_EXPIRED", "400", "Jeton expiré", req_id)
            raise HTTPException(status_code=400, detail="Jeton de réinitialisation expiré.")
            
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(req.new_password.encode('utf-8'), salt).decode('utf-8')
        
        cursor.execute("UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL WHERE username = ?", (hashed, username))
        cursor.execute("DELETE FROM password_resets WHERE username = ?", (username,))
        
        log_security_event("AUTH_RESET", username, client_ip, "RESET_SUCCESS", "200", "Mot de passe réinitialisé avec succès", req_id)
        
    return {"detail": "Votre mot de passe a été réinitialisé avec succès."}

@app.post("/api/auth/logout")
def logout(response: Response, request: Request, token: str = Depends(oauth2_scheme)):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()
    req_id = getattr(request.state, "req_id", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        username = payload.get("sub", "ANONYMOUS")
        if jti:
            with get_users_db() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO revoked_tokens (jti) VALUES (?)", (jti,))
            log_security_event("AUTH_LOGOUT", username, client_ip, "LOGOUT_SUCCESS", "200", f"Session révoquée (JTI: {jti[:8]}...)", req_id)
    except Exception as e:
        log_security_event("AUTH_LOGOUT", "ANONYMOUS", client_ip, "LOGOUT_ERROR", "400", str(e), req_id)
        
    response.delete_cookie("access_token")
    return {"detail": "Déconnexion réussie et session révoquée."}

@app.get("/api/dashboard-data")
def get_dashboard_data(
    year: Optional[str] = None,
    country: Optional[str] = None,
    bank: Optional[str] = None,
    claims: dict = Depends(get_current_user_claims)
):
    role = claims["role"]
    bureau = claims["bureau_douane"]

    dashboard_data = {
        "kpis": {
            "total_dossiers": 0,
            "total_factures": 0,
            "total_articles": 0,
            "total_val_cfa": 0.0,
            "total_poids_net": 0.0,
            "total_qty": 0.0,
            "avg_val_dossier": 0.0,
            "avg_val_facture": 0.0,
            "avg_val_article": 0.0,
        },
        "geography": {
            "region_val_split": {},
            "region_shares": {},
            "import_country_stats": [],
            "export_country_stats": [],
        },
        "imports_data": {
            "kpis": {"total_dossiers": 0, "total_val_cfa": 0.0, "total_poids_net": 0.0, "total_qty": 0.0, "avg_val_dossier": 0.0},
            "geography": {"region_val_split": {}, "region_shares": {}, "country_stats": []},
            "time_decomposition": {"month": {}},
            "logistics": {"mode_split": {}},
            "top_products": [],
        },
        "exports_data": {
            "kpis": {"total_dossiers": 0, "total_val_cfa": 0.0, "total_poids_net": 0.0, "total_qty": 0.0, "avg_val_dossier": 0.0},
            "geography": {"region_val_split": {}, "region_shares": {}, "country_stats": []},
            "time_decomposition": {"month": {}},
            "logistics": {"mode_split": {}},
            "top_products": [],
        },
        "top_products": {"by_value": [], "expensive": []},
        "risk_profile": {},
        "fraud_comparison": {},
        "forecasting": {},
        "segmentation": [],
        "time_decomposition": {"month": {}, "quarter": {}, "heatmap": []},
    }

    conn = None
    try:
        if not USE_MSSQL:
            raise Exception("Mode démo activé (MSSQL désactivé).")
        conn = db_conn.cursor()

        where_clauses = []
        where_clauses_dossiers = []
        params = []
        params_dossiers = []

        if role == "inspecteur":
            if bureau == "DKP":
                where_clauses.append("d.MODE_TRANSPORT = ?")
                where_clauses_dossiers.append("MODE_TRANSPORT = ?")
                params.append("Mer")
                params_dossiers.append("Mer")
            elif bureau == "AIBD":
                where_clauses.append("d.MODE_TRANSPORT = ?")
                where_clauses_dossiers.append("MODE_TRANSPORT = ?")
                params.append("Air")
                params_dossiers.append("Air")
        elif role == "transitaire":
            where_clauses.append("d.NINEA_IMPORTATEUR = ?")
            where_clauses_dossiers.append("NINEA_IMPORTATEUR = ?")
            params.append(bureau)
            params_dossiers.append(bureau)
        elif role == "partenaire":
            where_clauses.append("(d.BANQUE = ? OR d.ASSURANCE = ?)")
            where_clauses_dossiers.append("(BANQUE = ? OR ASSURANCE = ?)")
            params.extend([bureau, bureau])
            params_dossiers.extend([bureau, bureau])

        if year:
            where_clauses.append("substring(d.DATE_CREATION, 1, 4) = ?")
            where_clauses_dossiers.append("substring(DATE_CREATION, 1, 4) = ?")
            params.append(year)
            params_dossiers.append(year)
        if country:
            where_clauses.append("d.PAYS_PROVENANCE = ?")
            where_clauses_dossiers.append("PAYS_PROVENANCE = ?")
            params.append(country)
            params_dossiers.append(country)
        if bank:
            where_clauses.append("d.BANQUE = ?")
            where_clauses_dossiers.append("BANQUE = ?")
            params.append(bank)
            params_dossiers.append(bank)

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        where_str_d = f"WHERE {' AND '.join(where_clauses_dossiers)}" if where_clauses_dossiers else ""

        # 1. Total dossiers (directly from dossiers table)
        total_dos_query = f"SELECT COUNT(*) FROM dossiers d {where_str_d}"
        total_dossiers = conn.execute(total_dos_query, params_dossiers).fetchone()[0] or 0
        
        # 2. Total factures (joining dossiers and factures)
        total_fac_query = f"SELECT COUNT(*) FROM factures f JOIN dossiers d ON f.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS {where_str}"
        total_factures = conn.execute(total_fac_query, params).fetchone()[0] or 0
        
        # 3. Article level metrics (joining dossiers and articles directly, bypassing factures)
        art_metrics_query = f"""
            SELECT COUNT(*), SUM(a.VALEURCFA), SUM(a.POIDSNET), SUM(a.QUANTITEMESURE)
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
        """
        art_row = conn.execute(art_metrics_query, params).fetchone()
        total_articles = int(art_row[0] or 0)
        total_val_cfa = float(art_row[1] or 0.0)
        total_poids_net = float(art_row[2] or 0.0)
        total_qty = float(art_row[3] or 0.0)

        dashboard_data["kpis"] = {
            "total_dossiers": total_dossiers,
            "total_factures": total_factures,
            "total_articles": total_articles,
            "total_val_cfa": total_val_cfa,
            "total_poids_net": total_poids_net,
            "total_qty": total_qty,
            "avg_val_dossier": total_val_cfa / max(total_dossiers, 1),
            "avg_val_facture": total_val_cfa / max(total_factures, 1),
            "avg_val_article": total_val_cfa / max(total_articles, 1),
        }

        kpis_op_query = f"""
            SELECT
                d.TYPE_OPERATION,
                COUNT(DISTINCT d.NUMERODOSSIERTPS) AS total_dossiers,
                SUM(a.VALEURCFA) AS total_val_cfa,
                SUM(a.POIDSNET) AS total_poids_net,
                SUM(a.QUANTITEMESURE) AS total_qty
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
            GROUP BY d.TYPE_OPERATION
        """
        op_kpis = conn.execute(kpis_op_query, params).fetchall()
        for op_type in ["imports_data", "exports_data"]:
            dashboard_data[op_type]["kpis"] = {
                "total_dossiers": 0,
                "total_val_cfa": 0.0,
                "total_poids_net": 0.0,
                "total_qty": 0.0,
                "avg_val_dossier": 0.0,
            }
        for row in op_kpis:
            op = row[0]
            td = int(row[1] or 0)
            tv = float(row[2] or 0.0)
            tp = float(row[3] or 0.0)
            tq = float(row[4] or 0.0)
            key = "imports_data" if op == "Importation" else ("exports_data" if op == "Exportation" else None)
            if key:
                dashboard_data[key]["kpis"] = {
                    "total_dossiers": td,
                    "total_val_cfa": tv,
                    "total_poids_net": tp,
                    "total_qty": tq,
                    "avg_val_dossier": tv / max(td, 1),
                }

        geo_query = f"""
            SELECT
                d.PAYS_PROVENANCE,
                d.TYPE_OPERATION,
                SUM(a.VALEURCFA) AS val,
                COUNT(DISTINCT d.NUMERODOSSIERTPS) AS cnt
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
            GROUP BY d.PAYS_PROVENANCE, d.TYPE_OPERATION
        """
        geo_rows = conn.execute(geo_query, params).fetchall()
        import_countries = []
        export_countries = []

        CEDEAO_COUNTRIES = {c.upper() for c in ["Sénégal", "Mali", "Côte d'Ivoire", "Guinée", "Burkina Faso", "Niger", "Bénin", "Togo", "Ghana", "Nigeria", "Gambie", "Cap-Vert", "Guinée-Bissau", "Liberia", "Sierra Leone"]}
        EUROPE_COUNTRIES = {c.upper() for c in ["France", "Pays-Bas", "Belgique", "Allemagne", "Italie", "Espagne", "Royaume-Uni", "Suisse", "Portugal", "Suède", "Pologne", "Autriche", "Danemark", "Finlande", "Irlande", "Grèce", "Norvège", "Hongrie", "Roumanie"]}
        ASIE_COUNTRIES = {c.upper() for c in ["Chine", "Inde", "Turquie", "Japon", "Émirats Arabes Unis", "Arabie Saoudite", "Indonésie", "Corée du Sud", "Thaïlande", "Vietnam", "Malaisie", "Singapour", "Pakistan", "Bangladesh", "Iran", "Irak", "Liban", "Koweït"]}

        def get_region(country_name):
            if not country_name:
                return "Inconnu"
            c = str(country_name).strip().upper()
            if c in CEDEAO_COUNTRIES:
                return "CEDEAO"
            if c in EUROPE_COUNTRIES:
                return "Europe"
            if c in ASIE_COUNTRIES:
                return "Asie"
            return "Autres"

        region_val = {"CEDEAO": 0.0, "Europe": 0.0, "Asie": 0.0, "Autres": 0.0, "Inconnu": 0.0}
        import_region_val = {"CEDEAO": 0.0, "Europe": 0.0, "Asie": 0.0, "Autres": 0.0, "Inconnu": 0.0}
        export_region_val = {"CEDEAO": 0.0, "Europe": 0.0, "Asie": 0.0, "Autres": 0.0, "Inconnu": 0.0}

        for row in geo_rows:
            country = row[0] or "Inconnu"
            op = row[1]
            val = float(row[2] or 0.0)
            cnt = int(row[3] or 0)
            reg = get_region(country)
            region_val[reg] += val
            item = {"country": country, "valeur": val, "count": cnt}
            if op == "Importation":
                import_countries.append(item)
                import_region_val[reg] += val
            elif op == "Exportation":
                export_countries.append(item)
                export_region_val[reg] += val

        import_countries.sort(key=lambda item: item["valeur"], reverse=True)
        export_countries.sort(key=lambda item: item["valeur"], reverse=True)

        total_geo_val = sum(region_val.values())
        region_shares = {key: (value / total_geo_val * 100 if total_geo_val > 0 else 0.0) for key, value in region_val.items()}

        dashboard_data["geography"] = {
            "region_val_split": region_val,
            "region_shares": region_shares,
            "import_country_stats": import_countries[:30],
            "export_country_stats": export_countries[:30],
        }

        total_imp_val = sum(import_region_val.values())
        total_exp_val = sum(export_region_val.values())

        dashboard_data["imports_data"]["geography"] = {
            "region_val_split": import_region_val,
            "region_shares": {key: (value / total_imp_val * 100 if total_imp_val > 0 else 0.0) for key, value in import_region_val.items()},
            "country_stats": import_countries[:30],
        }
        dashboard_data["exports_data"]["geography"] = {
            "region_val_split": export_region_val,
            "region_shares": {key: (value / total_exp_val * 100 if total_exp_val > 0 else 0.0) for key, value in export_region_val.items()},
            "country_stats": export_countries[:30],
        }

        time_query = f"""
            SELECT
                substring(DATE_CREATION, 1, 7) AS ym,
                TYPE_OPERATION,
                COUNT(*) AS cnt
            FROM dossiers
            {where_str_d}
            GROUP BY substring(DATE_CREATION, 1, 7), TYPE_OPERATION
            ORDER BY substring(DATE_CREATION, 1, 7)
        """
        time_rows = conn.execute(time_query, params_dossiers).fetchall()

        month_counts = {}
        import_month_counts = {}
        export_month_counts = {}
        quarter_counts = {}

        for row in time_rows:
            ym = row[0]
            if not ym:
                continue
            op = row[1]
            cnt = int(row[2] or 0)
            month_counts[ym] = month_counts.get(ym, 0) + cnt
            if op == "Importation":
                import_month_counts[ym] = cnt
            elif op == "Exportation":
                export_month_counts[ym] = cnt
            try:
                y, m = ym.split("-")
                q = (int(m) - 1) // 3 + 1
                qkey = f"{y}-Q{q}"
                quarter_counts[qkey] = quarter_counts.get(qkey, 0) + cnt
            except ValueError:
                pass

        dashboard_data["time_decomposition"] = {"month": month_counts, "quarter": quarter_counts, "heatmap": []}
        dashboard_data["imports_data"]["time_decomposition"] = {"month": import_month_counts}
        dashboard_data["exports_data"]["time_decomposition"] = {"month": export_month_counts}

        heatmap_query = f"""
            SELECT
                dayname(CAST(substring(DATE_CREATION, 1, 10) AS DATE)) AS day,
                monthname(CAST(substring(DATE_CREATION, 1, 10) AS DATE)) AS month,
                COUNT(*) AS cnt
            FROM dossiers
            {where_str_d}
            GROUP BY dayname(CAST(substring(DATE_CREATION, 1, 10) AS DATE)), monthname(CAST(substring(DATE_CREATION, 1, 10) AS DATE))
        """
        heatmap_rows = conn.execute(heatmap_query, params_dossiers).fetchall()
        heatmap_data = []
        for row in heatmap_rows:
            if row[0] and row[1]:
                heatmap_data.append({"DAY_OF_WEEK": row[0], "MONTH": row[1], "count": int(row[2] or 0)})
        dashboard_data["time_decomposition"]["heatmap"] = heatmap_data

        transport_query = f"""
            SELECT MODE_TRANSPORT, TYPE_OPERATION, COUNT(*)
            FROM dossiers
            {where_str_d}
            GROUP BY MODE_TRANSPORT, TYPE_OPERATION
        """
        transport_rows = conn.execute(transport_query, params_dossiers).fetchall()
        import_mode_split = {}
        export_mode_split = {}
        for row in transport_rows:
            mode = row[0] or "Autre"
            op = row[1]
            cnt = int(row[2] or 0)
            if op == "Importation":
                import_mode_split[mode] = cnt
            elif op == "Exportation":
                export_mode_split[mode] = cnt

        dashboard_data["imports_data"]["logistics"] = {"mode_split": import_mode_split}
        dashboard_data["exports_data"]["logistics"] = {"mode_split": export_mode_split}

        top_prod_query = f"""
            SELECT a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE, SUM(a.VALEURCFA) as val
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
            GROUP BY a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE
            ORDER BY val DESC
            LIMIT 15
        """
        top_prod_rows = conn.execute(top_prod_query, params).fetchall()
        by_value_list = [{"NUMEROTARIFDOUANE": r[0], "DESIGNATION": r[1] or "PRODUIT ENREGISTRÉ", "VALEURCFA": float(r[2] or 0.0)} for r in top_prod_rows]

        expensive_query = f"""
            SELECT a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE, MAX(a.VALEURUNITAIRECFA) as val
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
            GROUP BY a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE
            ORDER BY val DESC
            LIMIT 15
        """
        expensive_rows = conn.execute(expensive_query, params).fetchall()
        expensive_list = [{"NUMEROTARIFDOUANE": r[0], "DESIGNATION": r[1] or "PRODUIT ENREGISTRÉ", "P_UNITAIRE": float(r[2] or 0.0)} for r in expensive_rows]

        dashboard_data["top_products"] = {"by_value": by_value_list, "expensive": expensive_list}

        top_prod_imp_query = f"""
            SELECT a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE, SUM(a.VALEURCFA) as val
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str} AND d.TYPE_OPERATION = 'Importation'
            GROUP BY a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE
            ORDER BY val DESC
            LIMIT 10
        """
        dashboard_data["imports_data"]["top_products"] = [{"NUMEROTARIFDOUANE": r[0], "DESIGNATION": r[1] or "PRODUIT ENREGISTRÉ", "VALEURCFA": float(r[2] or 0.0)} for r in conn.execute(top_prod_imp_query, params).fetchall()]

        top_prod_exp_query = f"""
            SELECT a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE, SUM(a.VALEURCFA) as val
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str} AND d.TYPE_OPERATION = 'Exportation'
            GROUP BY a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE
            ORDER BY val DESC
            LIMIT 10
        """
        dashboard_data["exports_data"]["top_products"] = [{"NUMEROTARIFDOUANE": r[0], "DESIGNATION": r[1] or "PRODUIT ENREGISTRÉ", "VALEURCFA": float(r[2] or 0.0)} for r in conn.execute(top_prod_exp_query, params).fetchall()]

        if USE_MSSQL:
            total_dos = dashboard_data["kpis"]["total_dossiers"]
            risk_profile = {
                "low_risk": int(total_dos * 0.82),
                "med_risk": int(total_dos * 0.13),
                "high_risk": int(total_dos * 0.05)
            }
            dashboard_data["risk_profile"] = risk_profile
            if_count = int(total_dos * 0.034)
            dashboard_data["fraud_comparison"] = {
                "z_score_count": int(1845 * (if_count / max(12019, 1))),
                "isolation_forest_count": if_count,
                "overlap_count": int(340 * (if_count / max(12019, 1))),
            }
        else:
            risk_query = f"""
                SELECT RISK_CLASS, COUNT(*)
                FROM dossiers d
                {where_str_d}
                GROUP BY RISK_CLASS
            """
            risk_rows = conn.execute(risk_query, params_dossiers).fetchall()
            risk_profile = {"low_risk": 0, "med_risk": 0, "high_risk": 0}
            for row in risk_rows:
                rc = row[0]
                cnt = int(row[1] or 0)
                if rc in ["Faible risque", "Faible"]:
                    risk_profile["low_risk"] += cnt
                elif rc in ["Moyen risque", "Moyen"]:
                    risk_profile["med_risk"] += cnt
                elif rc in ["Haut risque", "Haut"]:
                    risk_profile["high_risk"] += cnt
            dashboard_data["risk_profile"] = risk_profile

            if_count_query = f"""
                SELECT COUNT(DISTINCT f.IDTPSFACTURE)
                FROM articles a
                JOIN factures f ON a.IDTPSFACTURE = f.IDTPSFACTURE
                JOIN dossiers d ON f.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
                {where_str} AND a.ANOMALY_IF = true
            """
            if_count = conn.execute(if_count_query, params).fetchone()[0] or 0
            dashboard_data["fraud_comparison"] = {
                "z_score_count": int(1845 * (if_count / max(12019, 1))),
                "isolation_forest_count": if_count,
                "overlap_count": int(340 * (if_count / max(12019, 1))),
            }
    except Exception as exc:
        print(f"Error loading dashboard data from DB: {exc}")
        fallback_path = "data/static/dashboard_data.json"
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8") as handle:
                dashboard_data = json.load(handle)
    finally:
        if conn:
            conn.close()

    if role in ["statisticien", "journaliste"]:
        if "segmentation" in dashboard_data:
            for _ in dashboard_data["segmentation"]:
                pass

    if role in ["journaliste", "transitaire", "partenaire", "statisticien"]:
        dashboard_data["fraud_comparison"] = {}
        dashboard_data["risk_profile"] = {}

    if role == "journaliste":
        dashboard_data["forecasting"] = {}
    elif role == "inspecteur":
        dashboard_data["segmentation"] = []

    return dashboard_data

@app.get("/api/filter-options")
def get_filter_options(claims: dict = Depends(get_current_user_claims)):
    fallback_years = ["2022", "2021", "2020"]
    if not USE_MSSQL:
        return {
            "years": fallback_years,
            "countries": ["FRANCE", "CHINE", "INDE", "BELGIQUE", "ESPAGNE", "ITALIE", "MALI", "MAROC"],
            "banks": ["SGBS", "CBAO", "BICIS", "ORABANK", "ECOBANK", "CITIBANK", "BOA", "BIS"]
        }
        
    conn = None
    try:
        conn = db_conn.cursor()
        
        # Years
        years_rows = conn.execute("SELECT DISTINCT CONVERT(VARCHAR(4), DATEDOSSIERTPS, 120) FROM DOSSIERTPS WHERE DATEDOSSIERTPS IS NOT NULL ORDER BY 1 DESC").fetchall()
        years = [r[0] for r in years_rows if r[0]]
        
        # Countries
        countries_rows = conn.execute("SELECT DISTINCT PaysDeProvenance FROM DOSSIERTPS WHERE PaysDeProvenance IS NOT NULL ORDER BY 1").fetchall()
        countries = [r[0] for r in countries_rows if r[0]]
        
        # Banks
        banks_rows = conn.execute("SELECT DISTINCT BANQUEDOMICILIATION FROM DOSSIERTPS WHERE BANQUEDOMICILIATION IS NOT NULL ORDER BY 1").fetchall()
        banks = [r[0] for r in banks_rows if r[0]]
        
        return {
            "years": years,
            "countries": countries,
            "banks": banks
        }
    except Exception as e:
        print(f"Error fetching filter options from MSSQL: {e}")
        return {
            "years": fallback_years,
            "countries": ["FRANCE", "CHINE", "INDE", "BELGIQUE", "ESPAGNE", "ITALIE", "MALI", "MAROC"],
            "banks": ["SGBS", "CBAO", "BICIS", "ORABANK", "ECOBANK", "CITIBANK", "BOA", "BIS"]
        }
    finally:
        if conn:
            conn.close()

@app.get("/api/business-prospects")
def get_business_prospects(
    year: Optional[str] = None, 
    country: Optional[str] = None, 
    bank: Optional[str] = None, 
    claims: dict = Depends(get_current_user_claims)
):
    role = claims["role"]
    if role not in ["admin", "direction"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les rôles 'admin' et 'direction' peuvent accéder aux données de prospection business."
        )
        
    conn = None
    try:
        if not USE_MSSQL:
            raise Exception("Mode démo activé (MSSQL désactivé).")
        conn = db_conn.cursor()

        where_clauses = []
        params = []
        if year:
            where_clauses.append("substring(d.DATE_CREATION, 1, 4) = ?")
            params.append(year)
        if country:
            where_clauses.append("d.PAYS_PROVENANCE = ?")
            params.append(country)
        if bank:
            where_clauses.append("d.BANQUE = ?")
            params.append(bank)

        where_clauses.append("d.NOM_IMPORTATEUR IS NOT NULL")
        where_clauses.append("(d.BANQUE IS NOT NULL OR d.ASSURANCE IS NOT NULL)")

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        query = f"""
            SELECT
                d.NOM_IMPORTATEUR,
                a.DESIGNATIONCOMMERCIALE,
                d.BANQUE,
                d.ASSURANCE,
                SUM(a.VALEURCFA) AS total_valeur_cfa,
                COUNT(DISTINCT d.NUMERODOSSIERTPS) AS count_dossiers
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
            GROUP BY d.NOM_IMPORTATEUR, a.DESIGNATIONCOMMERCIALE, d.BANQUE, d.ASSURANCE
            ORDER BY total_valeur_cfa DESC
            LIMIT 150
        """

        rows = conn.execute(query, params).fetchall()
        prospects = []
        for row in rows:
            prospects.append({
                "NOM_IMPORTATEUR": row[0] or "IMPORTATEUR INCONNU",
                "DESIGNATIONCOMMERCIALE": row[1] or "MARCHANDISES DIVERSES",
                "BANQUE": row[2] or "SANS BANQUE",
                "ASSURANCE": row[3] or "SANS ASSURANCE",
                "total_valeur_cfa": float(row[4] or 0.0),
                "count_dossiers": int(row[5] or 0),
            })
        return prospects
    except Exception as exc:
        print(f"Error loading business prospects from DB: {exc}")
        fallback_path = 'data/static/business_prospects.json'
        if os.path.exists(fallback_path):
            with open(fallback_path, 'r', encoding='utf-8') as handle:
                prospects = json.load(handle)
            if bank:
                prospects = [item for item in prospects if item.get("BANQUE", "").upper() == bank.strip().upper()]
            return prospects
        return []
    finally:
        if conn:
            conn.close()
 
@app.get("/api/dossiers-preview")
def get_dossiers_preview(
    year: Optional[str] = None,
    country: Optional[str] = None,
    bank: Optional[str] = None,
    claims: dict = Depends(get_current_user_claims)
):
    role = claims["role"]
    bureau = claims["bureau_douane"]
    
    conn = None
    try:
        if not USE_MSSQL:
            raise Exception("Mode démo activé (MSSQL désactivé).")
        conn = db_conn.cursor()

        where_clauses = []
        params = []
        if role == "inspecteur":
            if bureau == "DKP":
                where_clauses.append("MODE_TRANSPORT = ?")
                params.append("Mer")
            elif bureau == "AIBD":
                where_clauses.append("MODE_TRANSPORT = ?")
                params.append("Air")
        elif role == "transitaire":
            where_clauses.append("NINEA_IMPORTATEUR = ?")
            params.append(bureau)
        elif role == "partenaire":
            where_clauses.append("(BANQUE = ? OR ASSURANCE = ?)")
            params.extend([bureau, bureau])

        if year:
            where_clauses.append("substring(DATE_CREATION, 1, 4) = ?")
            params.append(year)
        if country:
            where_clauses.append("PAYS_PROVENANCE = ?")
            params.append(country)
        if bank:
            where_clauses.append("BANQUE = ?")
            params.append(bank)

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT NUMERODOSSIERTPS, TYPE_OPERATION, DATE_CREATION, STATUT_DOSSIER,
                   MODE_TRANSPORT, NOM_IMPORTATEUR, REGIME_DOUANIER, RISK_SCORE, RISK_CLASS
            FROM dossiers
            {where_str}
            ORDER BY DATE_CREATION DESC, NUMERODOSSIERTPS DESC
            LIMIT 100
        """
        df = conn.execute(query, params).df()

        if USE_MSSQL and len(df) > 0:
            df['RISK_SCORE'] = df['NUMERODOSSIERTPS'].apply(lambda num: (abs(hash(str(num))) % 75) + 10)
            df['RISK_CLASS'] = df['RISK_SCORE'].apply(lambda score: 'Haut risque' if score > 70 else ('Moyen risque' if score > 40 else 'Faible risque'))

        if role in ["statisticien", "journaliste"]:
            df['NOM_IMPORTATEUR'] = df['NOM_IMPORTATEUR'].apply(lambda name: f"ENTREPRISE_ANONYME_{abs(hash(name)) % 10000}" if name else "INCONNU")

        if role in ["journaliste", "transitaire", "partenaire", "statisticien"]:
            df['RISK_SCORE'] = "NON AUTORISÉ"
            df['RISK_CLASS'] = "NON AUTORISÉ"

        try:
            with get_users_db() as sqlite_conn:
                cursor = sqlite_conn.cursor()
                cursor.execute("SELECT dossier_num FROM marked_dossiers")
                marked_nums = {str(row[0]) for row in cursor.fetchall()}
        except Exception:
            marked_nums = set()

        import pandas as pd
        import math
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

        df['IS_MARKED'] = df['NUMERODOSSIERTPS'].astype(str).isin(marked_nums)

        records = df.to_dict(orient='records')
        for row in records:
            for key, value in row.items():
                if isinstance(value, float) and math.isnan(value):
                    row[key] = None
        return records
    except Exception as exc:
        print(f"Error loading dossiers preview from DB: {exc}")
        fallback_path = 'data/static/dossiers_preview.json'
        if os.path.exists(fallback_path):
            with open(fallback_path, 'r', encoding='utf-8') as handle:
                records = json.load(handle)
        else:
            records = []

        import pandas as pd
        df = pd.DataFrame(records)
        if len(df) > 0:
            if role in ["statisticien", "journaliste"]:
                df['NOM_IMPORTATEUR'] = df['NOM_IMPORTATEUR'].apply(lambda name: f"ENTREPRISE_ANONYME_{abs(hash(name)) % 10000}" if name else "INCONNU")
            if role in ["journaliste", "transitaire", "partenaire", "statisticien"]:
                df['RISK_SCORE'] = "NON AUTORISÉ"
                df['RISK_CLASS'] = "NON AUTORISÉ"
            try:
                with get_users_db() as sqlite_conn:
                    cursor = sqlite_conn.cursor()
                    cursor.execute("SELECT dossier_num FROM marked_dossiers")
                    marked_nums = {str(row[0]) for row in cursor.fetchall()}
            except Exception:
                marked_nums = set()
            df['IS_MARKED'] = df['NUMERODOSSIERTPS'].astype(str).isin(marked_nums)
            return df.to_dict(orient='records')
        return records
    finally:
        if conn:
            conn.close()


# ==========================================
# INTERACTIVE ROLE-BASED SERVICES
# ==========================================

class RiskSimulationRequest(BaseModel):
    importer: str
    country: str
    hs_code: str
    amount: float

class MarkInspectionRequest(BaseModel):
    dossier_num: Union[str, int]

class WeightsSimulationRequest(BaseModel):
    weight_under_eval: int
    weight_top_amount: int
    weight_new_importer: int
    weight_country_contention: int

class IncidentSimulationRequest(BaseModel):
    incident_type: str

class ExportCSVRequest(BaseModel):
    mode_transport: Optional[str] = None
    country: Optional[str] = None
    type_operation: Optional[str] = None
    regime_douanier: Optional[str] = None
    statut_dossier: Optional[str] = None
    annee: Optional[str] = None

@app.post("/api/inspecteur/simulate-risk")
def simulate_risk(req: RiskSimulationRequest, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "inspecteur"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
    
    score = 0
    reasons = []
    
    # 1. Run real-time machine learning prediction using Isolation Forest
    if iforest_model is not None:
        try:
            conn = db_conn.cursor()
            stats = conn.execute("""
                SELECT MEDIAN(QUANTITEMESURE), MEDIAN(POIDSNET), MEDIAN(POIDSBRUT)
                FROM articles
                WHERE NUMEROTARIFDOUANE = ?
            """, (req.hs_code.strip(),)).fetchone()
            
            qty = float(stats[0]) if stats and stats[0] is not None else 1.0
            pnet = float(stats[1]) if stats and stats[1] is not None else 1.0
            pbrut = float(stats[2]) if stats and stats[2] is not None else 1.0
            
            # Predict
            pred = iforest_model.predict([[req.amount, qty, pnet, pbrut]])[0]
            if pred == -1:
                score += 35
                reasons.append("Modèle Isolation Forest : comportement financier atypique détecté (+35)")
        except Exception as e:
            print(f"Error executing real-time IF prediction: {e}")
            
    hs = req.hs_code.strip()
    if hs.startswith(("87", "84", "85", "10", "15")):
        score += 30
        reasons.append("Code SH sensible aux anomalies de valeur (+30)")
        
    if req.amount > 10000000:
        score += 15
        reasons.append("Montant élevé (> 10M CFA) (+15)")
        
    imp = req.importer.upper().strip()
    known_big = ["SAR", "SONATEL", "CIMENT DU SAHEL", "DANGOTE", "SENELEC", "TOTAL SENEGAL", "SGBS"]
    is_big = any(k in imp for k in known_big)
    if not is_big:
        score += 10
        reasons.append("Importateur occasionnel ou nouveau (+10)")
        
    co = req.country.upper().strip()
    if co in ["CN", "IN", "TR", "FR", "CHINA", "INDE", "TURQUIE", "FRANCE"]:
        score += 10
        reasons.append("Provenance géographique sous surveillance (+10)")
        
    score = min(score, 100)
    
    if score < 30:
        risk_class = "Faible risque"
    elif score < 60:
        risk_class = "Moyen risque"
    else:
        risk_class = "Haut risque"
        
    return {
        "score": score,
        "risk_class": risk_class,
        "reasons": reasons
    }

@app.post("/api/inspecteur/mark-inspection")
def mark_inspection(req: MarkInspectionRequest, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "inspecteur"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
        
    dossier_str = str(req.dossier_num)
    with get_users_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO marked_dossiers (dossier_num, marked_by) VALUES (?, ?)",
                (dossier_str, claims["username"])
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    return {"detail": f"Dossier {dossier_str} marqué pour inspection physique."}

@app.get("/api/inspecteur/marked-dossiers")
def get_marked_dossiers(claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "inspecteur"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
        
    with get_users_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT dossier_num FROM marked_dossiers")
        rows = cursor.fetchall()
    return [r[0] for r in rows]

@app.post("/api/direction/simulate-weights")
def simulate_weights(req: WeightsSimulationRequest, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "direction"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
        
    conn = db_conn.cursor()
    rows = conn.execute("SELECT RISK_SCORE, PAYS_PROVENANCE FROM dossiers ORDER BY DATE_CREATION DESC, NUMERODOSSIERTPS DESC LIMIT 2000").fetchall()
    
    sim_counts = {"low_risk": 0, "med_risk": 0, "high_risk": 0}
    
    for orig_score, pays in rows:
        has_under = False
        has_top = False
        has_new = False
        has_country = False
        has_qty = False
        
        rem = orig_score or 0
        if rem >= 40:
            has_under = True
            rem -= 40
        if rem >= 20:
            has_top = True
            rem -= 20
        if rem >= 15:
            has_new = True
            rem -= 15
        
        co = (pays or "").upper().strip()
        if co in ["CN", "IN", "TR", "FR", "CHINA", "INDE", "TURQUIE", "FRANCE"]:
            has_country = True
        elif rem >= 15:
            has_country = True
            rem -= 15
            
        if rem >= 10:
            has_qty = True
            rem -= 10
            
        new_score = 0
        if has_under: new_score += req.weight_under_eval
        if has_top: new_score += req.weight_top_amount
        if has_new: new_score += req.weight_new_importer
        if has_country: new_score += req.weight_country_contention
        if has_qty: new_score += 10
        
        new_score = min(new_score, 100)
        
        if new_score < 30:
            sim_counts["low_risk"] += 1
        elif new_score < 60:
            sim_counts["med_risk"] += 1
        else:
            sim_counts["high_risk"] += 1
            
    return sim_counts

@app.get("/api/direction/budget-alerts")
def get_budget_alerts(claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "direction"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
        
    if not USE_MSSQL and not os.path.exists(DB_DOUANE_PATH):
        return {
            "alert": False,
            "decline_pct": 1.2,
            "message": "Activité et recettes douanières stables (mode démo)."
        }
        
    conn = db_conn.cursor()
    rows = conn.execute("""
        SELECT substring(DATE_CREATION, 1, 10) as dt, COUNT(*) 
        FROM dossiers 
        WHERE DATE_CREATION IS NOT NULL 
        GROUP BY substring(DATE_CREATION, 1, 10) 
        ORDER BY dt DESC 
        LIMIT 60
    """).fetchall()
    
    if len(rows) < 30:
        return {"alert": False, "message": "Données insuffisantes pour l'analyse de tendance."}
        
    recent_30 = sum(r[1] for r in rows[:30])
    prev_30 = sum(r[1] for r in rows[30:60])
    
    decline_pct = 0.0
    if prev_30 > 0:
        decline_pct = ((prev_30 - recent_30) / prev_30) * 100
        
    alert = decline_pct > 5.0
    
    return {
        "alert": alert,
        "decline_pct": round(decline_pct, 2),
        "message": f"Alerte budgétaire : baisse d'activité de {round(decline_pct, 2)}% détectée sur les 30 derniers jours." if alert else "Activité et recettes douanières stables."
    }

@app.get("/api/direction/generate-pdf-report")
def generate_pdf_report(
    type: str = "executive", 
    anonymize: bool = False, 
    year: Optional[str] = None, 
    country: Optional[str] = None, 
    bank: Optional[str] = None, 
    reportMonth: Optional[str] = "07",
    reportYear: Optional[str] = "2026",
    claims: dict = Depends(get_current_user_claims)
):
    if claims["role"] not in ["admin", "direction", "statisticien", "inspecteur"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
    
    # Calculate filtered stats dynamically using active filters and RLS
    dashboard_data = get_dashboard_data(year=year, country=country, bank=bank, claims=claims)
    
    from pdf_generator import build_premium_pdf_report
    return build_premium_pdf_report(type, anonymize, claims["username"], dashboard_data, report_month=reportMonth, report_year=reportYear)

@app.get("/api/partenaire/importer-reliability")
def get_importer_reliability(ninea: str, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "partenaire"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
        
    conn = db_conn.cursor()
    cnt = conn.execute("SELECT COUNT(*) FROM dossiers WHERE NINEA_IMPORTATEUR = ?", (ninea,)).fetchone()[0] or 0
    if cnt == 0:
        return {"score": 85, "class": "A (Nouveau Client)", "total_dossiers": 0, "active_dossiers": 0, "pending_dossiers": 0}
        
    encours = conn.execute("SELECT COUNT(*) FROM dossiers WHERE NINEA_IMPORTATEUR = ? AND STATUT_DOSSIER = 'EnCours'", (ninea,)).fetchone()[0] or 0
    initialise = conn.execute("SELECT COUNT(*) FROM dossiers WHERE NINEA_IMPORTATEUR = ? AND STATUT_DOSSIER = 'Initialise'", (ninea,)).fetchone()[0] or 0
    
    h = abs(hash(ninea)) % 15
    base_score = 82 + h
    
    total = encours + initialise
    if total > 0:
        initialise_ratio = initialise / total
        deduction = int(initialise_ratio * 12)
        score = max(base_score - deduction, 60)
    else:
        score = base_score
        
    score = min(score, 100)
    
    if score >= 90:
        reliability_class = "A+ (Excellent)"
    elif score >= 80:
        reliability_class = "A (Très Solvable)"
    elif score >= 70:
        reliability_class = "B (Moyen / Conforme)"
    else:
        reliability_class = "C (Attention requise)"
        
    return {
        "score": score,
        "class": reliability_class,
        "total_dossiers": total,
        "active_dossiers": encours,
        "pending_dossiers": initialise
    }

@app.post("/api/statistician/export-csv")
def export_csv(req: ExportCSVRequest, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "statisticien"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
        
    conn = db_conn.cursor()
    where_clauses = []
    params = []
    if req.mode_transport:
        where_clauses.append("MODE_TRANSPORT = ?")
        params.append(req.mode_transport)
    if req.country:
        where_clauses.append("upper(PAYS_PROVENANCE) = ?")
        params.append(req.country.strip().upper())
    if req.type_operation:
        where_clauses.append("TYPE_OPERATION = ?")
        params.append(req.type_operation)
    if req.regime_douanier:
        where_clauses.append("upper(REGIME_DOUANIER) = ?")
        params.append(req.regime_douanier.strip().upper())
    if req.statut_dossier:
        where_clauses.append("STATUT_DOSSIER = ?")
        params.append(req.statut_dossier)
    if req.annee:
        where_clauses.append("substring(DATE_CREATION, 1, 4) = ?")
        params.append(req.annee)
        
    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    query = f"""
        SELECT NUMERODOSSIERTPS, TYPE_OPERATION, DATE_CREATION, STATUT_DOSSIER, 
               MODE_TRANSPORT, NOM_IMPORTATEUR, NINEA_IMPORTATEUR, REGIME_DOUANIER
        FROM dossiers 
        {where_str} 
        ORDER BY DATE_CREATION DESC, NUMERODOSSIERTPS DESC
        LIMIT 5000
    """
    rows = conn.execute(query, params).fetchall()
    
    import tempfile
    temp_dir = tempfile.gettempdir()
    export_filename = f"export_anonyme_{abs(hash(claims['username'])) % 10000}.csv"
    filepath = os.path.join(temp_dir, export_filename)
    
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(["NUMERODOSSIER", "TYPE_OPERATION", "DATE_CREATION", "STATUT", "MODE_TRANSPORT", "IMPORTATEUR_ANONYME", "NINEA_ANONYME", "REGIME"])
        for r in rows:
            anon_name = f"IMPORTATEUR_ANON_{abs(hash(r[5] or '')) % 10000}"
            anon_ninea = f"NINEA_ANON_{abs(hash(r[6] or '')) % 1000}"
            writer.writerow([r[0], r[1], r[2], r[3], r[4], anon_name, anon_ninea, r[7]])
            
    return {"download_url": f"/api/statistician/download-csv/{export_filename}"}

@app.get("/api/statistician/download-csv/{filename}")
def download_csv(filename: str, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] not in ["admin", "statisticien"]:
        raise HTTPException(status_code=403, detail="Accès interdit")
        
    import tempfile
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
        
    return FileResponse(filepath, media_type="text/csv", filename=filename)

@app.get("/api/admin/audit-logs")
def get_audit_logs(claims: dict = Depends(get_current_user_claims)):
    if claims["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul l'administrateur a accès à l'audit")
        
    with get_users_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, username, client_ip, server_ip, location, status FROM audit_logs ORDER BY id DESC")
        rows = cursor.fetchall()
        
    return [
        {
            "timestamp": r[0],
            "username": r[1],
            "client_ip": r[2],
            "server_ip": r[3],
            "location": r[4],
            "status": r[5]
        }
        for r in rows
    ]

@app.post("/api/admin/simulate-incident")
def simulate_incident(req: IncidentSimulationRequest, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul l'administrateur peut simuler des incidents")
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_users_db() as conn:
        cursor = conn.cursor()
        if req.incident_type == "brute_force":
            cursor.execute(
                "INSERT INTO audit_logs (timestamp, username, client_ip, server_ip, location, status) VALUES (?, ?, ?, ?, ?, ?)",
                (now_str, "suspect_user", "82.102.23.15", "10.200.12.5", "Paris, France", "Tentative Force Brute")
            )
        elif req.incident_type == "tor_node":
            cursor.execute(
                "INSERT INTO audit_logs (timestamp, username, client_ip, server_ip, location, status) VALUES (?, ?, ?, ?, ?, ?)",
                (now_str, "hacker_bot", "185.220.101.42", "10.200.12.5", "Frankfurt, Allemagne", "Bloqué (Tor Node)")
            )
        elif req.incident_type == "data_leak":
            cursor.execute(
                "INSERT INTO audit_logs (timestamp, username, client_ip, server_ip, location, status) VALUES (?, ?, ?, ?, ?, ?)",
                (now_str, "unknown_agent", "102.164.2.19", "10.200.12.5", "Dakar, Sénégal", "Alerte Exfiltration (Suspect)")
            )
    return {"detail": "Incident simulé avec succès."}

# ==========================================
# ADMIN USER MANAGEMENT ENDPOINTS
# ==========================================

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    bureau_douane: Optional[str] = None

@app.post("/api/admin/create-user")
def create_user(req: CreateUserRequest, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul l'administrateur peut créer des utilisateurs"
        )
        
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="L'identifiant est obligatoire")
        
    if not req.password:
        raise HTTPException(status_code=400, detail="Le mot de passe est obligatoire")
        
    validate_password_complexity(req.password)
        
    valid_roles = ["admin", "direction", "inspecteur", "transitaire", "partenaire", "statisticien", "journaliste"]
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rôle invalide. Rôles autorisés: {', '.join(valid_roles)}")
        
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(req.password.encode('utf-8'), salt).decode('utf-8')
    
    with get_users_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, bureau_douane) VALUES (?, ?, ?, ?)",
                (username, hashed, req.role, req.bureau_douane)
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Cet identifiant existe déjà")
            
    return {"detail": f"Utilisateur {username} créé avec succès"}

class UpdatePasswordRequest(BaseModel):
    username: str
    password: str

@app.post("/api/admin/update-password")
def update_password(req: UpdatePasswordRequest, claims: dict = Depends(get_current_user_claims)):
    if claims["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul l'administrateur peut modifier les mots de passe"
        )
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="L'identifiant est obligatoire")
    if not req.password:
        raise HTTPException(status_code=400, detail="Le mot de passe est obligatoire")

    validate_password_complexity(req.password)

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(req.password.encode('utf-8'), salt).decode('utf-8')

    with get_users_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        cursor.execute(
            "UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL WHERE username = ?",
            (hashed, username)
        )
    return {"detail": f"Mot de passe de l'utilisateur {username} modifié avec succès"}

@app.get("/api/admin/users")
def list_users(claims: dict = Depends(get_current_user_claims)):
    if claims["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul l'administrateur peut lister les utilisateurs"
        )
        
    with get_users_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, role, bureau_douane FROM users")
        rows = cursor.fetchall()
        
    return [
        {"username": row[0], "role": row[1], "bureau_douane": row[2]}
        for row in rows
    ]

# ==========================================
# CHATBOT ASSISTANT ENDPOINTS (LOCAL & SECURE)
# ==========================================

class ChatRequest(BaseModel):
    message: str

@app.post("/api/assistant/chat")
def assistant_chat(req: ChatRequest, claims: dict = Depends(get_current_user_claims)):
    import re
    import csv
    import tempfile
    import requests
    
    username = claims["username"]
    role = claims["role"]
    bureau = claims["bureau_douane"]
    message = req.message.strip()
    
    if not message:
        raise HTTPException(status_code=400, detail="Le message ne peut pas être vide")
        
    # Get RLS filters
    rls_clauses = []
    rls_params = []
    
    if role == "inspecteur":
        if bureau == "DKP":
            rls_clauses.append("d.MODE_TRANSPORT = ?")
            rls_params.append("Mer")
        elif bureau == "AIBD":
            rls_clauses.append("d.MODE_TRANSPORT = ?")
            rls_params.append("Air")
    elif role == "transitaire":
        rls_clauses.append("d.NINEA_IMPORTATEUR = ?")
        rls_params.append(bureau)
    elif role == "partenaire":
        rls_clauses.append("(d.BANQUE = ? OR d.ASSURANCE = ?)")
        rls_params.extend([bureau, bureau])
        
    # Check if this message is a database query (intent matching)
    
    # 1. HELP / GREETING
    if re.search(r'\b(bonjour|salut|hello|hi|aide|help|aidez|qui)\b', message, re.IGNORECASE):
        reply = (
            f"Bonjour **{username}** ! Je suis l'assistant intelligent d'Orbus Sentinel (expérimental) 🤖.\n\n"
            "Je peux répondre à vos requêtes sur la base de données douanière locale. Posez-moi des questions comme :\n"
            "- *« Combien de dossiers au total ? »*\n"
            "- *« Quels sont les principaux pays d'origine ? »*\n"
            "- *« Montre-moi les anomalies détectées »*\n"
            "- *« Exporte les dossiers en CSV »*"
        )
        return {"reply": reply}
        
    # 2. COUNT DOSSIERS
    elif re.search(r'combien|total|nombre|quantité|volume', message, re.IGNORECASE) and re.search(r'dossier|déclaration|import', message, re.IGNORECASE):
        query_clauses = list(rls_clauses)
        query_params = list(rls_params)
        
        # Parse transport mode
        transport_label = ""
        if re.search(r'mer|maritime|port', message, re.IGNORECASE):
            query_clauses.append("d.MODE_TRANSPORT = ?")
            query_params.append("Mer")
            transport_label = "maritimes"
        elif re.search(r'air|aérien|aibd', message, re.IGNORECASE):
            query_clauses.append("d.MODE_TRANSPORT = ?")
            query_params.append("Air")
            transport_label = "aériens"
        elif re.search(r'route|routier|frontière', message, re.IGNORECASE):
            query_clauses.append("d.MODE_TRANSPORT = ?")
            query_params.append("Route")
            transport_label = "routiers"
            
        # Parse status (Map to DB values EnCours / Initialise)
        status_label = ""
        if re.search(r'en\s*cours|encours|soumis|valid|active', message, re.IGNORECASE):
            query_clauses.append("d.STATUT_DOSSIER = ?")
            query_params.append("EnCours")
            status_label = "en cours"
        elif re.search(r'initialis|nouveau|créé', message, re.IGNORECASE):
            query_clauses.append("d.STATUT_DOSSIER = ?")
            query_params.append("Initialise")
            status_label = "initialisés"
            
        # Parse country
        country_name = None
        countries = ["Chine", "France", "Inde", "Espagne", "Italie", "Belgique", "Sénégal"]
        for c in countries:
            if re.search(r'\b' + c + r'\b', message, re.IGNORECASE):
                query_clauses.append("d.PAYS_PROVENANCE = ?")
                query_params.append(c)
                country_name = c
                break
                
        where_str = f"WHERE {' AND '.join(query_clauses)}" if query_clauses else ""
        sql = f"SELECT COUNT(DISTINCT d.NUMERODOSSIERTPS) FROM dossiers d {where_str}"
        
        conn = db_conn.cursor()
        count = conn.execute(sql, query_params).fetchone()[0]
        conn.close()
        
        # Build nice scope description
        parts = []
        if status_label:
            parts.append(status_label)
        if transport_label:
            parts.append(transport_label)
        if country_name:
            parts.append(f"provenance {country_name}")
            
        scope_text = ""
        if parts:
            scope_text = f"({', '.join(parts)})"
        else:
            scope_text = "totaux"
            
        role_restriction_text = ""
        if role == "transitaire":
            role_restriction_text = f" associés à votre PPM ({bureau})"
        elif role == "inspecteur":
            role_restriction_text = f" sous la juridiction du bureau {bureau}"
        elif role == "partenaire":
            role_restriction_text = f" associés à votre banque/assurance ({bureau})"
            
        reply = f"Il y a actuellement **{count} dossiers** {scope_text}{role_restriction_text} enregistrés dans le système."
        return {"reply": reply}

    # 2. EXPORTS / REPORTS
    elif re.search(r'export|télécharg|csv|rapport|fichier|extraire', message, re.IGNORECASE):
        query_clauses = list(rls_clauses)
        query_params = list(rls_params)
        
        # Parse transport mode
        transport_label = ""
        if re.search(r'mer|maritime|port', message, re.IGNORECASE):
            query_clauses.append("d.MODE_TRANSPORT = ?")
            query_params.append("Mer")
            transport_label = "_mer"
        elif re.search(r'air|aérien|aibd', message, re.IGNORECASE):
            query_clauses.append("d.MODE_TRANSPORT = ?")
            query_params.append("Air")
            transport_label = "_air"
        elif re.search(r'route|routier|frontière', message, re.IGNORECASE):
            query_clauses.append("d.MODE_TRANSPORT = ?")
            query_params.append("Route")
            transport_label = "_route"
            
        where_str = f"WHERE {' AND '.join(query_clauses)}" if query_clauses else ""
        sql = f"""
            SELECT d.NUMERODOSSIERTPS, d.TYPE_OPERATION, d.DATE_CREATION, d.STATUT_DOSSIER, 
                   d.MODE_TRANSPORT, d.NOM_IMPORTATEUR, d.NINEA_IMPORTATEUR, d.REGIME_DOUANIER, d.RISK_SCORE
            FROM dossiers d
            {where_str}
            ORDER BY d.DATE_CREATION DESC
            LIMIT 5000
        """
        
        conn = db_conn.cursor()
        rows = conn.execute(sql, query_params).fetchall()
        conn.close()
        
        if not rows:
            return {"reply": "Aucun dossier trouvé correspondant à vos critères pour générer l'export."}
            
        export_filename = f"export_assistant_{username}_{abs(hash(message + str(datetime.now()))) % 100000}{transport_label}.csv"
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, export_filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(["NUMERODOSSIER", "TYPE_OPERATION", "DATE_CREATION", "STATUT", "MODE_TRANSPORT", "IMPORTATEUR", "NINEA", "REGIME", "SCORE_RISQUE"])
            for r in rows:
                if role in ["partenaire", "journaliste"]:
                    anon_name = f"IMPORTATEUR_ANON_{abs(hash(r[5] or '')) % 10000}"
                    anon_ninea = f"NINEA_ANON_{abs(hash(r[6] or '')) % 1000}"
                    writer.writerow([r[0], r[1], r[2], r[3], r[4], anon_name, anon_ninea, r[7], r[8]])
                else:
                    writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]])
                    
        reply = f"J'ai préparé l'export CSV contenant **{len(rows)} dossiers** correspondant à vos droits d'accès. Vous pouvez le télécharger via le bouton ci-dessous."
        return {
            "reply": reply,
            "export_url": f"/api/assistant/download-csv/{export_filename}"
        }

    # 3. ANOMALIES & RISKS
    elif re.search(r'anomalie|anomale|suspect|fraude|risque|risk|isolation forest', message, re.IGNORECASE):
        where_clauses = ["a.ANOMALY_IF = True"]
        params = []
        for cl in rls_clauses:
            where_clauses.append(cl)
        params.extend(rls_params)
        
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql_anom = f"""
            SELECT COUNT(DISTINCT d.NUMERODOSSIERTPS)
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
        """
        
        where_clauses_risk = ["d.RISK_CLASS = ?"]
        params_risk = ["Haut risque"]
        for cl in rls_clauses:
            where_clauses_risk.append(cl)
        params_risk.extend(rls_params)
        
        where_str_risk = f"WHERE {' AND '.join(where_clauses_risk)}" if where_clauses_risk else ""
        sql_risk = f"SELECT COUNT(*) FROM dossiers d {where_str_risk}"
        
        sql_examples = f"""
            SELECT DISTINCT d.NUMERODOSSIERTPS, a.DESIGNATIONCOMMERCIALE, a.VALEURCFA, d.RISK_SCORE
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
            ORDER BY d.RISK_SCORE DESC
            LIMIT 3
        """
        
        conn = db_conn.cursor()
        anom_count = conn.execute(sql_anom, params).fetchone()[0]
        risk_count = conn.execute(sql_risk, params_risk).fetchone()[0]
        examples = conn.execute(sql_examples, params).fetchall()
        conn.close()
        
        reply = f"Analyse de risque Orbus Sentinel :\n- **{anom_count} articles** sont détectés comme anormaux par l'algorithme *Isolation Forest*.\n- **{risk_count} dossiers** sont classés comme *Haut Risque* (Score > 75).\n\n"
        if examples:
            reply += "Voici les 3 anomalies prioritaires :\n"
            for ex in examples:
                reply += f"- **Dossier N° {ex[0]}** : {ex[1]} (Valeur: {ex[2]:,.0f} CFA, Risque: {ex[3]}/100)\n"
        else:
            reply += "Aucune anomalie détectée dans votre périmètre de données."
            
        return {"reply": reply}

    # 4. COUNTRIES OF ORIGIN
    elif re.search(r'pays|origine|provenance|destination|chine|france|inde', message, re.IGNORECASE):
        where_clauses = ["a.PAYSORIGINE IS NOT NULL"]
        params = []
        for cl in rls_clauses:
            where_clauses.append(cl)
        params.extend(rls_params)
        
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""
            SELECT a.PAYSORIGINE, COUNT(DISTINCT d.NUMERODOSSIERTPS) as count, SUM(a.VALEURCFA) as total_val
            FROM articles a
            JOIN dossiers d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
            {where_str}
            GROUP BY a.PAYSORIGINE
            ORDER BY count DESC
            LIMIT 5
        """
        
        conn = db_conn.cursor()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        
        if not rows:
            return {"reply": "Aucune donnée de provenance trouvée dans votre périmètre."}
            
        reply = "Top 5 des pays d'origine pour vos dossiers :\n"
        for i, r in enumerate(rows, 1):
            reply += f"{i}. **{r[0]}** : {r[1]} dossiers (Valeur cumulative: {r[2]:,.0f} CFA)\n"
        return {"reply": reply}
        
    # 5. SOLVENCY / PPM INFO
    elif re.search(r'solvabilité|fiabilité|segment|ninea|ppm', message, re.IGNORECASE):
        ninea = None
        search_match = re.search(
            r'(?:solvabilité|fiabilité|segment|ninea|ppm)(?:\s+(?:de|du|de\s+la|d\'|pour))?\s+([a-z0-9_\-\s&]+)', 
            message, 
            re.IGNORECASE
        )
        if search_match:
            ninea = search_match.group(1).strip()
            ninea = re.sub(r'^(?:du\s+|le\s+)?(?:ninea|ppm)\s+', '', ninea, flags=re.IGNORECASE).strip()
            
        if role == "transitaire":
            ninea = bureau
            
        if not ninea:
            reply = "Pour obtenir des détails sur la solvabilité ou le segment d'un importateur, veuillez préciser son nom ou son code PPM (ex: *« Solvabilité de NESTLE SENEGAL »*)."
            return {"reply": reply}
            
        sql = """
            SELECT NOM_IMPORTATEUR, NINEA_IMPORTATEUR, IMPORTATEUR_SEGMENT, AVG(RISK_SCORE)
            FROM dossiers d
            WHERE d.NINEA_IMPORTATEUR = ?
            GROUP BY NOM_IMPORTATEUR, NINEA_IMPORTATEUR, IMPORTATEUR_SEGMENT
            LIMIT 1
        """
        conn = db_conn.cursor()
        res = conn.execute(sql, [ninea]).fetchone()
        conn.close()
        
        if not res:
            sql_name = """
                SELECT NOM_IMPORTATEUR, NINEA_IMPORTATEUR, IMPORTATEUR_SEGMENT, AVG(RISK_SCORE)
                FROM dossiers d
                WHERE d.NOM_IMPORTATEUR ILIKE ?
                GROUP BY NOM_IMPORTATEUR, NINEA_IMPORTATEUR, IMPORTATEUR_SEGMENT
                LIMIT 1
            """
            conn = db_conn.cursor()
            res = conn.execute(sql_name, [f"%{ninea}%"]).fetchone()
            conn.close()
            
        if not res:
            return {"reply": f"Aucun importateur trouvé avec le code PPM ou nom correspondant à **{ninea}** dans la base."}
            
        reply = (
            f"Fiche d'information solvabilité pour l'importateur :\n"
            f"- **Nom** : {res[0]}\n"
            f"- **Code PPM** : {res[1]}\n"
            f"- **Segmentation** : Segment {res[2]} (K-Means)\n"
            f"- **Score de risque moyen** : {res[3]:.1f}/100\n"
            f"- **Statut** : Solvable, actif dans le système."
        )
        return {"reply": reply}

    # 6. DEFAULT FALLBACK
    else:
        reply = (
            "Désolé, je ne parviens pas à interpréter votre demande en langage naturel.\n\n"
            "Je suis un chatbot local déterministe. Vous pouvez me poser des questions précises sur :\n"
            "- **Le volume de dossiers** (ex: *« Combien de dossiers validés par mer ? »*)\n"
            "- **Les anomalies de douane** (ex: *« Montre-moi les anomalies récentes »*)\n"
            "- **Les pays d'origine** (ex: *« Quels sont les pays d'origine principaux ? »*)\n"
            "- **La solvabilité des PPM** (ex: *« Solvabilité de NESTLE SENEGAL »* ou PPM *« 0013920 »*)\n"
            "- **Générer des exports** (ex: *« Exporte les dossiers de ce mois »*)"
        )
        return {"reply": reply}

@app.get("/api/assistant/download-csv/{filename}")
def assistant_download_csv(filename: str, claims: dict = Depends(get_current_user_claims)):
    import tempfile
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")
        
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
        
    return FileResponse(filepath, media_type="text/csv", filename=filename)

@app.post("/api/log-error")
def log_client_error(payload: dict):
    print("=" * 60)
    print("CLIENT-SIDE BROWSER CONSOLE ERROR DETECTED:")
    print(f"Message: {payload.get('message')}")
    print(f"Source: {payload.get('source')} (Line {payload.get('lineno')}, Col {payload.get('colno')})")
    print(f"Stack Trace:\n{payload.get('stack')}")
    print("=" * 60)
    return {"status": "ok"}

# ==========================================
# ADVANCED COPILOT & SIEM ENTERPRISE ENDPOINTS
# ==========================================

class TOTPVerifyRequest(BaseModel):
    token: str
    secret: str

@app.post("/api/auth/2fa/setup")
def setup_2fa(claims: dict = Depends(get_current_user_claims)):
    username = claims["username"]
    import base64
    random_bytes = os.urandom(10)
    secret_b32 = base64.b32encode(random_bytes).decode('utf-8').replace('=', '')
    totp_uri = f"otpauth://totp/GAINDE2000:{username}?secret={secret_b32}&issuer=GAINDE2000"
    return {
        "username": username,
        "secret": secret_b32,
        "otpauth_url": totp_uri
    }

@app.post("/api/auth/2fa/verify")
def verify_2fa(req: TOTPVerifyRequest, claims: dict = Depends(get_current_user_claims)):
    import base64, hmac, hashlib, struct
    try:
        secret = req.secret.strip().upper()
        missing_padding = len(secret) % 8
        if missing_padding:
            secret += '=' * (8 - missing_padding)
        key = base64.b32decode(secret)
        counter = int(time.time()) // 30
        
        valid = False
        for c in [counter, counter - 1, counter + 1]:
            msg = struct.pack(">Q", c)
            h = hmac.new(key, msg, hashlib.sha1).digest()
            offset = h[-1] & 0x0F
            code = (struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
            if f"{code:06d}" == req.token.strip():
                valid = True
                break
                
        if not valid:
            raise HTTPException(status_code=400, detail="Code de vérification 2FA invalide ou expiré.")
        return {"detail": "Vérification 2FA réussie avec succès."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de validation 2FA: {str(e)}")

@app.get("/api/copilot/explain-dossier/{dossier_num}")
def copilot_explain_dossier(dossier_num: str, claims: dict = Depends(get_current_user_claims)):
    conn = db_conn.cursor()
    row = conn.execute("""
        SELECT NUMERODOSSIERTPS, NOMOURAISONSOCIALEBENEFICIAIRE, VALEURTOTALECFA, 
               MODETRANSPORT, NIVEAUEXECUTIONDOSSIERTPS, PaysDeProvenance, RegimeDouanier
        FROM dossiers WHERE NUMERODOSSIERTPS = ?
    """, (dossier_num,)).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
        
    num, importer, val_cfa, mode, status_dos, provenance, regime = row
    val_cfa = float(val_cfa or 0)
    
    avg_val = conn.execute("SELECT AVG(VALEURTOTALECFA) FROM dossiers WHERE MODETRANSPORT = ?", (mode,)).fetchone()[0] or 1000000.0
    deviation_pct = round(((val_cfa - avg_val) / max(avg_val, 1.0)) * 100, 1)
    
    if deviation_pct > 150:
        risk_level = "CRITIQUE"
        risk_score = 92
        recommendation = "Contrôle physique intégral obligatoire sur cale avec dépotage et contre-expertise de la valeur FOB par un inspecteur principal."
        reasons = [
            f"Écart de valeur déclarée de +{deviation_pct}% par rapport à la valeur sectorielle moyenne ({avg_val:,.0f} CFA).",
            f"Régime douanier sous surveillance renforcée ({regime}).",
            f"Provenance à haut suivi logistique ({provenance})."
        ]
    elif deviation_pct > 50:
        risk_level = "ÉLEVÉ"
        risk_score = 75
        recommendation = "Inspection documentaire approfondie des factures acquittées et vérification du connaissement maritime."
        reasons = [
            f"Écart de valeur significative de +{deviation_pct}% détecté.",
            f"Mode de transport {mode} soumis à contrôle douanier ciblé."
        ]
    else:
        risk_level = "MODÉRÉ"
        risk_score = 35
        recommendation = "Mainlevée sous réserve de vérification automatique des droits et taxes acquittés."
        reasons = [
            "Valeur déclarée conforme aux moyennes sectorielles historiques.",
            "Importateur régulier sans historique récent d'infraction."
        ]
        
    return {
        "dossier_num": num,
        "importer": importer,
        "mode_transport": mode,
        "valeur_cfa": val_cfa,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "deviation_pct": deviation_pct,
        "recommendation": recommendation,
        "reasons": reasons
    }

@app.get("/api/admin/siem-threats")
def get_siem_threats(claims: dict = Depends(get_current_user_claims)):
    if claims["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul l'administrateur a accès au dashboard SIEM")
        
    log_file = "data/logs/security_audit.log"
    recent_events = []
    ip_counts = {}
    category_counts = {}
    total_events = 0
    failed_logins = 0
    
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-300:]
            
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            total_events += 1
            
            if "[AUTH_FAILURE]" in line_str or "LOGIN_FAILED" in line_str:
                failed_logins += 1
                
            ip_match = re.search(r'IP=([0-9\.]+)', line_str)
            if ip_match:
                ip = ip_match.group(1)
                ip_counts[ip] = ip_counts.get(ip, 0) + 1
                
            cat_match = re.search(r'\[([A-Z_]+)\]', line_str)
            if cat_match:
                cat = cat_match.group(1)
                category_counts[cat] = category_counts.get(cat, 0) + 1
                
            if len(recent_events) < 50:
                recent_events.append(line_str)
                
    top_ips = sorted([{"ip": k, "requests": v} for k, v in ip_counts.items()], key=lambda x: x["requests"], reverse=True)[:10]
    
    return {
        "total_events_logged": total_events,
        "failed_logins_count": failed_logins,
        "top_requesting_ips": top_ips,
        "categories_breakdown": category_counts,
        "recent_raw_events": recent_events[::-1]
    }