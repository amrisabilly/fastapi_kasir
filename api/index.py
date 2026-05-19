from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client
import os

app = FastAPI(
    title="Management Kasir API",
    description="Backend API untuk sistem management kasir menggunakan FastAPI dan Supabase Auth",
    version="1.0.0"
)

# 1. KONFIGURASI CORS
# Memastikan Next.js (baik lokal maupun produksi di Vercel) dapat mengakses API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://management-kasir.vercel.app",  # URL Produksi Vercel Anda
        "http://localhost:3000"                  # URL Lokal untuk development
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. INISIALISASI SUPABASE CLIENT
# PENTING: SUPABASE_KEY harus menggunakan SERVICE_ROLE_KEY (Secret Key) 
# agar fungsi admin.create_user dapat berjalan tanpa hambatan RLS atau konfirmasi email.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Gunakan service_role_key agar bisa create-user

if not SUPABASE_URL or SUPABASE_KEY == "ISI_DENGAN_SERVICE_ROLE_KEY_ANDA":
    print("PERINGATAN: Pastikan Anda telah mengatur SUPABASE_URL dan SUPABASE_KEY (Service Role) dengan benar!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# 3. VALIDASI SKEMA DATA (PYDANTIC MODELS)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password minimal 6 karakter")
    username: str = Field(..., min_length=3, description="Username unik pengguna")
    full_name: str = Field(..., description="Nama lengkap pengguna")
    role: str = Field(..., description="Role wajib diisi: 'manager', 'supervisor', atau 'kasir'")


# 4. ENDPOINT 1: LOGIN UTK SEMUA ROLE
@app.post("/api/auth/login", summary="Login menggunakan Email dan Password Supabase")
def login_with_supabase(payload: LoginRequest):
    try:
        # Melakukan autentikasi via Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        user_data = response.user
        session_data = response.session

        if not user_data or not session_data:
            raise HTTPException(status_code=401, detail="Data autentikasi tidak valid")

        # Mengambil metadata yang disimpan saat registrasi
        user_metadata = user_data.user_metadata if user_data.user_metadata else {}
        user_role = user_metadata.get("role", "kasir")
        full_name = user_metadata.get("name", "Pengguna")

        return {
            "status": "success",
            "message": "Login berhasil",
            "user": {
                "id": user_data.id,
                "name": full_name,
                "email": user_data.email,
                "role": user_role,  # Nilai dinamis: 'manager' | 'supervisor' | 'kasir'
            },
            "token": session_data.access_token # Token JWT untuk dikirimkan Next.js pada request selanjutnya
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah atau kredensial tidak ditemukan."
        )


# 5. ENDPOINT 2: PEMBUATAN USER SECARA DINAMIS (ADMIN ONLY BY SERVICE ROLE)
@app.post("/create-user", summary="Membuat User baru (Manager, Supervisor, atau Kasir)")
def create_user(payload: CreateUserRequest):
    # Validasi server-side untuk memastikan role yang masuk sesuai ketentuan
    allowed_roles = ["manager", "supervisor", "kasir"]
    if payload.role.lower() not in allowed_roles:
        raise HTTPException(
            status_code=400, 
            detail=f"Role tidak valid. Pilih salah satu dari: {', '.join(allowed_roles)}"
        )

    try:
        # A. Daftarkan akun ke Supabase Authentication (Bypass email confirmation)
        auth_response = supabase.auth.admin.create_user({
            "email": payload.email,
            "password": payload.password,
            "email_confirm": True, # Otomatis langsung aktif tanpa klik link verifikasi email
            "user_metadata": {
                "name": payload.full_name,
                "role": payload.role.lower() # Menyimpan role langsung di metadata auth agar cepat dibaca saat login
            }
        })

        user = auth_response.user
        if not user:
            raise HTTPException(status_code=400, detail="Gagal membuat user di sistem autentikasi Supabase")

        # B. Sinkronisasi data profile tambahan ke dalam tabel database "user_profile"
        profile_data = {
            "id": user.id, # Hubungkan ID Auth Supabase dengan ID tabel profile Anda
            "username": payload.username,
            "full_name": payload.full_name,
            "role": payload.role.lower()
        }
        
        supabase.table("user_profile").insert(profile_data).execute()

        return {
            "status": "success",
            "message": f"User baru berhasil didaftarkan!",
            "data": {
                "user_id": user.id,
                "username": payload.username,
                "email": payload.email,
                "role": payload.role.lower()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proses pembuatan user gagal: {str(e)}"
        )