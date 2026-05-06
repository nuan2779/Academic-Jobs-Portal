# 🎓 Academic Jobs Portal & Employer Management System
> **Project 21 — DATCOM Lab, NEU-College of Technology**  
> National Economics University | Faculty of Data Science and Artificial Intelligence

---

## 📌 Overview

A full-stack academic recruitment platform built on **MySQL + Python + Streamlit**, featuring a **Hybrid Search engine (BM25 + HNSW)** for intelligent job discovery. The system manages the complete lifecycle of academic job postings — from employer publication to applicant submission — with role-based access control enforced at both the database and application layers.

The dataset is sourced from **AcademicGate**, a real-world international academic job board, containing **41,635 job postings** across 22 countries and 23 research disciplines.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔍 **Hybrid Search** | BM25 (keyword) + HNSW (semantic) fused via Reciprocal Rank Fusion |
| 🔐 **Role-Based Access** | 4 roles: Admin, Employer, Analyst, App User — enforced via MySQL GRANT |
| 📊 **Analytics Dashboard** | Real-time stats by country, category, research area, employer |
| 📝 **Application Tracking** | Full lifecycle: pending → reviewed → shortlisted → accepted/rejected |
| ⚙️ **Auto Job Management** | Triggers auto-expire jobs, log status changes, enforce constraints |
| 🛡️ **DB Security** | RBAC, input validation, SQL injection whitelist protection |
| 💾 **Backup & Recovery** | Scheduled `mysqldump` via Windows Task Scheduler + web UI restore |

---

## 🗂️ Project Structure


AcademicGateDAta/
│
├── cleaned_for_sql/              # Cleaned CSV files ready for MySQL import
│   ├── tbl_continents_clean.csv
│   ├── tbl_country_clean.csv
│   ├── tbl_university_clean.csv
│   ├── tbl_positiontype_clean.csv
│   ├── tbl_researcharea_clean.csv
│   ├── tbl_positions_clean.csv
│   ├── tbl_job_positiontype_clean.csv
│   ├── tbl_positions_researchareas_clean.csv
│   ├── applicants.csv
│   ├── blogs.csv
│   ├── news.csv
│   ├── embeddings.npy            # Pre-computed job vectors
│   ├── metadata.pkl              # Job metadata for HNSW filtering
│   └── hnsw_index.bin            # FAISS HNSW index
│
├── sql/
│   ├── 01_create_table.sql       # Schema: 12 tables
│   ├── 02_load_data.sql          # LOAD DATA with column mapping
│   ├── 03_views.sql              # 6 views
│   ├── 04_store_produced.sql     # 6 stored procedures
│   ├── 05_functions.sql          # 6 UDFs
│   ├── 06_triggers.sql           # 3 triggers
│   ├── 07_sercurity.sql          # RBAC: 4 user roles
│   └── 08_add_tables.sql         # Applicants, Applications, Blogs, News
│
├── prepare.py                    # Vectorization pipeline (BGE + FAISS)
├── streamlit.py                  # Main web application
├── clean_academicgate.py         # Data cleaning script
└── README.md




## 🏗️ Database Schema

**12 tables** organized in a star-schema pattern:


Continents ──► Countries ──► Employers ──► AcademicJobs ◄── JobCategories
                                                │
                                    ┌───────────┴───────────┐
                              Applications            JobCategoryLinks
                                   │                  JobResearchAreas
                              Applicants               JobStatusLog (log)
                                                      ResearchAreas
                              Blogs / News (optional)




## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| **Database** | MySQL 8.0 |
| **Backend** | Python 3.11, mysql-connector-python |
| **Frontend** | Streamlit |
| **Semantic Search** | FAISS (HNSW), `BAAI/bge-small-en-v1.5` |
| **Keyword Search** | BM25 (rank-bm25) |
| **Data Processing** | Pandas, NumPy |
| **DB Admin** | MySQL Workbench 8.0 |

---

## 🚀 Getting Started

### 1. Prerequisites

bash
pip install streamlit mysql-connector-python faiss-cpu \
            sentence-transformers rank-bm25 pandas numpy torch


### 2. Database Setup

Run SQL scripts in order inside MySQL Workbench:

sql
-- Step 1: Create schema
SOURCE sql/01_create_table.sql;

-- Step 2: Load data (update file paths first)
SOURCE sql/02_load_data.sql;

-- Step 3: Create views, procedures, functions, triggers
SOURCE sql/03_views.sql;
SOURCE sql/04_store_produced.sql;
SOURCE sql/05_functions.sql;
SOURCE sql/06_triggers.sql;

-- Step 4: Configure security
SOURCE sql/07_sercurity.sql;

-- Step 5: Add supplementary tables + sample data
SOURCE sql/08_add_tables.sql;


### 3. Build Search Index

bash
# Edit DB_CONFIG and OUTPUT_DIR in prepare.py first
python prepare.py


This generates 3 files in `cleaned_for_sql/`:
- `embeddings.npy` — job vectors
- `metadata.pkl` — filter metadata
- `hnsw_index.bin` — FAISS index

### 4. Run the Web App

bash
# Edit DB_CONFIG and DATA_DIR in streamlit.py first
streamlit run streamlit.py


Open `http://localhost:8501` in your browser.

---

## 👥 User Roles & Credentials

| Role | DB User | Default Password | Access |
|---|---|---|---|
| 👑 Admin | `admin_portal` | `Admin@Portal2024!` | Full access + system management |
| 🏛️ Employer | `employer_portal` | `Employer@Portal2024!` | Post/manage jobs, view applications |
| 📊 Analyst | `readonly_portal` | `ReadOnly@Portal2024!` | Dashboard & reports (read-only) |
| 🔍 App User | `app_user` | `App@Portal2024!` | Search jobs + apply |

> ⚠️ Change all passwords before any public deployment.

---

## 🔍 Hybrid Search Architecture


User Query
    │
    ├──► BM25         ──► Top-300 by keyword rank
    │     └── rank-bm25
    │
    └──► HNSW (Semantic)     ──► Top-300 by vector similarity
          └── FAISS + BGE
                │
                ▼
         RRF Fusion (k=60)
         score = α·(1/k+r_HNSW) + (1-α)·(1/k+r_BM25)
                │
                ▼
         Metadata Filter
         (country, category)
                │
                ▼
         Top-K Results → MySQL fetch → UI


**α (HNSW weight)** is adjustable via sidebar slider (0 = pure keyword, 1 = pure semantic).

---

## 📊 Dataset Statistics

| Metric | Value |
|---|---|
| Total job postings | 41,635 |
| Universities | 3,053 |
| Countries | 22 active (246 in lookup) |
| Research areas | 23 |
| Position categories | 10 |
| Bridge table rows | ~1.26M |
| Time period | Jan 2024 – Mar 2025 |

---

## 🗃️ Advanced DB Objects

| Type | Count | Examples |
|---|---|---|
| **Views** | 6 | `vw_ActiveJobs`, `vw_ExpiredJobs`, `vw_EmployerSummary` |
| **Stored Procedures** | 6 | `sp_PostJob`, `sp_CloseJob`, `sp_ExpireJobs` |
| **UDFs** | 6 | `fn_IsJobActive`, `fn_DaysToDeadline`, `fn_CountActiveJobs` |
| **Triggers** | 3 | `trg_SetJobStatus_Insert`, `trg_LogJobStatusChange` |
| **Indexes** | 15 | FULLTEXT on `JobTitle`, composite on `(JobID, ApplicantID)` |

---

## ⚠️ Known Limitations

- HNSW index requires manual rebuild (`prepare.py`) when new jobs are added
- Leak of salary data ()
- Authentication relies on MySQL passwords only 
- Local deployment only — not production-ready out of the box

---

## 📄 License

This project was developed for academic purposes as part of the NEU curriculum.  
Not licensed for commercial use.

---

## 👤 Author

**Nguyễn Hữu Luân** — Student ID: 11247191  
Faculty of Data Science and Artificial Intelligence  
National Economics University, Hanoi  
Supervisor: Dr. Hung Tran
