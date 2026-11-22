from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import users, entries, screenshots, auth, admin
from mangum import Mangum
import firebase_admin
from firebase_admin import credentials
import json
from config import settings

# ── Firebase init ──────────────────────────────────────────────────────────────
# On Lambda there is no GCP metadata server, so ADC (ApplicationDefault) won't work.
# We load the service account JSON from the GCP_SERVICE_ACCOUNT_JSON env var instead.
print("Initializing Firebase with service account credentials")
service_account_info = json.loads(settings.GCP_SERVICE_ACCOUNT_JSON)
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(redirect_slashes=False)

# ── CORS ───────────────────────────────────────────────────────────────────────
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5500",
    "https://smile-snap.vercel.app",
    "https://smile-snap-git-main-noah-kims-projects-027c25a1.vercel.app",
    "https://smile-snap-6q6kd1b98-noah-kims-projects-027c25a1.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(users.router)
app.include_router(entries.router)
app.include_router(screenshots.router)
app.include_router(auth.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}

# ── Lambda handler ─────────────────────────────────────────────────────────────
# Mangum wraps the fully-configured app so AWS Lambda can invoke it.
# This must come AFTER app is built and all routers are registered.
handler = Mangum(app)