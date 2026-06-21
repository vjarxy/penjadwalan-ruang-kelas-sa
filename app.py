from flask import Flask, request, redirect, session, render_template_string, url_for, flash
import mysql.connector
from mysql.connector import IntegrityError
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = "secret-key-project-penjadwalan"


# ============================================================
# KONFIGURASI DATABASE MYSQL
# ============================================================

DB_CONFIG = {
    "host": "sql.freedb.tech",
    "user": "u_z6M1TI",
    "password": "9PerXwHpsuQf",
    "database": "freedb_GGSui8CO",  
}


class Database:
    """
    Wrapper agar pemakaian MySQL tetap mirip kode awal:
    db.execute(...).fetchone(), db.execute(...).fetchall(), db.commit(), db.close()
    """

    def __init__(self):
        self.conn = mysql.connector.connect(**DB_CONFIG)

    def execute(self, sql, params=None):
        sql = sql.replace("INSERT OR IGNORE", "INSERT IGNORE")
        sql = sql.replace("?", "%s")
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        return cursor

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db():
    return Database()


# ============================================================
# HELPER LOGIN DAN TEMPLATE
# ============================================================

def login_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if role is not None and session.get("role") != role:
                flash("Anda tidak memiliki akses ke halaman tersebut.", "danger")
                return redirect(url_for("index"))

            return func(*args, **kwargs)
        return wrapper
    return decorator


BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f3f4f6;
            margin: 0;
            padding: 0;
        }
        header {
            background: #1f2937;
            color: white;
            padding: 18px 30px;
        }
        header h1 {
            margin: 0;
            font-size: 22px;
        }
        nav {
            background: #374151;
            padding: 12px 30px;
        }
        nav a {
            color: white;
            text-decoration: none;
            margin-right: 16px;
            font-weight: bold;
        }
        .container {
            padding: 25px 30px;
        }
        .card {
            background: white;
            padding: 18px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }
        input, select, button {
            padding: 8px;
            margin: 4px;
        }
        button, .btn {
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 8px 12px;
            text-decoration: none;
            cursor: pointer;
            display: inline-block;
        }
        .btn-danger { background: #dc2626; }
        .btn-success { background: #16a34a; }
        .btn-warning { background: #d97706; }
        .btn-secondary { background: #4b5563; }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 12px;
            background: white;
        }
        th, td {
            border: 1px solid #d1d5db;
            padding: 9px;
            font-size: 14px;
            vertical-align: top;
        }
        th { background: #e5e7eb; }
        .success {
            background: #dcfce7;
            color: #166534;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .danger {
            background: #fee2e2;
            color: #991b1b;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .warning {
            background: #fef3c7;
            color: #92400e;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .badge {
            padding: 4px 8px;
            border-radius: 5px;
            background: #e5e7eb;
            font-size: 12px;
            font-weight: bold;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
        }
        .small { font-size: 13px; color: #4b5563; }
    </style>
</head>
<body>
    <header>
        <h1>{{ title }}</h1>
        {% if session.get('username') %}
            <p>
                Login sebagai: <b>{{ session.get('username') }}</b>
                | Role: <b>{{ session.get('role') }}</b>
            </p>
        {% endif %}
    </header>

    {% if session.get('username') %}
    <nav>
        <a href="/">Beranda</a>
        {% if session.get('role') == 'admin' %}
            <a href="/admin/data">Kelola Data</a>
            <a href="/admin/jadwal">Persetujuan Jadwal</a>
        {% endif %}
        {% if session.get('role') == 'dosen' %}
            <a href="/dosen">Jadwal Dosen</a>
            <a href="/dosen/pilih_jadwal">Pilih Jadwal</a>
        {% endif %}
        {% if session.get('role') == 'mahasiswa' %}
            <a href="/mahasiswa">Jadwal Mahasiswa</a>
        {% endif %}
        <a href="/logout">Logout</a>
    </nav>
    {% endif %}

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        CONTENT
    </div>
</body>
</html>
"""


def render_page(title, content, **context):
    html = BASE_HTML.replace("CONTENT", content)
    return render_template_string(html, title=title, **context)


# ============================================================
# ROUTE UTAMA
# ============================================================

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    if session.get("role") == "dosen":
        return redirect(url_for("dosen_dashboard"))
    if session.get("role") == "mahasiswa":
        return redirect(url_for("mahasiswa_dashboard"))

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        db.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["ref_id"] = user["ref_id"]
            flash("Login berhasil.", "success")
            return redirect(url_for("index"))

        flash("Username atau password salah.", "danger")

    content = """
    <div class="card">
        <h2>Login Sistem</h2>
        <form method="POST">
            <p>Username</p>
            <input type="text" name="username" required>
            <p>Password</p>
            <input type="password" name="password" required>
            <br><br>
            <button type="submit">Login</button>
        </form>
    </div>
    """
    return render_page("Login Sistem Penjadwalan Ruang Kelas", content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    db = get_db()
    total_dosen = db.execute("SELECT COUNT(*) AS total FROM dosen").fetchone()["total"]
    total_mahasiswa = db.execute("SELECT COUNT(*) AS total FROM mahasiswa").fetchone()["total"]
    total_matkul = db.execute("SELECT COUNT(*) AS total FROM mata_kuliah").fetchone()["total"]
    total_ruang = db.execute("SELECT COUNT(*) AS total FROM ruang").fetchone()["total"]
    total_slot = db.execute("SELECT COUNT(*) AS total FROM slot_waktu").fetchone()["total"]
    total_jadwal = db.execute("SELECT COUNT(*) AS total FROM jadwal").fetchone()["total"]
    menunggu = db.execute("SELECT COUNT(*) AS total FROM jadwal WHERE status_jadwal = 'menunggu_persetujuan'").fetchone()["total"]
    final = db.execute("SELECT COUNT(*) AS total FROM jadwal WHERE status_jadwal = 'final'").fetchone()["total"]
    bentrok = db.execute("SELECT COUNT(*) AS total FROM jadwal WHERE status_jadwal = 'bentrok'").fetchone()["total"]
    db.close()

    content = """
    <div class="card">
        <h2>Dashboard Admin</h2>
        <p>Admin menginput data dasar. Dosen memilih jadwal sendiri. Admin menyetujui jadwal yang sudah diajukan dosen.</p>
    </div>

    <div class="grid">
        <div class="card"><h3>Dosen</h3><p><b>{{ total_dosen }}</b></p></div>
        <div class="card"><h3>Mahasiswa</h3><p><b>{{ total_mahasiswa }}</b></p></div>
        <div class="card"><h3>Mata Kuliah</h3><p><b>{{ total_matkul }}</b></p></div>
        <div class="card"><h3>Ruang</h3><p><b>{{ total_ruang }}</b></p></div>
        <div class="card"><h3>Slot Waktu</h3><p><b>{{ total_slot }}</b></p></div>
        <div class="card"><h3>Total Jadwal</h3><p><b>{{ total_jadwal }}</b></p></div>
        <div class="card"><h3>Menunggu Persetujuan</h3><p><b>{{ menunggu }}</b></p></div>
        <div class="card"><h3>Final</h3><p><b>{{ final }}</b></p></div>
        <div class="card"><h3>Bentrok</h3><p><b>{{ bentrok }}</b></p></div>
    </div>

    <div class="card">
        <a class="btn" href="/admin/data">Kelola Data</a>
        <a class="btn btn-warning" href="/admin/jadwal">Persetujuan Jadwal</a>
    </div>
    """

    return render_page(
        "Dashboard Admin",
        content,
        total_dosen=total_dosen,
        total_mahasiswa=total_mahasiswa,
        total_matkul=total_matkul,
        total_ruang=total_ruang,
        total_slot=total_slot,
        total_jadwal=total_jadwal,
        menunggu=menunggu,
        final=final,
        bentrok=bentrok,
    )


# ============================================================
# ADMIN KELOLA DATA
# ============================================================

@app.route("/admin/data")
@login_required("admin")
def admin_data():
    db = get_db()
    dosen = db.execute("SELECT * FROM dosen ORDER BY nip").fetchall()
    mahasiswa = db.execute("SELECT * FROM mahasiswa ORDER BY nim").fetchall()
    matkul = db.execute("""
        SELECT m.*, d.nama_dosen
        FROM mata_kuliah m
        LEFT JOIN dosen d ON m.nip = d.nip
        ORDER BY m.kode_matkul
    """).fetchall()
    ruang = db.execute("SELECT * FROM ruang ORDER BY kode_ruang").fetchall()
    slot = db.execute("SELECT * FROM slot_waktu ORDER BY kode_slot").fetchall()
    db.close()

    content = """
    <div class="card">
        <h2>Tambah Dosen</h2>
        <form method="POST" action="/admin/tambah_dosen">
            <input name="nip" placeholder="NIP Dosen" required>
            <input name="nama_dosen" placeholder="Nama Dosen" required>
            <input name="email" placeholder="Email">
            <button type="submit">Simpan Dosen</button>
        </form>
        <p class="small">Akun login dosen otomatis dibuat dengan username = NIP kecil dan password = dosen123.</p>
    </div>

    <div class="card">
        <h2>Tambah Mahasiswa</h2>
        <form method="POST" action="/admin/tambah_mahasiswa">
            <input name="nim" placeholder="NIM" required>
            <input name="nama_mahasiswa" placeholder="Nama Mahasiswa" required>
            <input name="email" placeholder="Email">
            <input name="semester" type="number" placeholder="Semester" required>
            <input name="kelas" placeholder="Kelas, contoh TI-2A" required>
            <button type="submit">Simpan Mahasiswa</button>
        </form>
        <p class="small">Akun login mahasiswa otomatis dibuat dengan username = NIM dan password = mhs123.</p>
    </div>

    <div class="card">
        <h2>Tambah Mata Kuliah</h2>
        <form method="POST" action="/admin/tambah_matkul">
            <input name="kode_matkul" placeholder="Kode Matkul" required>
            <input name="nama_matkul" placeholder="Nama Matkul" required>
            <select name="nip" required>
                {% for d in dosen %}
                    <option value="{{ d.nip }}">{{ d.nip }} - {{ d.nama_dosen }}</option>
                {% endfor %}
            </select>
            <input name="kelas" placeholder="Kelas" required>
            <input name="semester" type="number" placeholder="Semester" required>
            <input name="jumlah_mahasiswa" type="number" placeholder="Jumlah Mahasiswa" required>
            <input name="durasi" type="number" placeholder="Durasi Jam" required>
            <select name="jenis_kegiatan">
                <option value="teori">Teori</option>
                <option value="praktikum">Praktikum</option>
            </select>
            <select name="kebutuhan_ruang">
                <option value="kelas">Kelas</option>
                <option value="laboratorium">Laboratorium</option>
            </select>
            <button type="submit">Simpan Mata Kuliah</button>
        </form>
    </div>

    <div class="card">
        <h2>Tambah Ruang</h2>
        <form method="POST" action="/admin/tambah_ruang">
            <input name="kode_ruang" placeholder="Kode Ruang" required>
            <input name="nama_ruang" placeholder="Nama Ruang" required>
            <input name="kapasitas" type="number" placeholder="Kapasitas" required>
            <select name="jenis_ruang">
                <option value="kelas">Kelas</option>
                <option value="laboratorium">Laboratorium</option>
            </select>
            <input name="lokasi" placeholder="Lokasi">
            <button type="submit">Simpan Ruang</button>
        </form>
    </div>

    <div class="card">
        <h2>Tambah Slot Waktu</h2>
        <form method="POST" action="/admin/tambah_slot">
            <input name="kode_slot" placeholder="Kode Slot" required>
            <select name="hari">
                <option>Senin</option>
                <option>Selasa</option>
                <option>Rabu</option>
                <option>Kamis</option>
                <option>Jumat</option>
            </select>
            <input name="jam_mulai" placeholder="Jam Mulai, contoh 08:00" required>
            <input name="jam_selesai" placeholder="Jam Selesai, contoh 10:00" required>
            <button type="submit">Simpan Slot</button>
        </form>
    </div>

    <div class="card">
        <h2>Data Dosen</h2>
        <table>
            <tr><th>NIP</th><th>Nama</th><th>Email</th><th>Status</th><th>Aksi</th></tr>
            {% for d in dosen %}
            <tr>
                <td>{{ d.nip }}</td><td>{{ d.nama_dosen }}</td><td>{{ d.email }}</td><td>{{ d.status }}</td>
                <td><a class="btn btn-danger" href="/admin/hapus/dosen/{{ d.nip }}">Hapus</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h2>Data Mahasiswa</h2>
        <table>
            <tr><th>NIM</th><th>Nama</th><th>Kelas</th><th>Semester</th><th>Status</th><th>Aksi</th></tr>
            {% for m in mahasiswa %}
            <tr>
                <td>{{ m.nim }}</td><td>{{ m.nama_mahasiswa }}</td><td>{{ m.kelas }}</td><td>{{ m.semester }}</td><td>{{ m.status }}</td>
                <td><a class="btn btn-danger" href="/admin/hapus/mahasiswa/{{ m.nim }}">Hapus</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h2>Data Mata Kuliah</h2>
        <table>
            <tr><th>Kode</th><th>Nama Matkul</th><th>Dosen</th><th>Kelas</th><th>Jumlah Mhs</th><th>Jenis</th><th>Kebutuhan Ruang</th><th>Aksi</th></tr>
            {% for m in matkul %}
            <tr>
                <td>{{ m.kode_matkul }}</td><td>{{ m.nama_matkul }}</td><td>{{ m.nama_dosen }}</td><td>{{ m.kelas }}</td>
                <td>{{ m.jumlah_mahasiswa }}</td><td>{{ m.jenis_kegiatan }}</td><td>{{ m.kebutuhan_ruang }}</td>
                <td><a class="btn btn-danger" href="/admin/hapus/matkul/{{ m.kode_matkul }}">Hapus</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h2>Data Ruang</h2>
        <table>
            <tr><th>Kode</th><th>Nama Ruang</th><th>Kapasitas</th><th>Jenis</th><th>Lokasi</th><th>Status</th><th>Aksi</th></tr>
            {% for r in ruang %}
            <tr>
                <td>{{ r.kode_ruang }}</td><td>{{ r.nama_ruang }}</td><td>{{ r.kapasitas }}</td><td>{{ r.jenis_ruang }}</td><td>{{ r.lokasi }}</td><td>{{ r.status }}</td>
                <td><a class="btn btn-danger" href="/admin/hapus/ruang/{{ r.kode_ruang }}">Hapus</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h2>Data Slot Waktu</h2>
        <table>
            <tr><th>Kode Slot</th><th>Hari</th><th>Jam</th><th>Aksi</th></tr>
            {% for s in slot %}
            <tr>
                <td>{{ s.kode_slot }}</td><td>{{ s.hari }}</td><td>{{ s.jam_mulai }} - {{ s.jam_selesai }}</td>
                <td><a class="btn btn-danger" href="/admin/hapus/slot/{{ s.kode_slot }}">Hapus</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """

    return render_page("Kelola Data Sistem", content, dosen=dosen, mahasiswa=mahasiswa, matkul=matkul, ruang=ruang, slot=slot)


@app.route("/admin/tambah_dosen", methods=["POST"])
@login_required("admin")
def tambah_dosen():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO dosen (nip, nama_dosen, email, status) VALUES (?, ?, ?, 'aktif')",
            (request.form["nip"], request.form["nama_dosen"], request.form["email"])
        )
        db.execute(
            "INSERT IGNORE INTO users (username, password, role, ref_id) VALUES (?, 'dosen123', 'dosen', ?)",
            (request.form["nip"].lower(), request.form["nip"])
        )
        db.commit()
        flash("Data dosen berhasil ditambahkan. Akun dosen otomatis dibuat.", "success")
    except IntegrityError:
        db.rollback()
        flash("NIP dosen sudah ada.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_data"))


@app.route("/admin/tambah_mahasiswa", methods=["POST"])
@login_required("admin")
def tambah_mahasiswa():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO mahasiswa (nim, nama_mahasiswa, email, semester, kelas, status) VALUES (?, ?, ?, ?, ?, 'aktif')",
            (request.form["nim"], request.form["nama_mahasiswa"], request.form["email"], request.form["semester"], request.form["kelas"])
        )
        db.execute(
            "INSERT IGNORE INTO users (username, password, role, ref_id) VALUES (?, 'mhs123', 'mahasiswa', ?)",
            (request.form["nim"], request.form["kelas"])
        )
        db.commit()
        flash("Data mahasiswa berhasil ditambahkan. Akun mahasiswa otomatis dibuat.", "success")
    except IntegrityError:
        db.rollback()
        flash("NIM mahasiswa sudah ada.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_data"))


@app.route("/admin/tambah_matkul", methods=["POST"])
@login_required("admin")
def tambah_matkul():
    db = get_db()
    try:
        db.execute("""
            INSERT INTO mata_kuliah
            (kode_matkul, nama_matkul, nip, kelas, semester, jumlah_mahasiswa, durasi, jenis_kegiatan, kebutuhan_ruang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["kode_matkul"], request.form["nama_matkul"], request.form["nip"],
            request.form["kelas"], request.form["semester"], request.form["jumlah_mahasiswa"],
            request.form["durasi"], request.form["jenis_kegiatan"], request.form["kebutuhan_ruang"]
        ))
        db.commit()
        flash("Data mata kuliah berhasil ditambahkan.", "success")
    except IntegrityError:
        db.rollback()
        flash("Kode mata kuliah sudah ada atau data dosen tidak valid.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_data"))


@app.route("/admin/tambah_ruang", methods=["POST"])
@login_required("admin")
def tambah_ruang():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO ruang (kode_ruang, nama_ruang, kapasitas, jenis_ruang, lokasi, status) VALUES (?, ?, ?, ?, ?, 'aktif')",
            (request.form["kode_ruang"], request.form["nama_ruang"], request.form["kapasitas"], request.form["jenis_ruang"], request.form["lokasi"])
        )
        db.commit()
        flash("Data ruang berhasil ditambahkan.", "success")
    except IntegrityError:
        db.rollback()
        flash("Kode ruang sudah ada.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_data"))


@app.route("/admin/tambah_slot", methods=["POST"])
@login_required("admin")
def tambah_slot():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO slot_waktu (kode_slot, hari, jam_mulai, jam_selesai) VALUES (?, ?, ?, ?)",
            (request.form["kode_slot"], request.form["hari"], request.form["jam_mulai"], request.form["jam_selesai"])
        )
        db.commit()
        flash("Data slot waktu berhasil ditambahkan.", "success")
    except IntegrityError:
        db.rollback()
        flash("Kode slot sudah ada.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_data"))


@app.route("/admin/hapus/<jenis>/<kode>")
@login_required("admin")
def hapus_data(jenis, kode):
    daftar_tabel = {
        "dosen": ("dosen", "nip"),
        "mahasiswa": ("mahasiswa", "nim"),
        "matkul": ("mata_kuliah", "kode_matkul"),
        "ruang": ("ruang", "kode_ruang"),
        "slot": ("slot_waktu", "kode_slot")
    }

    if jenis not in daftar_tabel:
        flash("Jenis data tidak valid.", "danger")
        return redirect(url_for("admin_data"))

    tabel, kolom = daftar_tabel[jenis]
    db = get_db()
    try:
        db.execute(f"DELETE FROM {tabel} WHERE {kolom} = ?", (kode,))
        db.commit()
        flash("Data berhasil dihapus.", "success")
    except IntegrityError:
        db.rollback()
        flash("Data tidak dapat dihapus karena masih digunakan di jadwal.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_data"))


# ============================================================
# ALGORITMA REKOMENDASI / BRANCH AND BOUND INTERAKTIF
# ============================================================

def waktu_ke_menit(jam):
    jam = str(jam)
    bagian = jam.split(":")
    return int(bagian[0]) * 60 + int(bagian[1])


def waktu_overlap(slot_a, slot_b):
    if slot_a["hari"] != slot_b["hari"]:
        return False
    mulai_a = waktu_ke_menit(slot_a["jam_mulai"])
    selesai_a = waktu_ke_menit(slot_a["jam_selesai"])
    mulai_b = waktu_ke_menit(slot_b["jam_mulai"])
    selesai_b = waktu_ke_menit(slot_b["jam_selesai"])
    return mulai_a < selesai_b and mulai_b < selesai_a


def get_jadwal_aktif(db, exclude_jadwal_id=None):
    sql = """
        SELECT
            j.id,
            j.kode_matkul,
            j.nip,
            j.kode_ruang,
            j.kode_slot,
            j.status_jadwal,
            m.nama_matkul,
            m.kelas,
            r.nama_ruang,
            r.jenis_ruang,
            s.hari,
            s.jam_mulai,
            s.jam_selesai
        FROM jadwal j
        JOIN mata_kuliah m ON j.kode_matkul = m.kode_matkul
        LEFT JOIN ruang r ON j.kode_ruang = r.kode_ruang
        LEFT JOIN slot_waktu s ON j.kode_slot = s.kode_slot
        WHERE j.status_jadwal IN ('menunggu_persetujuan', 'final')
    """
    params = []
    if exclude_jadwal_id is not None:
        sql += " AND j.id != ?"
        params.append(exclude_jadwal_id)
    return db.execute(sql, tuple(params)).fetchall()


def cek_constraint_pilihan(matkul, ruang, slot, jadwal_aktif):
    """
    Mengecek pilihan jadwal dosen.

    Return:
    - valid: True jika tidak ada pelanggaran constraint.
    - alasan_list: daftar detail bentrok/pelanggaran yang akan ditampilkan ke dosen.
    """
    alasan = []

    jumlah_mahasiswa = int(matkul["jumlah_mahasiswa"])
    kapasitas_ruang = int(ruang["kapasitas"])

    if jumlah_mahasiswa > kapasitas_ruang:
        alasan.append(
            f"Kapasitas ruangan tidak mencukupi. Mata kuliah {matkul['nama_matkul']} berisi "
            f"{jumlah_mahasiswa} mahasiswa, sedangkan {ruang['nama_ruang']} hanya berkapasitas "
            f"{kapasitas_ruang} mahasiswa."
        )

    if matkul["kebutuhan_ruang"] == "laboratorium" and ruang["jenis_ruang"] != "laboratorium":
        alasan.append(
            f"Jenis ruangan tidak sesuai. Mata kuliah {matkul['nama_matkul']} membutuhkan laboratorium, "
            f"tetapi ruangan yang dipilih adalah {ruang['nama_ruang']} dengan jenis {ruang['jenis_ruang']}."
        )

    for j in jadwal_aktif:
        if not j.get("kode_slot"):
            continue

        slot_lama = {
            "hari": j["hari"],
            "jam_mulai": j["jam_mulai"],
            "jam_selesai": j["jam_selesai"],
        }

        if j["kode_ruang"] == ruang["kode_ruang"] and waktu_overlap(slot_lama, slot):
            alasan.append(
                f"Bentrok ruangan. {ruang['nama_ruang']} sudah digunakan untuk mata kuliah "
                f"{j['nama_matkul']} pada {j['hari']} pukul {j['jam_mulai']} - {j['jam_selesai']}."
            )

        if j["nip"] == matkul["nip"] and waktu_overlap(slot_lama, slot):
            alasan.append(
                f"Bentrok dosen. Dosen dengan NIP {matkul['nip']} sudah mengajar mata kuliah "
                f"{j['nama_matkul']} pada {j['hari']} pukul {j['jam_mulai']} - {j['jam_selesai']}."
            )

        if j["kelas"] == matkul["kelas"] and waktu_overlap(slot_lama, slot):
            alasan.append(
                f"Bentrok kelas mahasiswa. Kelas {matkul['kelas']} sudah memiliki jadwal mata kuliah "
                f"{j['nama_matkul']} pada {j['hari']} pukul {j['jam_mulai']} - {j['jam_selesai']}."
            )

    return len(alasan) == 0, alasan


def hitung_skor_rekomendasi(matkul, ruang, slot, ruang_awal=None, slot_awal=None):
    """
    Semakin kecil skor, semakin baik rekomendasi.
    """
    skor = 0

    # Kapasitas yang pas lebih baik daripada terlalu besar.
    sisa_kapasitas = int(ruang["kapasitas"]) - int(matkul["jumlah_mahasiswa"])
    skor += max(sisa_kapasitas, 0)

    # Teori sebaiknya tidak memakai lab jika masih ada ruang kelas biasa.
    if matkul["kebutuhan_ruang"] == "kelas" and ruang["jenis_ruang"] == "laboratorium":
        skor += 15

    # Praktikum lebih bagus di laboratorium.
    if matkul["jenis_kegiatan"] == "praktikum" and ruang["jenis_ruang"] == "laboratorium":
        skor -= 5

    # Penalti perubahan dari pilihan awal dosen.
    if ruang_awal and ruang["kode_ruang"] != ruang_awal["kode_ruang"]:
        skor += 5

    if slot_awal:
        if slot["hari"] != slot_awal["hari"]:
            skor += 20
        elif slot["kode_slot"] != slot_awal["kode_slot"]:
            skor += 10

    # Jam terlalu siang sedikit dipenalti.
    skor += waktu_ke_menit(slot["jam_mulai"]) // 180

    # Jumat diberi penalti kecil.
    if slot["hari"] == "Jumat":
        skor += 3

    return skor


def cari_rekomendasi_branch_and_bound(matkul, list_ruang, list_slot, jadwal_aktif, ruang_awal=None, slot_awal=None, limit=5):
    """
    Branch and Bound versi interaktif:
    1. Branch: coba semua kombinasi ruang dan slot waktu.
    2. Bound: buang kandidat yang melanggar constraint.
    3. Hitung skor.
    4. Ambil rekomendasi skor terkecil.
    """
    kandidat_valid = []
    best_score = float("inf")

    for ruang in list_ruang:
        for slot in list_slot:
            valid, alasan = cek_constraint_pilihan(matkul, ruang, slot, jadwal_aktif)
            if not valid:
                continue

            skor = hitung_skor_rekomendasi(matkul, ruang, slot, ruang_awal, slot_awal)

            # Bound sederhana: kandidat yang terlalu jauh dari solusi terbaik tidak diprioritaskan.
            if best_score != float("inf") and skor > best_score + 50:
                continue

            if skor < best_score:
                best_score = skor

            perubahan = []
            if ruang_awal and ruang["kode_ruang"] != ruang_awal["kode_ruang"]:
                perubahan.append(f"ruangan diganti dari {ruang_awal['nama_ruang']} ke {ruang['nama_ruang']}")
            elif ruang_awal:
                perubahan.append(f"tetap memakai ruangan {ruang['nama_ruang']}")

            if slot_awal:
                if slot["kode_slot"] != slot_awal["kode_slot"]:
                    perubahan.append(
                        f"waktu diganti dari {slot_awal['hari']} {slot_awal['jam_mulai']} - {slot_awal['jam_selesai']} "
                        f"ke {slot['hari']} {slot['jam_mulai']} - {slot['jam_selesai']}"
                    )
                else:
                    perubahan.append("tetap memakai waktu pilihan awal")

            if perubahan:
                detail_perubahan = "; ".join(perubahan)
            else:
                detail_perubahan = "alternatif memenuhi semua constraint"

            kandidat_valid.append({
                "kode_matkul": matkul["kode_matkul"],
                "nama_matkul": matkul["nama_matkul"],
                "kode_ruang": ruang["kode_ruang"],
                "nama_ruang": ruang["nama_ruang"],
                "kode_slot": slot["kode_slot"],
                "hari": slot["hari"],
                "jam_mulai": slot["jam_mulai"],
                "jam_selesai": slot["jam_selesai"],
                "skor": skor,
                "alasan": (
                    f"Alternatif valid karena tidak melanggar constraint. {detail_perubahan}. "
                    f"Skor {skor} dihitung dari kapasitas ruangan, jenis ruangan, perubahan ruangan, perubahan waktu, dan preferensi jam."
                )
            })

    kandidat_valid.sort(key=lambda x: x["skor"])
    return kandidat_valid[:limit]


# ============================================================
# DOSEN: MELIHAT, MEMILIH, MENYIMPAN, DAN MENERIMA REKOMENDASI
# ============================================================

@app.route("/dosen")
@login_required("dosen")
def dosen_dashboard():
    nip = session.get("ref_id")
    db = get_db()

    jadwal = db.execute("""
        SELECT
            j.id,
            j.status_jadwal,
            j.keterangan,
            j.skor,
            m.nama_matkul,
            m.kelas,
            r.nama_ruang,
            s.hari,
            s.jam_mulai,
            s.jam_selesai
        FROM jadwal j
        JOIN mata_kuliah m ON j.kode_matkul = m.kode_matkul
        LEFT JOIN ruang r ON j.kode_ruang = r.kode_ruang
        LEFT JOIN slot_waktu s ON j.kode_slot = s.kode_slot
        WHERE j.nip = ?
        ORDER BY FIELD(j.status_jadwal, 'bentrok', 'menunggu_persetujuan', 'final', 'ditolak'), s.hari, s.jam_mulai
    """, (nip,)).fetchall()

    db.close()

    content = """
    <div class="card">
        <h2>Dashboard Dosen</h2>
        <p>Alur terbaru: dosen memilih mata kuliah, ruangan, dan slot waktu. Jika bentrok, sistem menampilkan informasi bentrok dan rekomendasi berdasarkan Branch and Bound.</p>
        <a class="btn btn-success" href="/dosen/pilih_jadwal">Pilih Jadwal Mata Kuliah</a>
    </div>

    <div class="card">
        <h2>Jadwal Saya</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Mata Kuliah</th>
                <th>Kelas</th>
                <th>Ruang</th>
                <th>Waktu</th>
                <th>Status</th>
                <th>Skor</th>
                <th>Keterangan</th>
                <th>Aksi</th>
            </tr>
            {% for j in jadwal %}
            <tr>
                <td>{{ j.id }}</td>
                <td>{{ j.nama_matkul }}</td>
                <td>{{ j.kelas }}</td>
                <td>{{ j.nama_ruang or '-' }}</td>
                <td>
                    {% if j.hari %}
                        {{ j.hari }}, {{ j.jam_mulai }} - {{ j.jam_selesai }}
                    {% else %}
                        -
                    {% endif %}
                </td>
                <td><span class="badge">{{ j.status_jadwal }}</span></td>
                <td>{{ j.skor or '-' }}</td>
                <td>{{ j.keterangan }}</td>
                <td>
                    {% if j.status_jadwal == 'bentrok' %}
                        <a class="btn btn-warning" href="/dosen/rekomendasi/{{ j.id }}">Lihat Rekomendasi</a>
                    {% else %}
                        -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """

    return render_page("Dashboard Dosen", content, jadwal=jadwal)


@app.route("/dosen/pilih_jadwal")
@login_required("dosen")
def dosen_pilih_jadwal():
    nip = session.get("ref_id")
    db = get_db()

    matkul = db.execute("""
        SELECT m.*, d.nama_dosen
        FROM mata_kuliah m
        JOIN dosen d ON m.nip = d.nip
        WHERE m.nip = ?
        ORDER BY m.kode_matkul
    """, (nip,)).fetchall()

    ruang = db.execute("SELECT * FROM ruang WHERE status = 'aktif' ORDER BY kode_ruang").fetchall()
    slot = db.execute("SELECT * FROM slot_waktu ORDER BY kode_slot").fetchall()

    jadwal_saya = db.execute("""
        SELECT j.*, m.nama_matkul, r.nama_ruang, s.hari, s.jam_mulai, s.jam_selesai
        FROM jadwal j
        JOIN mata_kuliah m ON j.kode_matkul = m.kode_matkul
        LEFT JOIN ruang r ON j.kode_ruang = r.kode_ruang
        LEFT JOIN slot_waktu s ON j.kode_slot = s.kode_slot
        WHERE j.nip = ?
        ORDER BY j.id DESC
    """, (nip,)).fetchall()

    db.close()

    content = """
    <div class="card">
        <h2>Pilih Jadwal Mata Kuliah</h2>
        <p>Dosen memilih mata kuliah, ruangan, dan slot waktu. Saat tombol <b>Simpan</b> ditekan, sistem akan mengecek bentrok.</p>

        <form method="POST" action="/dosen/simpan_jadwal">
            <p><b>Mata Kuliah</b></p>
            <select name="kode_matkul" required>
                {% for m in matkul %}
                    <option value="{{ m.kode_matkul }}">
                        {{ m.kode_matkul }} - {{ m.nama_matkul }} | Kelas {{ m.kelas }} | {{ m.jumlah_mahasiswa }} mahasiswa | {{ m.kebutuhan_ruang }}
                    </option>
                {% endfor %}
            </select>

            <p><b>Ruangan</b></p>
            <select name="kode_ruang" required>
                {% for r in ruang %}
                    <option value="{{ r.kode_ruang }}">
                        {{ r.kode_ruang }} - {{ r.nama_ruang }} | {{ r.jenis_ruang }} | kapasitas {{ r.kapasitas }}
                    </option>
                {% endfor %}
            </select>

            <p><b>Slot Waktu</b></p>
            <select name="kode_slot" required>
                {% for s in slot %}
                    <option value="{{ s.kode_slot }}">
                        {{ s.kode_slot }} - {{ s.hari }}, {{ s.jam_mulai }} - {{ s.jam_selesai }}
                    </option>
                {% endfor %}
            </select>

            <br><br>
            <button type="submit">Simpan Jadwal</button>
            <a class="btn btn-secondary" href="/dosen">Kembali</a>
        </form>
    </div>

    <div class="card">
        <h2>Riwayat Jadwal Saya</h2>
        <table>
            <tr><th>ID</th><th>Mata Kuliah</th><th>Ruang</th><th>Waktu</th><th>Status</th><th>Keterangan</th></tr>
            {% for j in jadwal_saya %}
            <tr>
                <td>{{ j.id }}</td>
                <td>{{ j.nama_matkul }}</td>
                <td>{{ j.nama_ruang or '-' }}</td>
                <td>
                    {% if j.hari %}
                        {{ j.hari }}, {{ j.jam_mulai }} - {{ j.jam_selesai }}
                    {% else %}
                        -
                    {% endif %}
                </td>
                <td><span class="badge">{{ j.status_jadwal }}</span></td>
                <td>{{ j.keterangan }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """

    return render_page("Pilih Jadwal Dosen", content, matkul=matkul, ruang=ruang, slot=slot, jadwal_saya=jadwal_saya)


@app.route("/dosen/simpan_jadwal", methods=["POST"])
@login_required("dosen")
def dosen_simpan_jadwal():
    nip = session.get("ref_id")
    kode_matkul = request.form["kode_matkul"]
    kode_ruang = request.form["kode_ruang"]
    kode_slot = request.form["kode_slot"]

    db = get_db()

    matkul = db.execute("SELECT * FROM mata_kuliah WHERE kode_matkul = ? AND nip = ?", (kode_matkul, nip)).fetchone()
    ruang = db.execute("SELECT * FROM ruang WHERE kode_ruang = ?", (kode_ruang,)).fetchone()
    slot = db.execute("SELECT * FROM slot_waktu WHERE kode_slot = ?", (kode_slot,)).fetchone()

    if matkul is None or ruang is None or slot is None:
        db.close()
        flash("Data mata kuliah, ruang, atau slot tidak ditemukan.", "danger")
        return redirect(url_for("dosen_pilih_jadwal"))

    # Jika mata kuliah sudah final, jangan boleh diajukan ulang.
    sudah_final = db.execute("""
        SELECT * FROM jadwal
        WHERE kode_matkul = ? AND status_jadwal = 'final'
    """, (kode_matkul,)).fetchone()

    if sudah_final:
        db.close()
        flash("Mata kuliah ini sudah memiliki jadwal final. Hubungi Admin jika ingin mengubahnya.", "warning")
        return redirect(url_for("dosen_dashboard"))

    # Hapus pengajuan lama yang belum final untuk mata kuliah yang sama agar tidak menumpuk.
    jadwal_lama = db.execute("""
        SELECT id FROM jadwal
        WHERE kode_matkul = ? AND status_jadwal IN ('bentrok', 'menunggu_persetujuan', 'ditolak')
    """, (kode_matkul,)).fetchall()

    for j in jadwal_lama:
        db.execute("DELETE FROM rekomendasi WHERE jadwal_id = ?", (j["id"],))
        db.execute("DELETE FROM jadwal WHERE id = ?", (j["id"],))

    jadwal_aktif = get_jadwal_aktif(db)

    slot_dipilih = {
        "kode_slot": slot["kode_slot"],
        "hari": slot["hari"],
        "jam_mulai": slot["jam_mulai"],
        "jam_selesai": slot["jam_selesai"],
    }

    valid, alasan_bentrok = cek_constraint_pilihan(matkul, ruang, slot_dipilih, jadwal_aktif)

    if valid:
        skor = hitung_skor_rekomendasi(matkul, ruang, slot_dipilih, ruang, slot_dipilih)
        db.execute("""
            INSERT INTO jadwal
            (kode_matkul, nip, kode_ruang, kode_slot, status_jadwal, keterangan, skor)
            VALUES (?, ?, ?, ?, 'menunggu_persetujuan', ?, ?)
        """, (
            kode_matkul,
            nip,
            kode_ruang,
            kode_slot,
            "Jadwal berhasil dipilih dosen dan menunggu persetujuan admin.",
            skor
        ))
        db.commit()
        db.close()
        flash("Jadwal tidak bentrok. Jadwal berhasil diajukan dan menunggu persetujuan Admin.", "success")
        return redirect(url_for("dosen_dashboard"))

    # Jika bentrok, simpan jadwal sebagai status bentrok dan buat rekomendasi.
    # Dipisah dengan || agar nanti bisa ditampilkan sebagai daftar poin di halaman rekomendasi.
    keterangan = "||".join(alasan_bentrok)
    cursor = db.execute("""
        INSERT INTO jadwal
        (kode_matkul, nip, kode_ruang, kode_slot, status_jadwal, keterangan, skor)
        VALUES (?, ?, ?, ?, 'bentrok', ?, NULL)
    """, (kode_matkul, nip, kode_ruang, kode_slot, keterangan))
    jadwal_id = cursor.lastrowid

    list_ruang = db.execute("SELECT * FROM ruang WHERE status = 'aktif' ORDER BY kode_ruang").fetchall()
    list_slot = db.execute("SELECT * FROM slot_waktu ORDER BY kode_slot").fetchall()
    rekomendasi = cari_rekomendasi_branch_and_bound(matkul, list_ruang, list_slot, jadwal_aktif, ruang, slot_dipilih, limit=5)

    for rec in rekomendasi:
        db.execute("""
            INSERT INTO rekomendasi
            (jadwal_id, kode_matkul, kode_ruang, kode_slot, alasan, skor, status)
            VALUES (?, ?, ?, ?, ?, ?, 'tersedia')
        """, (
            jadwal_id,
            kode_matkul,
            rec["kode_ruang"],
            rec["kode_slot"],
            rec["alasan"],
            rec["skor"]
        ))

    db.commit()
    db.close()

    flash("Jadwal bentrok. Detail bentrok dan rekomendasi alternatif ditampilkan di bawah.", "danger")
    return redirect(url_for("dosen_rekomendasi", jadwal_id=jadwal_id))


@app.route("/dosen/rekomendasi/<int:jadwal_id>")
@login_required("dosen")
def dosen_rekomendasi(jadwal_id):
    nip = session.get("ref_id")
    db = get_db()

    jadwal = db.execute("""
        SELECT
            j.*,
            m.nama_matkul,
            m.kelas,
            r.nama_ruang,
            s.hari,
            s.jam_mulai,
            s.jam_selesai
        FROM jadwal j
        JOIN mata_kuliah m ON j.kode_matkul = m.kode_matkul
        LEFT JOIN ruang r ON j.kode_ruang = r.kode_ruang
        LEFT JOIN slot_waktu s ON j.kode_slot = s.kode_slot
        WHERE j.id = ? AND j.nip = ?
    """, (jadwal_id, nip)).fetchone()

    if jadwal is None:
        db.close()
        flash("Jadwal tidak ditemukan atau bukan milik dosen ini.", "danger")
        return redirect(url_for("dosen_dashboard"))

    rekomendasi = db.execute("""
        SELECT
            rec.*,
            r.nama_ruang,
            r.jenis_ruang,
            r.kapasitas,
            s.hari,
            s.jam_mulai,
            s.jam_selesai
        FROM rekomendasi rec
        JOIN ruang r ON rec.kode_ruang = r.kode_ruang
        JOIN slot_waktu s ON rec.kode_slot = s.kode_slot
        WHERE rec.jadwal_id = ?
        ORDER BY rec.skor ASC
    """, (jadwal_id,)).fetchall()

    # Pecah keterangan bentrok menjadi daftar agar tampil rapi dan jelas.
    raw_keterangan = jadwal.get("keterangan") or ""
    if "||" in raw_keterangan:
        bentrok_list = [item.strip() for item in raw_keterangan.split("||") if item.strip()]
    else:
        bentrok_list = [item.strip() for item in raw_keterangan.split(" | ") if item.strip()]

    db.close()

    content = """
    <div class="card">
        <h2>Informasi Bentrok</h2>
        <p class="small">Pilihan jadwal tidak langsung disimpan karena sistem menemukan pelanggaran constraint berikut.</p>

        <table>
            <tr>
                <th>Mata Kuliah</th>
                <td>{{ jadwal.nama_matkul }}</td>
            </tr>
            <tr>
                <th>Kelas</th>
                <td>{{ jadwal.kelas }}</td>
            </tr>
            <tr>
                <th>Ruangan yang Dipilih</th>
                <td>{{ jadwal.nama_ruang or '-' }}</td>
            </tr>
            <tr>
                <th>Slot Waktu yang Dipilih</th>
                <td>{{ jadwal.hari or '-' }} {{ jadwal.jam_mulai or '' }} - {{ jadwal.jam_selesai or '' }}</td>
            </tr>
            <tr>
                <th>Status</th>
                <td><span class="badge">{{ jadwal.status_jadwal }}</span></td>
            </tr>
        </table>

        <h3>Detail Bentrok</h3>
        <div class="danger">
            <ol>
                {% for item in bentrok_list %}
                    <li>{{ item }}</li>
                {% endfor %}
            </ol>
        </div>
    </div>

    <div class="card">
        <h2>Rekomendasi Alternatif Berdasarkan Branch and Bound</h2>
        <p class="small">
            Rekomendasi di bawah ini sudah melewati pengecekan kapasitas ruangan, kebutuhan jenis ruang, bentrok ruangan,
            bentrok dosen, dan bentrok kelas mahasiswa. Semakin kecil skor, semakin baik rekomendasi.
        </p>

        {% if rekomendasi|length > 0 %}
        <table>
            <tr>
                <th>Peringkat</th>
                <th>Ruang Alternatif</th>
                <th>Jenis</th>
                <th>Kapasitas</th>
                <th>Waktu Alternatif</th>
                <th>Alasan Rekomendasi</th>
                <th>Skor</th>
                <th>Status</th>
                <th>Aksi</th>
            </tr>
            {% for r in rekomendasi %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ r.nama_ruang }}</td>
                <td>{{ r.jenis_ruang }}</td>
                <td>{{ r.kapasitas }}</td>
                <td>{{ r.hari }}, {{ r.jam_mulai }} - {{ r.jam_selesai }}</td>
                <td>{{ r.alasan }}</td>
                <td><b>{{ r.skor }}</b></td>
                <td><span class="badge">{{ r.status }}</span></td>
                <td>
                    {% if r.status == 'tersedia' %}
                        <a class="btn btn-warning" href="/dosen/pilih_rekomendasi/{{ r.id }}">Pilih Rekomendasi</a>
                    {% else %}
                        -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
            <p class="danger">Tidak ada rekomendasi valid. Admin perlu menambah ruang atau slot waktu baru.</p>
        {% endif %}

        <br>
        <a class="btn btn-secondary" href="/dosen/pilih_jadwal">Pilih Jadwal Lain</a>
        <a class="btn" href="/dosen">Kembali ke Dashboard</a>
    </div>
    """

    return render_page(
        "Informasi Bentrok dan Rekomendasi",
        content,
        jadwal=jadwal,
        rekomendasi=rekomendasi,
        bentrok_list=bentrok_list
    )


@app.route("/dosen/pilih_rekomendasi/<int:rekomendasi_id>")
@login_required("dosen")
def dosen_pilih_rekomendasi(rekomendasi_id):
    nip = session.get("ref_id")
    db = get_db()

    rec = db.execute("""
        SELECT rec.*, j.nip
        FROM rekomendasi rec
        JOIN jadwal j ON rec.jadwal_id = j.id
        WHERE rec.id = ? AND j.nip = ?
    """, (rekomendasi_id, nip)).fetchone()

    if rec is None:
        db.close()
        flash("Rekomendasi tidak ditemukan atau bukan milik dosen ini.", "danger")
        return redirect(url_for("dosen_dashboard"))

    db.execute("""
        UPDATE jadwal
        SET kode_ruang = ?,
            kode_slot = ?,
            status_jadwal = 'menunggu_persetujuan',
            keterangan = 'Dosen memilih rekomendasi alternatif. Menunggu persetujuan Admin.',
            skor = ?
        WHERE id = ?
    """, (rec["kode_ruang"], rec["kode_slot"], rec["skor"], rec["jadwal_id"]))

    db.execute("UPDATE rekomendasi SET status = 'tidak_dipilih' WHERE jadwal_id = ?", (rec["jadwal_id"],))
    db.execute("UPDATE rekomendasi SET status = 'diajukan' WHERE id = ?", (rekomendasi_id,))

    db.commit()
    db.close()

    flash("Rekomendasi dipilih dan diajukan ke Admin.", "success")
    return redirect(url_for("dosen_dashboard"))


# ============================================================
# ADMIN: MELIHAT DAN MENYETUJUI JADWAL DOSEN
# ============================================================

@app.route("/admin/jadwal")
@login_required("admin")
def admin_jadwal():
    db = get_db()

    jadwal = db.execute("""
        SELECT
            j.id,
            j.status_jadwal,
            j.keterangan,
            j.skor,
            m.kode_matkul,
            m.nama_matkul,
            m.kelas,
            m.jumlah_mahasiswa,
            d.nama_dosen,
            r.nama_ruang,
            r.jenis_ruang,
            s.hari,
            s.jam_mulai,
            s.jam_selesai
        FROM jadwal j
        JOIN mata_kuliah m ON j.kode_matkul = m.kode_matkul
        JOIN dosen d ON j.nip = d.nip
        LEFT JOIN ruang r ON j.kode_ruang = r.kode_ruang
        LEFT JOIN slot_waktu s ON j.kode_slot = s.kode_slot
        ORDER BY FIELD(j.status_jadwal, 'menunggu_persetujuan', 'bentrok', 'final', 'ditolak'), s.hari, s.jam_mulai
    """).fetchall()

    rekomendasi = db.execute("""
        SELECT
            rec.id,
            rec.jadwal_id,
            rec.alasan,
            rec.skor,
            rec.status,
            m.nama_matkul,
            d.nama_dosen,
            r.nama_ruang,
            s.hari,
            s.jam_mulai,
            s.jam_selesai
        FROM rekomendasi rec
        JOIN jadwal j ON rec.jadwal_id = j.id
        JOIN mata_kuliah m ON rec.kode_matkul = m.kode_matkul
        JOIN dosen d ON j.nip = d.nip
        JOIN ruang r ON rec.kode_ruang = r.kode_ruang
        JOIN slot_waktu s ON rec.kode_slot = s.kode_slot
        ORDER BY FIELD(rec.status, 'diajukan', 'tersedia', 'dipilih', 'tidak_dipilih'), rec.skor ASC
    """).fetchall()

    db.close()

    content = """
    <div class="card">
        <h2>Persetujuan Jadwal dari Dosen</h2>
        <p>Admin menyetujui jadwal yang sudah dipilih dosen atau dipilih dari rekomendasi sistem.</p>
        <table>
            <tr>
                <th>ID</th>
                <th>Mata Kuliah</th>
                <th>Kelas</th>
                <th>Dosen</th>
                <th>Jumlah Mhs</th>
                <th>Ruang</th>
                <th>Jenis Ruang</th>
                <th>Waktu</th>
                <th>Status</th>
                <th>Skor</th>
                <th>Keterangan</th>
                <th>Aksi Admin</th>
            </tr>
            {% for j in jadwal %}
            <tr>
                <td>{{ j.id }}</td>
                <td>{{ j.nama_matkul }}</td>
                <td>{{ j.kelas }}</td>
                <td>{{ j.nama_dosen }}</td>
                <td>{{ j.jumlah_mahasiswa }}</td>
                <td>{{ j.nama_ruang or '-' }}</td>
                <td>{{ j.jenis_ruang or '-' }}</td>
                <td>
                    {% if j.hari %}
                        {{ j.hari }}, {{ j.jam_mulai }} - {{ j.jam_selesai }}
                    {% else %}
                        -
                    {% endif %}
                </td>
                <td><span class="badge">{{ j.status_jadwal }}</span></td>
                <td>{{ j.skor or '-' }}</td>
                <td>{{ j.keterangan }}</td>
                <td>
                    {% if j.status_jadwal == 'menunggu_persetujuan' %}
                        <a class="btn btn-success" href="/admin/approve_jadwal/{{ j.id }}">Setujui</a>
                        <a class="btn btn-danger" href="/admin/tolak_jadwal/{{ j.id }}">Tolak</a>
                    {% elif j.status_jadwal == 'bentrok' %}
                        <span class="badge">Menunggu dosen memilih rekomendasi</span>
                    {% else %}
                        -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h2>Riwayat Rekomendasi</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Jadwal ID</th>
                <th>Mata Kuliah</th>
                <th>Dosen</th>
                <th>Ruang Alternatif</th>
                <th>Waktu Alternatif</th>
                <th>Alasan</th>
                <th>Skor</th>
                <th>Status</th>
            </tr>
            {% for r in rekomendasi %}
            <tr>
                <td>{{ r.id }}</td>
                <td>{{ r.jadwal_id }}</td>
                <td>{{ r.nama_matkul }}</td>
                <td>{{ r.nama_dosen }}</td>
                <td>{{ r.nama_ruang }}</td>
                <td>{{ r.hari }}, {{ r.jam_mulai }} - {{ r.jam_selesai }}</td>
                <td>{{ r.alasan }}</td>
                <td>{{ r.skor }}</td>
                <td><span class="badge">{{ r.status }}</span></td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """

    return render_page("Persetujuan Jadwal", content, jadwal=jadwal, rekomendasi=rekomendasi)


@app.route("/admin/approve_jadwal/<int:jadwal_id>")
@login_required("admin")
def approve_jadwal(jadwal_id):
    db = get_db()
    jadwal = db.execute("SELECT * FROM jadwal WHERE id = ?", (jadwal_id,)).fetchone()

    if jadwal is None:
        db.close()
        flash("Jadwal tidak ditemukan.", "danger")
        return redirect(url_for("admin_jadwal"))

    db.execute("""
        UPDATE jadwal
        SET status_jadwal = 'final',
            keterangan = 'Jadwal sudah disetujui Admin dan menjadi jadwal final.'
        WHERE id = ?
    """, (jadwal_id,))

    db.execute("UPDATE rekomendasi SET status = 'dipilih' WHERE jadwal_id = ? AND status = 'diajukan'", (jadwal_id,))
    db.commit()
    db.close()

    flash("Jadwal berhasil disetujui dan menjadi final.", "success")
    return redirect(url_for("admin_jadwal"))


@app.route("/admin/tolak_jadwal/<int:jadwal_id>")
@login_required("admin")
def tolak_jadwal(jadwal_id):
    db = get_db()
    db.execute("""
        UPDATE jadwal
        SET status_jadwal = 'ditolak',
            keterangan = 'Jadwal ditolak Admin. Dosen perlu memilih jadwal ulang.'
        WHERE id = ? AND status_jadwal = 'menunggu_persetujuan'
    """, (jadwal_id,))
    db.execute("UPDATE rekomendasi SET status = 'ditolak' WHERE jadwal_id = ? AND status = 'diajukan'", (jadwal_id,))
    db.commit()
    db.close()

    flash("Jadwal ditolak. Dosen perlu memilih jadwal ulang.", "warning")
    return redirect(url_for("admin_jadwal"))


# ============================================================
# MAHASISWA: MELIHAT JADWAL FINAL
# ============================================================

@app.route("/mahasiswa")
@login_required("mahasiswa")
def mahasiswa_dashboard():
    kelas = session.get("ref_id")
    db = get_db()

    jadwal = db.execute("""
        SELECT
            m.nama_matkul,
            m.kelas,
            m.semester,
            d.nama_dosen,
            r.nama_ruang,
            r.lokasi,
            s.hari,
            s.jam_mulai,
            s.jam_selesai,
            j.status_jadwal,
            j.keterangan
        FROM jadwal j
        JOIN mata_kuliah m ON j.kode_matkul = m.kode_matkul
        JOIN dosen d ON j.nip = d.nip
        LEFT JOIN ruang r ON j.kode_ruang = r.kode_ruang
        LEFT JOIN slot_waktu s ON j.kode_slot = s.kode_slot
        WHERE m.kelas = ? AND j.status_jadwal = 'final'
        ORDER BY s.hari, s.jam_mulai
    """, (kelas,)).fetchall()

    db.close()

    content = """
    <div class="card">
        <h2>Jadwal Kuliah Final</h2>
        <p>Kelas: <b>{{ kelas }}</b></p>
        <p class="small">Mahasiswa hanya melihat jadwal yang sudah disetujui Admin dengan status final.</p>

        <table>
            <tr>
                <th>Mata Kuliah</th>
                <th>Semester</th>
                <th>Dosen</th>
                <th>Ruang</th>
                <th>Lokasi</th>
                <th>Waktu</th>
                <th>Status</th>
                <th>Keterangan</th>
            </tr>
            {% for j in jadwal %}
            <tr>
                <td>{{ j.nama_matkul }}</td>
                <td>{{ j.semester }}</td>
                <td>{{ j.nama_dosen }}</td>
                <td>{{ j.nama_ruang or '-' }}</td>
                <td>{{ j.lokasi or '-' }}</td>
                <td>
                    {% if j.hari %}
                        {{ j.hari }}, {{ j.jam_mulai }} - {{ j.jam_selesai }}
                    {% else %}
                        -
                    {% endif %}
                </td>
                <td><span class="badge">{{ j.status_jadwal }}</span></td>
                <td>{{ j.keterangan }}</td>
            </tr>
            {% endfor %}
        </table>

        {% if jadwal|length == 0 %}
            <p class="warning">Belum ada jadwal final untuk kelas ini.</p>
        {% endif %}
    </div>
    """

    return render_page("Dashboard Mahasiswa", content, jadwal=jadwal, kelas=kelas)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
