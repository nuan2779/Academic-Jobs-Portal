# backup.py — chạy độc lập, schedule bằng cron hoặc Task Scheduler
import subprocess, os, datetime

DB_NAME = "academic_jobs_portal"
DB_USER = "root"
DB_PASS = "Luan270706"
BACKUP_DIR = r"C:\Users\Admin\Downloads\AcademicGateDAta\backups"

def run_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{BACKUP_DIR}/backup_{timestamp}.sql"

    MYSQLDUMP_PATH = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

    cmd = [
        MYSQLDUMP_PATH,
        f"-u{DB_USER}",
        f"-p{DB_PASS}",
        "--single-transaction",   # không lock bảng khi backup
        "--routines",             # backup stored procedures
        "--triggers",
        DB_NAME
    ]
    with open(filename, "w") as f:
        subprocess.run(cmd, stdout=f, check=True)

    print(f"✅ Backup thành công: {filename}")

    # Xóa backup cũ hơn 7 ngày
    for file in os.listdir(BACKUP_DIR):
        fpath = os.path.join(BACKUP_DIR, file)
        age   = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
        if age.days > 7:
            os.remove(fpath)
            print(f"🗑️ Đã xóa backup cũ: {file}")

if __name__ == "__main__":
    run_backup()