"""
================================================================================
  DATA CLEANING — AcademicGate Dataset
  Mục tiêu: Làm sạch 8 bảng CSV, xuất ra file sạch sẵn sàng tải lên SQL
================================================================================
  Thay DATA_DIR thành thư mục chứa CSV của bạn
  Output: thư mục cleaned_for_sql/
================================================================================
"""

import re
import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR  = Path(r"C:\Users\Admin\Downloads\AcademicGateDAta\AcademicGateDAta")               # <-- SỬA ĐƯỜNG DẪN
OUT_DIR   = Path("cleaned_for_sql")
OUT_DIR.mkdir(exist_ok=True)

# ── Helper ─────────────────────────────────────────────────────────────────────
def load(pattern):
    files = list(DATA_DIR.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy: {pattern}")
    df = pd.read_csv(files[0], low_memory=False)
    print(f"  ✓ Loaded  {files[0].name:55s} → {df.shape[0]:>6,} rows × {df.shape[1]} cols")
    return df

def save(df, name):
    path = OUT_DIR / f"{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  ✓ Saved   {name:50s} → {df.shape[0]:>6,} rows × {df.shape[1]} cols")
    return df

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def report_drop(col, reason):
    print(f"    DROP  [{col}]  — {reason}")

def report_clean(col, detail):
    print(f"    CLEAN [{col}]  — {detail}")


# ══════════════════════════════════════════════════════════════════════════════
# LOAD TẤT CẢ BẢNG
# ══════════════════════════════════════════════════════════════════════════════
section("LOAD DATA")

pos       = load("tbl_positions.csv")
ra_link   = load("tbl_positions_researchareas_202604131031.csv")
pt_link   = load("tbl_job_positiontype_202604131031.csv")
pos_type  = load("tbl_positiontype_202604131031.csv")
res_area  = load("tbl_researcharea_202604131031.csv")
uni       = load("tbl_university_202604131031.csv")
country   = load("tbl_country_202604131031.csv")
continent = load("tbl_continents_202604131031.csv")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 1 — tbl_positions  (bảng chính, phức tạp nhất)
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 1 — tbl_positions")
df = pos.copy()
print(f"  Trước khi clean: {df.shape[0]:,} rows × {df.shape[1]} cols")

# ── 1.1 DROP cột 100% trống ───────────────────────────────────────────────────
DROP_100PCT = ["Language", "DateOfPublish"]
for c in DROP_100PCT:
    if c in df.columns:
        report_drop(c, "100% missing")
df.drop(columns=[c for c in DROP_100PCT if c in df.columns], inplace=True)

# ── 1.2 DROP cột thừa/redundant ──────────────────────────────────────────────
# Các cột list dạng string — đã có bảng linking riêng đầy đủ hơn
DROP_REDUNDANT = [
    "ID_ResearchAreaList", "ResearchAreaList",
    "Res_ID_ResearchAreaList", "Res_ResearchAreaList",
    "ID_PositionList", "ID_Position_List", "PositionList",
    "Res_ID_PositionList", "Res_PositionList",
]
for c in DROP_REDUNDANT:
    if c in df.columns:
        report_drop(c, "Redundant — đã có bảng linking riêng")
df.drop(columns=[c for c in DROP_REDUNDANT if c in df.columns], inplace=True)

# ── 1.3 DROP cột derived (tính lại được từ DateofPost) ───────────────────────
DROP_DERIVED = ["YearPost", "MonthPost", "YearMonth"]
for c in DROP_DERIVED:
    if c in df.columns:
        report_drop(c, "Derived column — tính lại được từ DateofPost")
df.drop(columns=[c for c in DROP_DERIVED if c in df.columns], inplace=True)

# ── 1.4 DROP cột HTML (quá nặng, không phù hợp SQL thông thường) ─────────────
DROP_HTML = ["HTMLAdvertisement"]
for c in DROP_HTML:
    if c in df.columns:
        report_drop(c, "HTML/text nặng — lưu riêng nếu cần full-text search")
df.drop(columns=[c for c in DROP_HTML if c in df.columns], inplace=True)

# ── 1.5 PARSE & CHUẨN HÓA DATE ───────────────────────────────────────────────
for col in ["DateofPost", "Deadline"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
        report_clean(col, f"Parse → YYYY-MM-DD (nulls: {df[col].isna().sum()})")

# ── 1.6 FILL missing nhỏ ──────────────────────────────────────────────────────
if "Abstract" in df.columns:
    df["Abstract"] = df["Abstract"].fillna("").str.strip()
    report_clean("Abstract", "fillna('') — 0.29% missing")

if "NonHTMLAdvertisement" in df.columns:
    df["NonHTMLAdvertisement"] = df["NonHTMLAdvertisement"].fillna("").str.strip()
    report_clean("NonHTMLAdvertisement", "Giữ lại làm nội dung chính cho Embedding")
    
if "Salary" in df.columns:
    df["Salary"] = df["Salary"].fillna("Not specified").str.strip()
    report_clean("Salary", "fillna('Not specified') — 0.26% missing")

# ── 1.7 CLEAN WorkingTime ──────────────────────────────────────────────────────
if "WorkingTime" in df.columns:
    wt_map = {
        "full time": "Full Time", "full-time": "Full Time", "fulltime": "Full Time",
        "part time": "Part Time", "part-time": "Part Time", "parttime": "Part Time",
        "negotiation": "Negotiation", "negotiable": "Negotiation",
        "to be discussed": "Negotiation",
    }
    df["WorkingTime"] = (df["WorkingTime"]
        .fillna("Not specified")
        .str.strip()
        .str.lower()
        .map(lambda x: wt_map.get(x, x.title()))
    )
    report_clean("WorkingTime", f"Chuẩn hóa chữ hoa/thường, map synonyms → {df['WorkingTime'].nunique()} unique values")

# ── 1.8 CLEAN ContractType ────────────────────────────────────────────────────
if "ContractType" in df.columns:
    def clean_contract(s):
        if pd.isna(s) or str(s).strip() == "":
            return "Not specified"
        s = str(s).strip().lower()
        if re.search(r"fixed.?term|fix.?term|definite|determinado", s):
            return "Fixed-term"
        if re.search(r"permanent|indeterminate|indefinite|open.?ended|tenure", s):
            return "Permanent"
        if re.search(r"temporary|temp\b", s):
            return "Temporary"
        if re.search(r"casual|sessional|hourly", s):
            return "Casual"
        if re.search(r"volunteer|voluntary", s):
            return "Voluntary"
        return "Other"

    df["ContractType_Clean"] = df["ContractType"].apply(clean_contract)
    df.drop(columns=["ContractType"], inplace=True)
    df.rename(columns={"ContractType_Clean": "ContractType"}, inplace=True)
    report_clean("ContractType", f"Chuẩn hóa → {df['ContractType'].value_counts().to_dict()}")

# ── 1.9 CLEAN JobTitle — trim whitespace ─────────────────────────────────────
if "JobTitle" in df.columns:
    df["JobTitle"] = df["JobTitle"].fillna("").str.strip()
    report_clean("JobTitle", "strip whitespace")

# ── 1.10 CLEAN IsAlive / JobStatus — đảm bảo numeric ─────────────────────────
for col in ["IsAlive", "JobStatus", "FavoriteCount", "SiteId"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# ── 1.11 TRIM tất cả cột string ──────────────────────────────────────────────
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip() if c.dtype == "object" else c)

print(f"\n  Sau khi clean:  {df.shape[0]:,} rows × {df.shape[1]} cols")
print(f"  Các cột còn lại: {list(df.columns)}")
save(df, "tbl_positions_clean")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 2 — tbl_university
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 2 — tbl_university")
df = uni.copy()

# Drop longitude/latitude (100% trống)
for c in ["longitude", "latitude", "Longitude", "Latitude"]:
    if c in df.columns and df[c].isna().mean() > 0.9:
        report_drop(c, f"{df[c].isna().mean()*100:.0f}% missing")
        df.drop(columns=[c], inplace=True)

# Trim strings
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

# Fill missing text fields
for col in df.select_dtypes(include="object").columns:
    miss = df[col].isna().sum()
    if miss > 0:
        df[col] = df[col].fillna("")
        report_clean(col, f"fillna('') — {miss} nulls")

print(f"\n  Sau khi clean: {df.shape}")
save(df, "tbl_university_clean")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 3 — tbl_country
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 3 — tbl_country")
df = country.copy()

# Trim & fill
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
df.fillna("", inplace=True)

# Drop duplicate rows nếu có
before = len(df)
df.drop_duplicates(inplace=True)
if len(df) < before:
    print(f"    DROP {before - len(df)} duplicate rows")

print(f"\n  Sau khi clean: {df.shape}")
save(df, "tbl_country_clean")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 4 — tbl_continents
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 4 — tbl_continents")
df = continent.copy()
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
df.fillna("", inplace=True)
print(f"\n  Sau khi clean: {df.shape}")
save(df, "tbl_continents_clean")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 5 — tbl_positiontype
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 5 — tbl_positiontype")
df = pos_type.copy()
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
df.fillna("", inplace=True)
print(f"\n  Sau khi clean: {df.shape}")
save(df, "tbl_positiontype_clean")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 6 — tbl_researcharea
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 6 — tbl_researcharea")
df = res_area.copy()
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
df.fillna("", inplace=True)
print(f"\n  Sau khi clean: {df.shape}")
save(df, "tbl_researcharea_clean")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 7 — tbl_job_positiontype  (bridge table)
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 7 — tbl_job_positiontype")
df = pt_link.copy()
# Đảm bảo Weight là numeric 0–1
if "Weight" in df.columns:
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["Weight"] = df["Weight"].clip(0, 1)
    report_clean("Weight", f"clip(0,1) — nulls: {df['Weight'].isna().sum()}")

# Xóa dòng không có ID hoặc ID_Position
before = len(df)
df.dropna(subset=["ID", "ID_PositionType"], inplace=True)
if len(df) < before:
    print(f"    DROP {before - len(df)} rows — null FK (ID hoặc ID_Position)")

# Drop duplicates
before = len(df)
df.drop_duplicates(inplace=True)
if len(df) < before:
    print(f"    DROP {before - len(df)} duplicate rows")

# Trim strings
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

print(f"\n  Sau khi clean: {df.shape}")
save(df, "tbl_job_positiontype_clean")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG 8 — tbl_positions_researchareas  (bridge table)
# ══════════════════════════════════════════════════════════════════════════════
section("BẢNG 8 — tbl_positions_researchareas")
df = ra_link.copy()

# Đảm bảo Weight là numeric 0–1
if "Weight" in df.columns:
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df["Weight"] = df["Weight"].clip(0, 1)
    report_clean("Weight", f"clip(0,1) — nulls: {df['Weight'].isna().sum()}")

# Xóa dòng null FK
before = len(df)
df.dropna(subset=["ID", "ID_ResearchArea"], inplace=True)
if len(df) < before:
    print(f"    DROP {before - len(df)} rows — null FK")

# Drop duplicates
before = len(df)
df.drop_duplicates(inplace=True)
if len(df) < before:
    print(f"    DROP {before - len(df)} duplicate rows")

# Trim strings
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

print(f"\n  Sau khi clean: {df.shape}")
save(df, "tbl_positions_researchareas_clean")


# ══════════════════════════════════════════════════════════════════════════════
# TỔNG KẾT
# ══════════════════════════════════════════════════════════════════════════════
section("TỔNG KẾT")
print(f"""
  ✅ Đã xuất 8 file sạch vào thư mục: {OUT_DIR.resolve()}

  ┌─────────────────────────────────────────────────────────────┐
  │  Những gì đã làm:                                           │
  │                                                             │
  │  tbl_positions:                                             │
  │    • Xóa Language, DateOfPublish (100% trống)               │
  │    • Xóa 9 cột redundant list (đã có bảng linking)          │
  │    • Xóa YearPost, MonthPost, YearMonth (derived)           │
  │    • Xóa HTMLAdvertisement, NonHTMLAdvertisement            │
  │    • Parse DateofPost, Deadline → YYYY-MM-DD                │
  │    • Chuẩn hóa WorkingTime, ContractType                    │
  │    • fillna Salary, Abstract                                │
  │                                                             │
  │  tbl_university:                                            │
  │    • Xóa longitude, latitude (100% trống)                   │
  │                                                             │
  │  Tất cả bảng:                                               │
  │    • Trim whitespace, fillna chuỗi rỗng                     │
  │    • Drop duplicate rows                                    │
  │    • Weight clip(0,1), drop null FK (bridge tables)         │
  └─────────────────────────────────────────────────────────────┘

  👉 Bước tiếp theo (SQL):
     1. Tạo schema → import theo thứ tự:
        continents → country → university → positiontype → researcharea
        → positions → job_positiontype → positions_researchareas
     2. Đặt FK constraints sau khi import xong tất cả
""")