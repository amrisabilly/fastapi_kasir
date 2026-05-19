from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client
from typing import Optional
import os

app = FastAPI(
    title="Management Karyawan API",
    description="Backend API untuk sistem management karyawan menggunakan FastAPI dan Supabase Auth",
    version="1.1.0"
)

# 1. KONFIGURASI CORS
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
# PENTING: Gunakan SERVICE_ROLE_KEY agar bisa melakukan bypass RLS database, create, update, dan delete user auth.
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ghowabpmxojzlbbskbzn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "ISI_DENGAN_SERVICE_ROLE_KEY_ANDA")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# 3. VALIDASI SKEMA DATA (PYDANTIC MODELS)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    username: str = Field(..., min_length=3)
    full_name: str
    role: str # 'manager', 'supervisor', atau 'kasir'

class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None


# 4. ENDPOINT: LOGIN
@app.post("/api/auth/login")
def login_with_supabase(payload: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        user_data = response.user
        session_data = response.session

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
                "role": user_role,
            },
            "token": session_data.access_token
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Email atau password salah.")


# 5. ENDPOINT: POST - BUAT USER BARU
@app.post("/create-user")
def create_user(payload: CreateUserRequest):
    role_lower = payload.role.lower()
    if role_lower not in ["manager", "supervisor", "kasir"]:
        raise HTTPException(status_code=400, detail="Role tidak valid.")

    try:
        # A. Buat user di Supabase Auth
        auth_response = supabase.auth.admin.create_user({
            "email": payload.email,
            "password": payload.password,
            "email_confirm": True,
            "user_metadata": {
                "name": payload.full_name,
                "role": role_lower
            }
        })

        user = auth_response.user
        if not user:
            raise HTTPException(status_code=400, detail="Gagal membuat akun auth.")

        # B. Simpan data profil ke tabel user_profile
        profile_data = {
            "id": user.id,
            "username": payload.username,
            "full_name": payload.full_name,
            "role": role_lower
        }
        supabase.table("user_profile").insert(profile_data).execute()

        return {
            "status": "success",
            "message": "Karyawan berhasil didaftarkan!",
            "data": {
                "user_id": user.id,
                "username": payload.username,
                "email": payload.email,
                "role": role_lower
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 6. ENDPOINT (PERBAIKAN): GET ALL EMPLOYEES (SUPERVISOR & KASIR)
@app.get("/api/users")
def get_employees():
    try:
        # Perbaikan query: Kita ambil semua data profil karyawan dari database.
        # Menghapus filter filter kaku .in_() untuk memastikan data ditarik terlebih dahulu.
        response = supabase.table("user_profile").select("*").execute()
        
        # Saring data di tingkat aplikasi agar fleksibel (tidak sensitif huruf besar/kecil)
        filtered_data = [
            emp for emp in response.data 
            if emp.get("role", "").lower() in ["supervisor", "kasir"]
        ]
        
        return {
            "status": "success",
            "data": filtered_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat data: {str(e)}")


# 7. ENDPOINT: PUT - UPDATE/EDIT DATA KARYAWAN
@app.put("/api/users/{user_id}")
def update_employee(user_id: str, payload: UpdateUserRequest):
    try:
        # A. Update data Auth di Supabase (jika email atau password diubah)
        auth_updates = {}
        if payload.email:
            auth_updates["email"] = payload.email
        if payload.password:
            auth_updates["password"] = payload.password
        if payload.full_name or payload.role:
            auth_updates["user_metadata"] = {}
            if payload.full_name:
                auth_updates["user_metadata"]["name"] = payload.full_name
            if payload.role:
                auth_updates["user_metadata"]["role"] = payload.role.lower()

        if auth_updates:
            supabase.auth.admin.update_user_by_id(user_id, auth_updates)

        # B. Update data di tabel user_profile database
        profile_updates = {}
        if payload.username:
            profile_updates["username"] = payload.username
        if payload.full_name:
            profile_updates["full_name"] = payload.full_name
        if payload.role:
            profile_updates["role"] = payload.role.lower()

        if profile_updates:
            supabase.table("user_profile").update(profile_updates).eq("id", user_id).execute()

        return {
            "status": "success",
            "message": "Data karyawan berhasil diperbarui"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal memperbarui data: {str(e)}")


# 8. ENDPOINT: DELETE - HAPUS AKUN KARYAWAN
@app.delete("/api/users/{user_id}")
def delete_employee(user_id: str):
    try:
        # Menghapus user dari autentikasi utama Supabase.
        # Karena tabel user_profile menggunakan ON DELETE CASCADE, 
        # baris data di tabel user_profile otomatis akan ikut terhapus secara otomatis.
        supabase.auth.admin.delete_user(user_id)
        
        return {
            "status": "success",
            "message": "Akun karyawan berhasil dihapus dari sistem"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menghapus akun: {str(e)}")