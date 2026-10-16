# 📖 Buku Panduan Penggunaan & Panduan Video Demo MerchantGuard
**AMD Developer Hackathon: ACT III — Track: Reinvent Commerce**  
*Autonomous Dispute & Margin Recovery Copilot powered by AMD ROCm + Google Gemma*

---

## Daftar Isi
1. [Apa itu MerchantGuard? (Konsep Inti)](#1-apa-itu-merchantguard-konsep-inti)
2. [Arsitektur 4-Pilar: Cara Sistem Bekerja](#2-arsitektur-4-pilar-cara-sistem-bekerja)
3. [Langkah Menjalankan Aplikasi di Komputer Lokal](#3-langkah-menjalankan-aplikasi-di-komputer-lokal)
4. [Tur Lengkap Antarmuka (UI Dashboard)](#4-tur-lengkap-antarmuka-ui-dashboard)
5. [Bedah 4 Skenario Demo Utama (Wajib Dipahami!)](#5-bedah-4-skenario-demo-utama-wajib-dipahami)
6. [Fitur-Fitur Interaktif Penting Saat Demo](#6-fitur-fitur-interaktif-penting-saat-demo)
7. [Panduan & Skrip Rekaman Video Demo (Durasi ~3–4 Menit)](#7-panduan--skrip-rekaman-video-demo-durasi-34-menit)
8. [FAQ & Solusi Masalah Teknis Singkat](#8-faq--solusi-masalah-teknis-singkat)

---

## 1. Apa itu MerchantGuard? (Konsep Inti)

Banyak merchant toko online (e-commerce) **kehilangan keuntungan (margin) puluhan hingga ratusan juta rupiah** setiap bulannya akibat sengketa pembayaran (*chargeback* / komplain pembeli palsu):
1. **Pasrah Refund:** Merchant sering langsung mengembalikan uang (*refund*) padahal kurir sudah menyerahkan barang dengan tanda tangan & bukti GPS valid.
2. **Jebakan Biaya (*Economic Fee Trap*):** Merchant nekat melawan sengketa barang murah, padahal biaya arbitrase bank ($15) jauh lebih mahal daripada margin barang yang diselamatkan ($3.80). Hasilnya: merchant malah tekor!
3. **Chatbot Halusinasi:** Model LLM biasa tidak boleh dibiarkan mengambil keputusan hukum/keuangan sendiri karena rawan mengarang tanggal atau menyetujui refund secara keliru.

**MerchantGuard hadir untuk menyelesaikan masalah ini:**
> Keputusan sengketa **TIDAK DIBUAT OLEH LLM**, melainkan oleh **Aturan Kebijakan Deterministik** + **Model Statistik Margin**.  
> LLM terbuka (**Google Gemma-4-31B-IT** di atas infrastruktur **AMD Radeon Cloud**) bertugas khusus merangkai **narasi bukti hukum bersitasi faktual** yang anti-halusinasi. Seluruh jejak keputusan dikunci dalam **Buku Besar Kriptografis SHA-256**.

---

## 2. Arsitektur 4-Pilar: Cara Sistem Bekerja

Saat sebuah sengketa masuk, MerchantGuard memprosesnya melalui 4 tahapan berurutan (*Sequential Streaming*):

```
       [ Kasus Sengketa Pembeli ]
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 1. DETERMINISTIC POLICY GATE (Aturan)   │ ➔ Cek R-001 s/d R-006 (0 Token LLM)
└──────────────────┬──────────────────────┘
                   │ Status Lolos / Perlu Evaluasi
                   ▼
┌─────────────────────────────────────────┐
│ 2. STATISTICAL MARGIN ENGINE (Sklearn)  │ ➔ Prediksi P(Win) & Hitung Rumus EV:
│                                         │    EV = P(win)×(Nilai+Margin) - (1-P(win))×Biaya
└──────────────────┬──────────────────────┘
                   │ Keputusan Final Terkunci (CONTEST / REFUND / ESCALATE)
                   ▼
┌─────────────────────────────────────────┐
│ 3. LLM FACT NARRATOR (AMD + Gemma)      │ ➔ Hasilkan Draf Sanggahan Bersitasi [F1, F2]
│                                         │    Diperiksa oleh Anti-Hallucination Validator
└──────────────────┬──────────────────────┘
                   │ Narasi Faktual Terverifikasi
                   ▼
┌─────────────────────────────────────────┐
│ 4. CRYPTOGRAPHIC AUDIT LEDGER (SHA-256) │ ➔ Rekam hash keputusan ke dalam rantai blok
└─────────────────────────────────────────┘
```

---

## 3. Langkah Menjalankan Aplikasi di Komputer Lokal

Pastikan Anda berada di direktori proyek `d:\merchantguard`.

### Langkah 1: Buka Terminal PowerShell
Jalankan perintah aktivasi virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(Pastikan tanda `(.venv)` muncul di sebelah kiri baris perintah).*

### Langkah 2: Jalankan Server Uvicorn
```powershell
uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload
```
Tunggu hingga muncul pesan:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Langkah 3: Buka Browser
Akses alamat berikut di browser Chrome / Edge:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 4. Tur Lengkap Antarmuka (UI Dashboard)

Saat membuka dashboard, Anda akan melihat antarmuka berdesain *dark mode cyberpunk sleek* dengan bagian-bagian berikut:

### A. Bilah Atas (Header & Status Telemetri)
- **Logo MerchantGuard:** Disertai badge **`AMD ROCm · Google Gemma`**.
- **Inference Tier:** Menampilkan **`AMD ROCm (Gemma-4-31B-IT · LIVE)`** berwarna hijau emerald (menandakan terhubung langsung ke gateway AMD).
- **AMD Gateway Badge:** `Token Factory (Quota: Active)`.
- **Tombol "Verify Ledger":** Tombol untuk memeriksa integritas buku besar SHA-256.

### B. Bagian 1: 4 Tombol Skenario Demo Cepat (1-Click Selector)
Empat kotak skenario di bawah header yang siap diklik untuk pengujian instan:
1. `Scenario 1: Clean Win` (Hijau Emerald)
2. `Scenario 2: Ambiguous Evidence` (Kuning Amber)
3. `Scenario 3: Window Bypass` (Biru Cyan)
4. `Scenario 4: Economic Fee Trap` (Merah Rose)

### C. Bagian 2: Pipeline Stepper (Visualisasi Telemetri SSE)
Indikator 4 langkah visual:
`1. Policy Gate` $\to$ `2. Margin Engine` $\to$ `3. LLM Narration` $\to$ `4. Audit Chain`  
*(Saat skenario diklik, lampu status akan bergerak dari ACTIVE $\to$ COMPLETED secara real-time).*

### D. Kolom Kiri: Bukti Lapangan vs Klaim Pembeli
- **Daftar Antrean Kasus (*Case Queue*):** Menampilkan daftar nomor sengketa beserta nominal nilai uangnya.
- **Perbandingan Klaim Pembeli vs Log Kurir:**
  - Klaim pembeli (alasan komplain, kutipan kalimat pembeli).
  - Telemetri kurir (status pengiriman, tanggal, catatan lapangan).
  - Badge **`GPS MATCH ✓`** dan **`SIGNED ✓`**.

### E. Kolom Kanan: Hasil Keputusan & Narasi Faktual
- **Kartu Keputusan Utama:** Menampilkan aksi yang diputuskan: **`CONTEST`**, **`NEEDS_HUMAN`**, atau **`ACCEPT_REFUND`** beserta estimasi pemulihan margin bersih (**+$226.57**).
- **Rincian Perhitungan Finansial (*Financial Margin Recovery*):** Menampilkan probabilitas menang $P(\text{Win})$, perbandingan potensi kerugian, serta rumus matematika $\text{EV}$ interaktif.
- **Checklist Aturan Gate (R-001 s/d R-006):** Menampilkan aturan yang lolos (**`PASS`**) atau terpicu (**`TRIGGERED`**).
- **Narasi Arbitrase Bersitasi Fakta:** Draf surat resmi yang disusun oleh **Gemma-4-31B-IT** di AMD Token Factory lengkap dengan chip sitasi `[F1: ...]`, `[F2: ...]`.
- **Inspektur Ledger Kriptografis:** Menampilkan nomor indeks blok audit, hash SHA-256 saat ini, dan hash blok sebelumnya.

---

## 5. Bedah 4 Skenario Demo Utama (Wajib Dipahami!)

Setiap juri hackathon akan menilai bagaimana sistem merespons skenario nyata e-commerce. Berikut rahasia dan alasan di balik tiap skenario:

| Skenario | Kasus | Masalah Pembeli | Hasil Keputusan | Mengapa Sistem Mengambil Keputusan Ini? |
|---|---|---|---|---|
| **Skenario 1: Clean Win** | `CASE-1001` | Mengaku tidak terima paket, minta refund penuh. | **`CONTEST`** *(Lawan Sengketa)* | Telemetri kurir membuktikan koordinat GPS cocok 100% dan ada tanda tangan asli penerima ('M. Vance'). Model margin menghitung $P(\text{Win}) = 98\%$ dengan margin pemulihan $+\$226.57$. Gemma merangkai surat sanggahan formal yang menyitir data GPS kurir. |
| **Skenario 2: Ambiguous Evidence** | `CASE-1002` | Mengaku paket dicuri di luar rumah. | **`NEEDS_HUMAN`** *(Eskalasi ke Staf)* | Catatan kurir menuliskan *"left by fence / unattended"*, tanpa tanda tangan. Data ambigu dan berisiko tinggi kalah. Daripada menolak membabi-buta, sistem mengeskalasikan kasus ini ke operator manusia untuk investigasi manual. |
| **Skenario 3: Window Bypass** | `CASE-1003` | Mengajukan klaim komplain pada hari ke-21 setelah barang sampai. | **`CONTEST`** *(Otomatis Ditolak)* | Batas masa komplain kebijakan toko adalah 14 hari. Aturan R-001 mendeteksi pelanggaran batas waktu (21 > 14 hari). Kasus langsung diputuskan tolak **secara deterministik tanpa memanggil LLM** (Hemat token AMD, biaya 0 token, latensi hanya 1 milidetik!). |
| **Skenario 4: Economic Fee Trap** | `CASE-1004` | Komplain pada barang bernilai murah ($12.50) dengan keuntungan toko hanya $3.80. | **`ACCEPT_REFUND`** *(Setujui Refund)* | Biaya arbitrase sengketa bank adalah $15.00. Jika merchant nekat melawan dan kalah, toko rugi $15 + $12.50 = $27.50! Demi mencegah kerugian margin yang lebih besar, aturan R-005 secara cerdas memaksa sistem memilih **ACCEPT_REFUND** (*Margin Protection*). |

---

## 6. Fitur-Fitur Interaktif Penting Saat Demo

Saat merekam video atau demo langsung di depan juri, lakukan interaksi berikut agar tampilan aplikasi terlihat hidup:

1. **Klik Tombol "Verify Ledger" (Di Kanan Atas Header):**
   - Muncul modal popup: **`TAMPER-PROOF AUDIT LEDGER: VALID (UNBROKEN)`**.
   - Jelaskan bahwa setiap keputusan dirangkai dengan hash kriptografis SHA-256 sehingga tidak bisa diubah atau dipalsukan di kemudian hari.
2. **Klik Tombol "Formula" (Di Bagian Expected Value):**
   - Membuka rincian matematika:  
     $$\text{EV} = P(\text{win}) \times (\text{Nilai Pesanan} + \text{Margin}) - (1 - P(\text{win})) \times \text{Biaya Sengketa}$$
   - Tunjukkan bahwa sistem ini transparan (*explainable AI*), bukan kotak hitam (*black box*).
3. **Klik Tombol "Copy Response" (Di Bawah Draf Narasi):**
   - Menghasilkan efek *Copied ✓*, menunjukkan bahwa draf bukti sanggahan dari Gemma siap ditempelkan langsung ke portal pembayaran (Stripe / Shopify / PayPal).

---

## 7. Panduan & Skrip Rekaman Video Demo (Durasi ~3–4 Menit)

Gunakan panduan waktu dan naskah bicara (voiceover) bahasa Indonesia berikut ini saat merekam layar (gunakan OBS Studio atau Xbox Game Bar `Win + G`):

### [0:00 – 0:30] Bagian 1: Pembukaan & Latar Belakang Masalah
- **Aksi Visual:** Tampilkan halaman utama MerchantGuard. Arahkan kursor ke judul dan badge **`AMD ROCm · Google Gemma`**.
- **Contoh Naskah Bicara:**
  > *"Halo juri AMD Hackathon ACT III! Tahukah Anda bahwa merchant e-commerce kehilangan miliaran rupiah margin setiap tahun akibat salah mengambil keputusan sengketa sengketa atau chargeback? Mereka kerap menyerah melakukan refund pada kasus yang sebenarnya bisa dimenangkan, atau sebaliknya, nekat melawan kasus yang biaya dispute perbankannya justru jauh lebih mahal daripada nilai barangnya.*
  > 
  > *Inilah **MerchantGuard**: Copilot Otonom Pemulihan Margin Sengketa yang ditenagai oleh kombinasi deterministik policy gate, model statistik margin, dan model bahasa terbuka Google Gemma-4-31B-IT di atas infrastruktur AMD Radeon Cloud Token Factory."*

### [0:30 – 1:20] Bagian 2: Skenario 1 — Clean Win (Live Inference AMD + Gemma)
- **Aksi Visual:** Klik tombol **`Scenario 1: Clean Win`**. Perhatikan indikator stepper bergerak dari Gate $\to$ Margin $\to$ Narration $\to$ Audit. Tunjukkan chip sitasi `[F1]`, `[F2]`.
- **Contoh Naskah Bicara:**
  > *"Mari kita uji Skenario 1: Kasus sengketa CASE-1001 di mana pembeli mengaku tidak menerima barang. Perhatikan bagaimana streaming SSE berjalan secara real-time.*
  >
  > *Pertama, Policy Gate memverifikasi bahwa pengiriman memiliki GPS cocok dan tanda tangan fisik. Kedua, Model Margin Statistik kami memprediksi probabilitas menang 98% dengan pemulihan margin bersih positif sebesar plus $226.57.*
  >
  > *Ketiga, model **Google Gemma-4-31B-IT** yang berjalan live di **AMD Token Factory** menyusun draf sanggahan arbitrase resmi. Perhatikan chip sitasi ini: setiap klaim terikat pada bukti ground-truth faktual. Model dilarang berhalusinasi dan tidak dapat mengubah keputusan sistem."*

### [1:20 – 2:00] Bagian 3: Skenario 4 — Economic Fee Trap (Margin Protection)
- **Aksi Visual:** Klik tombol **`Scenario 4: Economic Fee Trap`**. Tunjukkan badge berubah menjadi merah rose `ACCEPT_REFUND` dan klik tombol "Formula".
- **Contoh Naskah Bicara:**
  > *"Sekarang mari kita lihat Skenario 4: Jebakan Biaya atau Economic Fee Trap. Di sini, nilai produk kecil dan keuntungan merchant hanya $3.80, sementara biaya sengketa bank mencapai $15.00.*
  >
  > *Jika toko nekat melawan dan kalah, kerugian akan berlipat ganda. MerchantGuard secara cerdas mendeteksi anomali ini melalui aturan R-005 dan memutuskan **ACCEPT_REFUND**. Keputusan ini menyelamatkan margin toko dari jebakan biaya arbitrase yang destruktif."*

### [2:00 – 2:40] Bagian 4: Skenario 2 & 3 — Eskalasi & Efisiensi 0 Token
- **Aksi Visual:** Klik **`Scenario 2`**, lalu klik **`Scenario 3`**.
- **Contoh Naskah Bicara:**
  > *"Pada Skenario 2, kurir mencatat paket ditaruh di dekat pagar tanpa tanda tangan. Karena bukti ambigu, sistem tidak gegabah, melainkan mengeskalasikan kasus ke operator manusia (NEEDS_HUMAN).*
  >
  > *Sedangkan pada Skenario 3, pembeli mengajukan klaim di hari ke-21, melebihi batas kebijakan 14 hari. Sistem langsung menolak secara deterministik pada gerbang aturan pertama—tanpa menghabiskan 1 token LLM pun. Ini bukti arsitektur kami sangat hemat biaya operasional."*

### [2:40 – 3:15] Bagian 5: Integritas Buku Besar SHA-256 (Verify Ledger)
- **Aksi Visual:** Klik tombol **`Verify Ledger`** di kanan atas header. Modal popup hijau akan muncul.
- **Contoh Naskah Bicara:**
  > *"Terakhir, faktor kepatuhan hukum dan audit. Setiap keputusan yang diambil langsung disegel ke dalam Buku Besar Kriptografis SHA-256. Ketika kita klik tombol 'Verify Ledger', sistem memverifikasi rantai hash dari blok genesis hingga kepala rantai saat ini: status VALID dan UNBROKEN. Catatan sengketa tidak dapat dimanipulasi secara retrospektif oleh pihak manapun."*

### [3:15 – 3:40] Bagian 6: Penutup & Keunggulan Arsitektur
- **Aksi Visual:** Tunjukkan footer atau repositori GitHub [OkyWoww/merchantguard](https://github.com/OkyWoww/merchantguard).
- **Contoh Naskah Bicara:**
  > *"MerchantGuard membuktikan bahwa masa depan AI dalam perdagangan bukan sekadar chatbot bebas, melainkan harmoni antara aturan deterministik yang tegas, model keuangan statistik yang presisi, dan model open-weights Google Gemma di atas akselerasi AMD ROCm.*
  >
  > *Seluruh kode sumber, dokumentasi benchmark, dan pengujian unit telah tersedia di repositori GitHub kami. Terima kasih!"*

---

## 8. FAQ & Solusi Masalah Teknis Singkat

### Q1: Muncul error `[Errno 10048] address already in use` saat menyalakan server?
**Solusi:** Port 8000 masih terpakai oleh proses sebelumnya. Matikan proses dengan perintah PowerShell:
```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force
```
Lalu jalankan kembali: `uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload`.

### Q2: Apakah aplikasi tetap berjalan jika kuota atau internet ke AMD Token Factory terputus?
**Ya, 100% tetap berjalan!** MerchantGuard memiliki tangga degradasi (*Degradation Ladder*):
- Jika gateway LIVE gagal atau timeout (>35s), router otomatis beralih ke **Tier 2 (Cached Replay)**.
- Jika cache tidak ada, sistem turun ke **Tier 3 (Deterministic Template Synthesizer)**.  
Aplikasi tidak pernah *crash* dan keputusan sengketa tetap terlindungi.

### Q3: Apakah model Gemma bisa mengganti keputusan dari CONTEST menjadi REFUND?
**Sama sekali tidak bisa.** Arsitektur kami memegang prinsip *invarian*: Keputusan ditentukan secara permanen di Tahap 1 (Gate) dan Tahap 2 (Margin). Gemma hanya bertindak sebagai narator bukti hukum (*fact synthesizer*). Jika LLM mencoba mengusulkan refund pada kasus CONTEST, *Anti-Hallucination Validator* kami akan langsung menolak teks tersebut.
