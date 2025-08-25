from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from routers import users, entries, screenshots, auth, websockets, admin  # Import the new router
import firebase_admin
from firebase_admin import credentials
import os

print("Initializing Firebase with Application Default Credentials")
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)

app = FastAPI(redirect_slashes=False)

allowed_hosts = [
    "smile-snap-959486697650.us-west2.run.app", 
    "smile-snap.vercel.app",
    "127.0.0.1",      # <-- ADD THIS
    "localhost"       # <-- AND THIS
]

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed_hosts
)

# --- ADD THIS MIDDLEWARE CONFIGURATION ---
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5500",
    "https://smile-snap.vercel.app",  # Main production URL
    "https://smile-snap-git-main-noah-kims-projects-027c25a1.vercel.app",  # Git branch URL
    "https://smile-snap-6q6kd1b98-noah-kims-projects-027c25a1.vercel.app"  # Deployment URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

app.include_router(users.router)
app.include_router(entries.router)
app.include_router(screenshots.router)
app.include_router(auth.router)
app.include_router(websockets.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}

@app.get("/debug/routes")
def list_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": getattr(route, 'methods', [])
            })
    return {"routes": routes}

@app.get("/debug/env")
def debug_env():
    return {
        "BUCKET_NAME": os.getenv("BUCKET_NAME"),
        "GCP_PROJECT_ID": os.getenv("GCP_PROJECT_ID"), 
        "PROJECT_ID": os.getenv("GCP_PROJECT_ID"),  # Check if your code uses PROJECT_ID vs GCP_PROJECT_ID
        "K_SERVICE": os.getenv("K_SERVICE"),  # This confirms we're in Cloud Run
        "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT"),
    }