from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
import os

app = FastAPI()

# Perbaikan Konfigurasi CORS (Hapus sub-path /login)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://management-kasir-zixa.vercel.app",  # URL Produksi Vercel
        "http://localhost:3000"                      # URL Lokal untuk development
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi Supabase Client
# PENTING: Pastikan SUPABASE_KEY menggunakan Anon Key (string panjang diawali 'eyJ...') jika key di bawah gagal
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ghowabpmxojzlbbskbzn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_sxchFXHtEoZhWfbcrMHbIg_00Kk7UIg")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@app.post("/api/auth/login")
def login_with_supabase(payload: LoginRequest):
    try:
        # Melakukan sign-in menggunakan Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        user_data = response.user
        session_data = response.session

        # Ambil role dari user_metadata (default: cashier)
        user_role = user_data.user_metadata.get("role", "cashier")

        return {
            "status": "success",
            "user": {
                "id": user_data.id,
                "name": user_data.user_metadata.get("name", "Pengguna"),
                "email": user_data.email,
                "role": user_role,
            },
            "token": session_data.access_token
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah atau terjadi kesalahan autentikasi."
        )
    
@app.post("/create-user")
def create_user():

    auth_response = supabase.auth.admin.create_user({
        "email": "kasir@coffee.com",
        "password": "kasir123",
        "email_confirm": True
    })

    user = auth_response.user

    supabase.table("user_profile").insert({
        "id": user.id,
        "username": "kasir01",
        "full_name": "Kasir Coffee",
        "role": "kasir"
    }).execute()

    return {
        "message": "User berhasil dibuat"
    }