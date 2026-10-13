## Tentang Dataset

### Asal Data dan Disclaimer

Proyek ini menggunakan **dataset Point of Sale (POS) sintetis yang dibuat secara programatis menggunakan Python dengan bantuan AI dalam pengembangan generator data**. Dataset ini bukan berasal dari perusahaan, restoran, kafe, sistem POS, ataupun basis data transaksi komersial yang nyata.

Seluruh data outlet, produk, transaksi, harga, kuantitas, pembayaran, dan permasalahan kualitas data dibuat secara artifisial untuk keperluan pembelajaran dan portofolio. Data ini tidak merepresentasikan aktivitas bisnis atau transaksi pelanggan yang sebenarnya.

Dataset dirancang untuk menyimulasikan lingkungan bisnis Food & Beverage (F&B) dengan banyak outlet, sekaligus mendemonstrasikan bagaimana pipeline Data Engineering memproses data transaksional dalam volume besar.

### Ringkasan Dataset

Simulasi bisnis ini terdiri dari 30 outlet yang beroperasi selama periode 30 hari. Data transaksi dihasilkan menggunakan Python dengan *random seed* tetap untuk mendukung reproduksibilitas selama konfigurasi dan kode generator tidak berubah.

| Atribut | Deskripsi |
|---|---|
| Domain bisnis | Food & Beverage (F&B) |
| Sumber data | Data sintetis yang dihasilkan menggunakan Python |
| Peran AI | Pembuatan Script generator untuk Data POS |
| Jumlah outlet | 30 |
| Periode simulasi | 30 hari |
| Target jumlah transaksi | 225.000 |
| Katalog produk | 100 entri menu sintetis |
| Item transaksi | Satu atau lebih item pada setiap transaksi |
| Data pembayaran | Satu catatan pembayaran per transaksi pada baseline |
| Mata uang | Rupiah Indonesia (IDR) |
| Format data | CSV |
| Anomali data | Permasalahan kualitas data yang sengaja disisipkan |

Volume transaksi dan jumlah record di atas merupakan target berdasarkan konfigurasi generator. Jumlah aktual dapat berbeda apabila konfigurasi atau logika pembuatan data diubah.

### Struktur Dataset

Dataset terdiri dari beberapa komponen berikut:

| File | Deskripsi |
|---|---|
| `outlets.csv` | ID outlet, nama outlet, dan kota yang disimulasikan |
| `products.csv` | Katalog produk sintetis, kategori, harga jual, dan biaya per unit |
| `transactions.csv` | Informasi utama transaksi, termasuk waktu, outlet, jenis pesanan, metode pembayaran, status, dan total transaksi |
| `transaction_items.csv` | Detail item transaksi, termasuk ID produk, kuantitas, diskon, total item, dan biaya simulasi |
| `payments.csv` | Catatan pembayaran yang terhubung dengan setiap transaksi |

Data POS kemudian diorganisasikan menjadi batch ekspor harian untuk setiap outlet. Setiap batch berisi file CSV transaksi, detail item transaksi, dan pembayaran.

File manifest dan label anomali tambahan disediakan untuk mendukung pelacakan batch, validasi kualitas data, dan evaluasi pipeline.

### Simulasi Permasalahan Kualitas Data

Untuk mereproduksi tantangan yang umum ditemukan dalam proses Data Engineering, sebagian transaksi sengaja dimodifikasi pada tahap ekspor data.

Jenis anomali yang disimulasikan meliputi:

- **Ketidaksesuaian pembayaran (*payment mismatch*):** nominal pembayaran tidak sama dengan total transaksi.
- **Referensi produk tidak valid:** item transaksi merujuk pada ID produk yang tidak terdapat dalam katalog produk.
- **Kuantitas tidak valid:** item transaksi memiliki kuantitas nol atau negatif.
- **Transaksi duplikat:** satu record transaksi muncul lebih dari satu kali dalam suatu batch.

Target tingkat anomali secara default adalah 2% dari transaksi sumber. Jumlah aktual dan distribusi setiap jenis anomali dicatat dalam metadata yang dihasilkan.

File *ground truth* terpisah digunakan untuk mencatat anomali yang sengaja disisipkan. File ini berfungsi sebagai acuan evaluasi dan tidak boleh digunakan oleh logika deteksi anomali pada pipeline, karena tujuan proyek adalah mendeteksi masalah berdasarkan data transaksi itu sendiri.

### Batasan Dataset

Dataset ini merupakan simulasi terkontrol, bukan representasi langsung dari data operasional bisnis F&B di dunia nyata.

- Nama produk, informasi outlet, volume transaksi, harga, dan pola pembayaran bersifat sintetis.
- Dataset tidak memuat informasi pelanggan nyata ataupun transaksi keuangan aktual.
- Aturan bisnis dan anomali data disederhanakan untuk keperluan pembelajaran dan pengujian.
- *Random seed* tetap membantu reproduksibilitas, tetapi perubahan kode atau konfigurasi dapat mengubah hasil.
- Keberhasilan validasi menggunakan dataset ini tidak menjamin pipeline dapat menangani seluruh permasalahan yang ditemukan pada sistem POS produksi.

### Tujuan Penggunaan Dataset

Dataset ini digunakan untuk membangun dan mengevaluasi pipeline pemrosesan data batch menggunakan Apache Airflow.

Ruang lingkup pengembangan proyek meliputi:

1. Ingesti batch dari ekspor data berbagai outlet.
2. Validasi skema dan integritas referensial.
3. Rekonsiliasi transaksi dan pembayaran.
4. Pemantauan kualitas data dan deteksi anomali.
5. Karantina record yang tidak valid.
6. Pemrosesan data yang andal dan *idempotent*.
7. Pemuatan data tervalidasi ke dalam *analytical data warehouse*.

**Pernyataan transparansi:** Proyek ini mendemonstrasikan keterampilan Data Engineering menggunakan data sintetis. Proyek ini tidak mengklaim memiliki akses ke data POS eksklusif maupun pengalaman memproses transaksi aktual dari bisnis yang disimulasikan.
