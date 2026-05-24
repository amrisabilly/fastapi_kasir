from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import os
from supabase import create_client

router = APIRouter(prefix="/api/customers", tags=["Pelanggan & Promo"])

def get_supabase():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# SKEMA PYDANTIC (VALIDASI DATA)
# ==========================================
class LoyaltySettingUpdate(BaseModel):
    cafe_id: str
    earn_amount_per_point: float
    reward_type: str = Field(..., description="'rupiah' atau 'percentage'")
    reward_value: float

class CustomerCreate(BaseModel):
    cafe_id: str
    name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=9)
    points: float = 0

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    points: Optional[float] = None


# ==========================================
# 1. ENDPOINT: PENGATURAN POIN (SETTINGS)
# ==========================================

@router.get("/settings", summary="Ambil pengaturan loyalitas kafe")
def get_loyalty_settings(cafe_id: str):
    db = get_supabase()
    response = db.table("loyalty_settings").select("*").eq("cafe_id", cafe_id).execute()
    
    if not response.data:
        return {"status": "success", "data": None, "message": "Belum ada pengaturan"}
    return {"status": "success", "data": response.data[0]}


@router.post("/settings", summary="Simpan/Update pengaturan loyalitas")
def upsert_loyalty_settings(payload: LoyaltySettingUpdate):
    db = get_supabase()
    data = payload.dict()
    
    try:
        # Cek apakah cabang ini sudah punya pengaturan
        existing = db.table("loyalty_settings").select("id").eq("cafe_id", payload.cafe_id).execute()
        
        if existing.data:
            # Jika sudah ada, UPDATE datanya
            res = db.table("loyalty_settings").update(data).eq("cafe_id", payload.cafe_id).execute()
        else:
            # Jika belum ada, INSERT data baru
            res = db.table("loyalty_settings").insert(data).execute()
            
        return {"status": "success", "message": "Pengaturan Poin berhasil disimpan!", "data": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menyimpan pengaturan: {str(e)}")


# ==========================================
# 2. ENDPOINT: CRUD DATA PELANGGAN (MEMBER)
# ==========================================

@router.get("/", summary="Ambil daftar pelanggan / cari berdasarkan nomor HP")
def get_customers(cafe_id: str, phone: Optional[str] = None):
    db = get_supabase()
    query = db.table("customers").select("*").eq("cafe_id", cafe_id)
    
    # Fitur pencarian otomatis di kasir (berdasarkan nomor HP)
    if phone:
        query = query.ilike("phone", f"%{phone}%")
        
    try:
        # Urutkan berdasarkan waktu daftar terbaru
        response = query.order("created_at", desc=True).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", summary="Daftarkan pelanggan baru")
def create_customer(payload: CustomerCreate):
    db = get_supabase()
    
    try:
        # Validasi: Cek apakah nomor HP sudah terdaftar di cabang yang sama
        check_phone = db.table("customers").select("id").eq("cafe_id", payload.cafe_id).eq("phone", payload.phone).execute()
        
        if check_phone.data:
            raise HTTPException(status_code=400, detail="Nomor Handphone ini sudah terdaftar sebagai member!")
            
        response = db.table("customers").insert(payload.dict()).execute()
        return {"status": "success", "message": "Member baru berhasil didaftarkan!", "data": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{customer_id}", summary="Update data pelanggan (Edit nama/HP/Poin)")
def update_customer(customer_id: str, payload: CustomerUpdate):
    db = get_supabase()
    
    # Hapus field yang bernilai None dari payload
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Tidak ada data yang diubah")
        
    try:
        response = db.table("customers").update(update_data).eq("id", customer_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")
            
        return {"status": "success", "message": "Data member berhasil diupdate", "data": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{customer_id}", summary="Hapus data pelanggan")
def delete_customer(customer_id: str):
    db = get_supabase()
    try:
        # Berkat ON DELETE CASCADE di database, ini aman dilakukan
        response = db.table("customers").delete().eq("id", customer_id).execute()
        
        if not response.data:
             raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")
             
        return {"status": "success", "message": "Data member berhasil dihapus"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))