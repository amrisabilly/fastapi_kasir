# ☕ Coffee Shop API - Cloud Computing Project

[cite_start]Proyek ini adalah implementasi **Application Programming Interface (API)** menggunakan framework **FastAPI** (Python) untuk memenuhi tugas mata kuliah Teknologi Cloud Computing (SI-A)[cite: 1]. API ini menyediakan layanan pengelolaan data menu kopi dengan fitur pencarian dan perhitungan statistik harga.

## 🚀 Fitur Utama
[cite_start]Sesuai dengan spesifikasi tugas[cite: 3, 4], API ini memiliki:
1. **3 Jenis Layanan**:
    * **Data Retrieval**: Mengambil daftar lengkap menu kopi.
    * **Searching**: Mencari menu kopi berdasarkan nama.
    * **Komputasi Sederhana**: Menghitung total harga, rata-rata, dan harga tertinggi dari seluruh menu.
2. **3 Endpoint Utama**: `/menu`, `/menu/search`, dan `/menu/stats`.
3. **Dokumentasi Otomatis**: Mendukung Swagger UI (`/docs`).

## 🛠️ Tech Stack
* **Language**: Python
* **Framework**: FastAPI
* **Hosting**: Vercel (Cloud Deployment)
* **Standard**: ISO/IEC 25010 (Software Quality)

## 📌 Endpoint API

| Method | Endpoint | Fungsi | Jenis Layanan |
| :--- | :--- | :--- | :--- |
| `GET` | `/menu` | Mengambil seluruh daftar menu kopi | Data Retrieval |
| `GET` | `/menu/search` | Mencari kopi berdasarkan parameter `name` | Searching |
| `GET` | `/menu/stats` | Menghitung statistik harga menu | Komputasi |

## 💻 Cara Menjalankan Secara Lokal

1. **Clone Repository**
   ```bash
   git clone [https://github.com/amrisabilly/proyektcc.git](https://github.com/amrisabilly/proyektcc.git)
   cd proyektcc