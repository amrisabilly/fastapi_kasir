from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client
from typing import Optional  # Diperlukan agar tidak terjadi error NameError di Vercel
import os
from fastapi import Header
from .routes import kategori_router, menu_router, ingredients_router, stock_opname_router, customers_router


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
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# 3. VALIDASI SKEMA DATA (PYDANTIC MODELS)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginUsernameRequest(BaseModel):
    username: str
    password: str

class CreateCafeRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Nama kafe/outlet baru")
    address: Optional[str] = Field(None, description="Alamat lokasi kafe")
    manager_id: Optional[str] = Field(None, description="ID manager yang mengelola kafe")

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password minimal 6 karakter")
    username: str = Field(..., min_length=3, description="Username unik pengguna")
    full_name: str = Field(..., description="Nama lengkap pengguna")
    role: str = Field(..., description="Role wajib diisi: 'manager', 'supervisor', atau 'kasir'")
    cafe_id: Optional[str] = Field(None, description="ID kafe (opsional untuk manager)")

class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None

# 4. ENDPOINT: LOGIN EMAIL
@app.post("/api/auth/login", summary="Login menggunakan Email dan Password Supabase")
def login_with_supabase(payload: LoginRequest):
    print(f"DEBUG: Login attempt - Email: {payload.email}")
    try:
        response = get_supabase().auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        user_data = response.user
        session_data = response.session

        if not user_data or not session_data:
            raise HTTPException(status_code=401, detail="Data autentikasi tidak valid")

        user_metadata = user_data.user_metadata if user_data.user_metadata else {}
        user_role = user_metadata.get("role", "kasir")
        full_name = user_metadata.get("name", "Pengguna")
        cafe_id = user_metadata.get("cafe_id", "") 

        return {
            "status": "success",
            "message": "Login berhasil",
            "user": {
                "id": user_data.id,
                "name": full_name,
                "email": user_data.email,
                "role": user_role,
                "cafe_id": cafe_id 
            },
            "token": session_data.access_token
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah."
        )


# 4B. ENDPOINT: LOGIN USERNAME
@app.post("/api/auth/login-username", summary="Login menggunakan Username dan Password")
def login_with_username(payload: LoginUsernameRequest):
    print(f"DEBUG: Login attempt dengan username: {payload.username}")
    try:
        # PERBAIKAN 1: Tambahkan 'cafe_id' di dalam .select()
        user_profile_response = get_supabase().table("user_profile") \
            .select("id, username, email, full_name, role, cafe_id") \
            .eq("username", payload.username) \
            .execute()

        if not user_profile_response.data or len(user_profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah."
            )

        user_profile = user_profile_response.data[0]
        user_id = user_profile["id"]
        email = user_profile.get("email")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Data email tidak ditemukan untuk username ini."
            )

        login_response = get_supabase().auth.sign_in_with_password({
            "email": email,
            "password": payload.password
        })

        session_data = login_response.session
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah."
            )

        return {
            "status": "success",
            "message": "Login berhasil",
            "user": {
                "id": user_profile["id"],
                "username": user_profile["username"],
                "name": user_profile["full_name"],
                "role": user_profile["role"],
                "cafe_id": user_profile.get("cafe_id", "")
            },
            "token": session_data.access_token
        }
    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah."
        )

# 5. ENDPOINT: MEMBUAT KAFE BARU (LANGKAH 1)
@app.post("/create-cafes", summary="Langkah 1: Membuat data kafe baru di sistem")
def create_cafe(payload: CreateCafeRequest):
    try:
        cafe_payload = {
            "name": payload.name,
            "address": payload.address,
            "manager_id": payload.manager_id
        }
        response = get_supabase().table("cafes").insert(cafe_payload).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Gagal menyimpan data kafe.")
            
        new_cafe = response.data[0]
        return {
            "status": "success",
            "message": f"Kafe '{new_cafe['name']}' berhasil didaftarkan!",
            "data": {
                "cafe_id": new_cafe["id"],
                "cafe_name": new_cafe["name"],
                "manager_id": new_cafe.get("manager_id")
            }
        }
    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 6. ENDPOINT: PEMBUATAN USER (LANGKAH 2)
@app.post("/create-user", summary="Langkah 2: Membuat akun user (Manager/Supervisor/Kasir)")
def create_user(payload: CreateUserRequest):
    role_lower = payload.role.lower()
    if role_lower not in ["manager", "supervisor", "kasir"]:
        raise HTTPException(status_code=400, detail="Role tidak valid.")
    
    # Validasi: supervisor dan kasir harus memiliki cafe_id
    if role_lower in ["supervisor", "kasir"] and not payload.cafe_id:
        raise HTTPException(status_code=400, detail="cafe_id wajib diisi untuk supervisor dan kasir.")

    try:
        # A. Daftarkan akun ke Supabase Auth
        user_metadata = {
            "name": payload.full_name,
            "role": role_lower,
        }
        if payload.cafe_id:
            user_metadata["cafe_id"] = payload.cafe_id
            
        auth_response = get_supabase().auth.admin.create_user({
            "email": payload.email,
            "password": payload.password,
            "email_confirm": True,
            "user_metadata": user_metadata
        })

        user = auth_response.user
        if not user:
            raise HTTPException(status_code=400, detail="Gagal membuat akun autentikasi.")

        # B. Simpan data profil ke tabel user_profile
        profile_data = {
            "id": user.id,
            "email": payload.email,
            "username": payload.username,
            "full_name": payload.full_name,
            "role": role_lower,
            "cafe_id": payload.cafe_id  # Akan None jika tidak diisi (untuk manager)
        }
        get_supabase().table("user_profile").insert(profile_data).execute()

        return {
            "status": "success",
            "message": f"Akun dengan role '{role_lower}' berhasil dibuat!",
            "data": {
                "user_id": user.id,
                "username": payload.username,
                "role": role_lower,
                "cafe_id": payload.cafe_id
            }
        }
    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/users")
def get_employees(cafe_id: str):
    try:
        response = get_supabase().table("user_profile") \
            .select("*") \
            .eq("cafe_id", cafe_id) \
            .execute()
            
        filtered_data = [
            emp for emp in response.data 
            if emp.get("role", "").lower() in ["supervisor", "kasir"]
        ]
        return {"status": "success", "data": filtered_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 7. ENDPOINT: EDIT DATA KARYAWAN
@app.put("/api/users/{user_id}", summary="Memperbarui data akun karyawan")
def update_employee(user_id: str, payload: UpdateUserRequest):
    try:
        # A. Update data Auth di Supabase (jika data opsional diisi)
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
            get_supabase().auth.admin.update_user_by_id(user_id, auth_updates)

        # B. Update data di tabel database user_profile
        profile_updates = {}
        if payload.username:
            profile_updates["username"] = payload.username
        if payload.full_name:
            profile_updates["full_name"] = payload.full_name
        if payload.role:
            profile_updates["role"] = payload.role.lower()

        if profile_updates:
            get_supabase().table("user_profile").update(profile_updates).eq("id", user_id).execute()

        return {
            "status": "success",
            "message": "Data karyawan berhasil diperbarui"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal memperbarui data: {str(e)}"
        )


# 8. ENDPOINT: HAPUS AKUN KARYAWAN
@app.delete("/api/users/{user_id}", summary="Menghapus akun karyawan dari sistem")
def delete_employee(user_id: str):
    try:
        get_supabase().auth.admin.delete_user(user_id)
        return {
            "status": "success",
            "message": "Akun karyawan berhasil dihapus dari sistem"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal menghapus akun: {str(e)}"
        )
    
@app.get("/api/cafes", summary="Mengambil daftar kafe/cabang milik seorang Manager")
def get_manager_cafes(manager_id: str):
    try:
        response = get_supabase().table("cafes").select("*").eq("manager_id", manager_id).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Inisiasi rute
app.include_router(kategori_router)
app.include_router(menu_router)
app.include_router(ingredients_router)
app.include_router(stock_opname_router)
app.include_router(customers_router)