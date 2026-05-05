"""
============================================================================
  Academic Jobs Portal — Streamlit Web App
  Hybrid Search: BM25 + HNSW (FAISS) với BAAI/bge-small-en-v1.5
  Role-based UI khớp với security.sql (revised)
============================================================================
  Cài đặt:
    pip install streamlit mysql-connector-python faiss-cpu sentence-transformers
    pip install rank-bm25 pandas numpy torch

  Chạy:
    streamlit run streamlit.py
============================================================================
"""

import os
import pickle
import uuid
import warnings
import numpy as np
import pandas as pd
import streamlit as st
import mysql.connector
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# CẤU HÌNH
# ══════════════════════════════════════════════════════════════════════════════
MODEL_NAME = "BAAI/bge-small-en-v1.5"
DATA_DIR   = r"C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql"
META_FILE  = os.path.join(DATA_DIR, "metadata.pkl")
INDEX_FILE = os.path.join(DATA_DIR, "hnsw_index.bin")

# Role → DB user mapping (theo security.sql revised)
ROLE_CONFIG = {
    "👑 Admin":    {"db_user": "admin_portal",    "db_pass": "Admin@Portal2024!"},
    "🏛️ Employer": {"db_user": "employer_portal", "db_pass": "Employer@Portal2024!"},
    "📊 Analyst":  {"db_user": "readonly_portal", "db_pass": "ReadOnly@Portal2024!"},
    "🔍 App User": {"db_user": "app_user",        "db_pass": "App@Portal2024!"},
}

# Mô tả quyền hạn cho màn hình login
ROLE_DESC = {
    "👑 Admin":    "Toàn quyền: search, dashboard, quản lý user",
    "🏛️ Employer": "Đăng & quản lý job, xem đơn ứng tuyển",
    "📊 Analyst":  "Chỉ xem báo cáo & thống kê (read-only)",
    "🔍 App User": "Tìm kiếm & nộp đơn ứng tuyển",
}

DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "academic_jobs_portal"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Academic Jobs Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
    --navy: #0f1f3d; --blue: #1a4080; --accent: #e8a020;
    --light: #f5f7fa; --text: #1a1a2e; --muted: #6b7280;
    --card: #ffffff; --border: #e2e8f0;
}
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--text); }
.portal-header {
    background: linear-gradient(135deg, var(--navy) 0%, var(--blue) 100%);
    color: white; padding: 2rem 2.5rem; border-radius: 16px;
    margin-bottom: 1.5rem; display: flex; align-items: center; gap: 1.5rem;
}
.portal-header h1 { font-family: 'DM Serif Display', serif; font-size: 2rem; margin: 0; color: white; }
.portal-header p  { margin: 0.25rem 0 0; opacity: 0.8; font-size: 0.95rem; }
.role-badge {
    display: inline-block; background: rgba(232,160,32,0.2); color: var(--accent);
    border: 1px solid var(--accent); padding: 0.2rem 0.75rem; border-radius: 20px;
    font-size: 0.8rem; font-weight: 600; margin-left: 0.5rem;
}
.job-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    transition: box-shadow 0.2s, transform 0.2s; border-left: 4px solid var(--blue);
}
.job-card:hover { box-shadow: 0 4px 20px rgba(15,31,61,0.1); transform: translateY(-1px); }
.job-title { font-family: 'DM Serif Display', serif; font-size: 1.15rem; color: var(--navy); margin: 0 0 0.4rem; }
.job-meta { font-size: 0.85rem; color: var(--muted); display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 0.5rem; }
.job-meta span { display: flex; align-items: center; gap: 0.3rem; }
.score-badge {
    float: right; background: var(--light); border: 1px solid var(--border);
    padding: 0.15rem 0.6rem; border-radius: 20px; font-size: 0.75rem; color: var(--muted); font-weight: 500;
}
.tag { display: inline-block; background: #ebf5fb; color: #2471a3; border-radius: 6px; padding: 0.15rem 0.5rem; font-size: 0.78rem; margin-right: 0.3rem; }
.tag-status-active  { background: #d5f5e3; color: #1e8449; }
.tag-status-expired { background: #fde8d8; color: #ca6f1e; }
.tag-status-closed  { background: #f2f3f4; color: #717d7e; }
.login-wrap { max-width: 420px; margin: 4rem auto; background: white; border-radius: 20px; padding: 2.5rem; box-shadow: 0 8px 40px rgba(15,31,61,0.12); }
.login-logo { text-align: center; margin-bottom: 1.5rem; }
.login-logo h2 { font-family: 'DM Serif Display', serif; color: var(--navy); font-size: 1.6rem; margin: 0.5rem 0 0.25rem; }
.login-logo p { color: var(--muted); font-size: 0.9rem; margin: 0; }
[data-testid="metric-container"] { background: white; border: 1px solid var(--border); border-radius: 10px; padding: 0.75rem 1rem; }
.readonly-banner { background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 1rem; font-size: 0.9rem; color: #856404; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_conn(db_user: str, db_pass: str):
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=db_user, password=db_pass,
        auth_plugin="mysql_native_password",
        connection_timeout=10,
    )

def query_df(conn, sql, params=None):
    return pd.read_sql(sql, conn, params=params)

def sidebar_logout(key: str):
    st.markdown("---")
    if st.button("🚪 Đăng xuất", use_container_width=True, key=key):
        st.session_state.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH ENGINE (cached — chỉ load 1 lần)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner="⏳ Đang load search engine...")
def load_search_engine():
    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, "rb") as f:
        metadata = pickle.load(f)
    meta_df = pd.DataFrame(metadata)
    model   = SentenceTransformer(MODEL_NAME)
    return index, meta_df, model

@st.cache_data(ttl=3600, show_spinner=False)
def load_bm25(_conn_info):
    db_user, db_pass = _conn_info
    conn = get_conn(db_user, db_pass)
    df   = query_df(conn, "SELECT JobID, JobTitle FROM AcademicJobs")
    conn.close()
    corpus      = [str(t).lower().split() for t in df["JobTitle"].fillna("")]
    bm25        = BM25Okapi(corpus)
    job_id_list = df["JobID"].tolist()
    return bm25, job_id_list

def add_job_to_index(job_id: str, job_title: str, job_description: str, country: str = "", category_id: str = ""):
    """
    Encode cả Title và Description cho 1 job mới và đẩy vào FAISS index hiện có.
    """
    try:
        # 1. Load engine (từ cache)
        index, meta_df, model = load_search_engine()
 
        # 2. Chuẩn bị nội dung giống hệt lúc chạy prepare.py
        combined_text = f"Job Title: {job_title}. Description: {job_description}"
        
        # Bước 2.1: Chunking (cắt nhỏ nếu mô tả quá dài)
        # 1500 ký tự, overlap 200
        chunks = [combined_text[i:i+1500] for i in range(0, len(combined_text), 1300)]
        
        # Bước 2.2: Encoding các chunk này (thường chỉ 1-5 chunks cho 1 job)
        chunk_vecs = model.encode(chunks, normalize_embeddings=True).astype("float32")
        
        # Bước 2.3: Mean Pooling - Lấy trung bình cộng để ra 1 vector duy nhất
        # Công thức: $$ \vec{V}_{job} = \frac{1}{n} \sum \vec{v}_{chunk} $$
        job_vector = np.mean(chunk_vecs, axis=0, keepdims=True)
 
        # 3. Thêm vector vào FAISS index (HNSW hỗ trợ add thêm cực nhanh)[cite: 4]
        index.add(job_vector)
 
        # 4. Cập nhật Metadata tương ứng[cite: 4]
        new_row = pd.DataFrame([{
            "job_id":      job_id,
            "country":     country,
            "category_id": category_id,
            "status":      "active" # Mặc định job mới là active
        }])
        updated_meta = pd.concat([meta_df, new_row], ignore_index=True)
 
        # 5. Ghi lại file để không bị mất khi khởi động lại App
        faiss.write_index(index, INDEX_FILE)
        with open(META_FILE, "wb") as f:
            pickle.dump(updated_meta.to_dict(orient="records"), f)
 
        # 6. Clear cache để Streamlit nhận diện dữ liệu mới ngay lập tức[cite: 4]
        st.cache_resource.clear()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.warning(f"⚠️ Không thể cập nhật search index: {e}")
        return False

def hybrid_search(query, index, meta_df, embed_model, bm25, bm25_job_ids,
                  top_k=20, filter_country=None, filter_category=None,
                  alpha=0.6, hnsw_pool=200):
    if not query.strip():
        return []
    q_vec = embed_model.encode(
        [f"Represent this sentence: {query}"], normalize_embeddings=True
    ).astype("float32")
    distances, indices = index.search(q_vec, hnsw_pool)
    hnsw_results = {
        meta_df.iloc[idx]["job_id"]: rank
        for rank, idx in enumerate(indices[0]) if idx < len(meta_df)
    }
    tokens      = query.lower().split()
    bm25_scores = bm25.get_scores(tokens)
    bm25_top    = np.argsort(bm25_scores)[::-1][:hnsw_pool]
    bm25_results = {
        bm25_job_ids[i]: rank
        for rank, i in enumerate(bm25_top) if bm25_scores[i] > 0
    }
    candidates = set(hnsw_results) | set(bm25_results)
    if filter_country or filter_category:
        fm = meta_df.copy()
        if filter_country:  fm = fm[fm["country"].isin(filter_country)]
        if filter_category: fm = fm[fm["category_id"].isin(filter_category)]
        candidates &= set(fm["job_id"].tolist())
    if not candidates:
        return []
    k = 60
    rrf = {}
    for jid in candidates:
        rrf[jid] = (alpha       * 1.0 / (k + hnsw_results.get(jid, hnsw_pool+1))
                    + (1-alpha) * 1.0 / (k + bm25_results.get(jid, hnsw_pool+1)))
    return sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:top_k]


# ══════════════════════════════════════════════════════════════════════════════
# UI COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════
def render_header(role: str):
    st.markdown(f"""
    <div class="portal-header">
        <div style="font-size:3rem">🎓</div>
        <div>
            <h1>Academic Jobs Portal</h1>
            <p>NEU-College of Technology · DATCOM Lab
               <span class="role-badge">{role}</span>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_job_card(row, score=None):
    status_cls = f"tag-status-{str(row.get('Status','')).lower()}"
    score_html = f'<span class="score-badge">score: {score:.4f}</span>' if score else ""
    st.markdown(f"""
    <div class="job-card">
        {score_html}
        <div class="job-title">{row.get('JobTitle','N/A')}</div>
        <div class="job-meta">
            <span>🏛️ {row.get('EmployerName','N/A')}</span>
            <span>🌍 {row.get('CountryName','N/A')}</span>
            <span>💼 {row.get('CategoryName','N/A')}</span>
            <span>⏰ {row.get('WorkingTime','N/A')}</span>
            <span>📅 {str(row.get('PublishDate',''))[:10]}</span>
        </div>
        <div>
            <span class="tag {status_cls}">{str(row.get('Status','')).upper()}</span>
            <span class="tag">📋 {row.get('ContractType','N/A')}</span>
            {"<span class='tag'>💰 " + str(row.get('Salary',''))[:40] + "</span>" if row.get('Salary') else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

def _search_sidebar_filters(conn):
    """Sidebar filters dùng chung cho Search page."""
    with st.sidebar:
        st.markdown("### 🔧 Bộ lọc")
        countries = query_df(conn, "SELECT ID_Country, CountryName FROM Countries ORDER BY CountryName")
        sel_countries = st.multiselect(
            "🌍 Quốc gia", options=countries["ID_Country"].tolist(),
            format_func=lambda x: countries.set_index("ID_Country").loc[x, "CountryName"],
        )
        cats = query_df(conn, "SELECT CategoryID, CategoryName FROM JobCategories ORDER BY CategoryName")
        sel_cats = st.multiselect(
            "💼 Loại vị trí", options=cats["CategoryID"].tolist(),
            format_func=lambda x: cats.set_index("CategoryID").loc[x, "CategoryName"],
        )
        sel_status = st.multiselect("📌 Trạng thái", ["active","expired","closed"], default=["active"])
        st.markdown("---")
        st.markdown("### ⚙️ Search Settings")
        alpha = st.slider("HNSW weight (vs BM25)", 0.0, 1.0, 0.6, 0.05)
        top_k = st.slider("Số kết quả tối đa", 5, 50, 20, 5)
    return sel_countries, sel_cats, sel_status, alpha, top_k


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def page_login():
    st.markdown("""
    <div class="login-wrap">
        <div class="login-logo">
            <div style="font-size:3.5rem">🎓</div>
            <h2>Academic Jobs Portal</h2>
            <p>NEU-College of Technology · DATCOM Lab</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("### Đăng nhập")
        role     = st.selectbox("Chọn vai trò", list(ROLE_CONFIG.keys()))
        password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...")

        if st.button("🔐 Đăng nhập", use_container_width=True, type="primary"):
            cfg = ROLE_CONFIG[role]
            try:
                conn = get_conn(cfg["db_user"], password)
                conn.close()
                st.session_state["logged_in"] = True
                st.session_state["role"]      = role
                st.session_state["db_user"]   = cfg["db_user"]
                st.session_state["db_pass"]   = password
                st.rerun()
            except Exception as e:
                st.error(f"❌ Sai mật khẩu hoặc không có quyền truy cập!\n\n`{e}`")

        st.markdown("---")
        st.caption("ℹ️ Vai trò và quyền hạn:")
        for r, desc in ROLE_DESC.items():
            st.caption(f"**{r}**: {desc}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SEARCH  (dùng cho Admin + App User; Employer gọi từ menu của họ)
# ══════════════════════════════════════════════════════════════════════════════
def page_search(conn, show_apply_button: bool = False):
    """
    show_apply_button=True  → App User (có quyền INSERT Applications/Applicants)
    show_apply_button=False → Admin / Employer (chỉ xem)
    """
    index, meta_df, embed_model = load_search_engine()
    bm25, bm25_job_ids = load_bm25(
        (st.session_state["db_user"], st.session_state["db_pass"])
    )
    sel_countries, sel_cats, sel_status, alpha, top_k = _search_sidebar_filters(conn)


    query = st.text_input(
        "", placeholder="🔍  Tìm kiếm... vd: machine learning researcher, professor biology",
        label_visibility="collapsed",
    )

    if not query:
        c1, c2, c3, c4 = st.columns(4)
        stats = query_df(conn, """
            SELECT COUNT(*) AS total, SUM(Status='active') AS active,
                   COUNT(DISTINCT EmployerID) AS employers, COUNT(DISTINCT Country) AS countries
            FROM AcademicJobs
        """).iloc[0]
        c1.metric("📋 Tổng bài đăng", f"{stats['total']:,}")
        c2.metric("✅ Active",         f"{stats['active']:,}")
        c3.metric("🏛️ Trường ĐH",      f"{stats['employers']:,}")
        c4.metric("🌍 Quốc gia",       f"{stats['countries']:,}")
        st.info("💡 Nhập từ khóa để tìm kiếm với Hybrid Search (BM25 + Semantic HNSW)")
        return

    with st.spinner("🔄 Đang tìm kiếm..."):
        ranked = hybrid_search(
            query=query, index=index, meta_df=meta_df, embed_model=embed_model,
            bm25=bm25, bm25_job_ids=bm25_job_ids, top_k=top_k,
            filter_country=sel_countries or None, filter_category=sel_cats or None,
            alpha=alpha, hnsw_pool=300,
        )

    if not ranked:
        st.warning("😕 Không tìm thấy kết quả. Thử lại với từ khóa khác hoặc bỏ bớt bộ lọc.")
        return

    job_ids      = [r[0] for r in ranked]
    score_map    = {r[0]: r[1] for r in ranked}
    placeholders = ",".join(["%s"] * len(job_ids))
    status_clause = (
        "AND j.Status IN ({})".format(",".join([f"'{s}'" for s in sel_status]))
        if sel_status else ""
    )

    df_results = query_df(conn, f"""
        SELECT j.JobID, j.JobTitle, j.Status, j.WorkingTime,
               j.ContractType, j.Salary, j.PublishDate, j.ExpiryDate,
               e.EmployerName, c.CategoryName, co.CountryName
        FROM AcademicJobs j
        LEFT JOIN Employers     e  ON j.EmployerID = e.EmployerID
        LEFT JOIN JobCategories c  ON j.CategoryID = c.CategoryID
        LEFT JOIN Countries     co ON j.Country    = co.ID_Country
        WHERE j.JobID IN ({placeholders}) {status_clause}
    """, params=job_ids)

    df_results["_score"] = df_results["JobID"].map(score_map)
    df_results = df_results.sort_values("_score", ascending=False)

    st.markdown(f"**{len(df_results)} kết quả** cho *\"{query}\"*")
    st.markdown("---")

    for _, row in df_results.iterrows():
        render_job_card(row.to_dict(), score=row["_score"])
        with st.expander("Xem chi tiết"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**JobID:** `{row['JobID']}`")
                st.write(f"**Publish:** {str(row['PublishDate'])[:10]}")
                st.write(f"**Expiry:** {str(row['ExpiryDate'])[:10]}")
            with col2:
                st.write(f"**Salary:** {row.get('Salary') or 'N/A'}")
                st.write(f"**Contract:** {row.get('ContractType') or 'N/A'}")
            ra = query_df(conn, """
                SELECT ra.ResearchArea, jra.Weight FROM JobResearchAreas jra
                JOIN ResearchAreas ra ON jra.ID_ResearchArea = ra.ID_ResearchArea
                WHERE jra.JobID = %s ORDER BY jra.Weight DESC LIMIT 5
            """, params=(row["JobID"],))
            if not ra.empty:
                st.write("**Research Areas:**", " · ".join(ra["ResearchArea"].tolist()))

            # ── Nộp đơn — CHỈ App User mới thấy ─────────────────────────────
            if show_apply_button and str(row.get("Status","")).lower() == "active":
                st.markdown("---")
                st.markdown("##### 📨 Nộp đơn ứng tuyển")
                with st.form(f"apply_form_{row['JobID']}"):
                    c1, c2 = st.columns(2)
                    full_name = c1.text_input("Họ và tên *")
                    email     = c2.text_input("Email *")
                    c3, c4    = st.columns(2)
                    phone     = c3.text_input("Số điện thoại")
                    cv_link = c4.text_input("Link CV (URL)")
                    cover_note  = st.text_area("Cover note (tóm tắt lý do ứng tuyển)", height=100)
                    submitted   = st.form_submit_button("📤 Nộp đơn", type="primary")

                    if submitted:
                        if not full_name or not email:
                            st.error("Vui lòng điền đủ Họ tên và Email.")
                        else:
                            try:
                                cur = conn.cursor()

                                # Kiểm tra email đã tồn tại chưa → tái sử dụng ApplicantID
                                # Tránh dùng ON DUPLICATE KEY UPDATE (cần quyền UPDATE)
                                existing = query_df(conn,
                                    "SELECT ApplicantID FROM Applicants WHERE Email = %s",
                                    params=(email,))

                                if existing.empty:
                                    cur.execute("""
                                        INSERT INTO Applicants
                                            (ApplicantName, Email, PhoneNumber,CVLink)
                                        VALUES (%s, %s, %s, %s)
                                    """, (full_name, email, phone or None, cv_link or None))
                                    applicant_id = cur.lastrowid  
                                else:
                                    # Email đã tồn tại → dùng lại ApplicantID cũ
                                    applicant_id = existing.iloc[0]["ApplicantID"]

                                # Kiểm tra đã nộp đơn cho job này chưa
                                dup_check = query_df(conn, """
                                    SELECT ApplicationID FROM Applications
                                    WHERE JobID = %s AND ApplicantID = %s
                                """, params=(row["JobID"], applicant_id))

                                if not dup_check.empty:
                                    st.warning("⚠️ Bạn đã nộp đơn cho vị trí này rồi!")
                                else:
                                    cur.execute("""
                                        INSERT INTO Applications
                                            (JobID, ApplicantID, ApplyDate, CoverLetter, Status)
                                        VALUES (%s, %s, CURDATE(), %s, 'pending')
                                    """, (row["JobID"], applicant_id, cover_note or None))
                                    conn.commit()
                                    app_id = cur.lastrowid
                                    st.success(f"✅ Nộp đơn thành công! Mã đơn: `{app_id}`")
                            except Exception as e:
                                st.error(f"❌ Lỗi: {e}")

def _page_my_applications(conn):
    """Tab đơn của tôi — App User xem và rút đơn."""
    st.markdown("#### 📬 Đơn ứng tuyển của tôi")

    email_check = st.text_input(
        "Nhập Email đã dùng khi nộp đơn",
        placeholder="example@gmail.com",
        key="myapp_email"
    )

    if not email_check:
        st.info("Nhập email để xem các đơn đã nộp.")
        return

    # Tìm ApplicantID theo email
    applicant = query_df(conn,
        "SELECT ApplicantID, ApplicantName FROM Applicants WHERE Email = %s",
        params=(email_check,))

    if applicant.empty:
        st.warning("Không tìm thấy tài khoản với email này.")
        return

    app_id  = applicant.iloc[0]["ApplicantID"]
    app_name= applicant.iloc[0]["ApplicantName"]
    st.success(f"Xin chào **{app_name}**! Đây là danh sách đơn của bạn:")

    df = query_df(conn, """
        SELECT a.ApplicationID,
               LEFT(j.JobTitle, 45)  AS JobTitle,
               e.EmployerName,
               co.CountryName,
               a.ApplyDate,
               a.Status,
               a.CoverLetter
        FROM Applications a
        JOIN AcademicJobs  j  ON a.JobID       = j.JobID
        JOIN Employers     e  ON j.EmployerID  = e.EmployerID
        JOIN Countries     co ON j.Country     = co.ID_Country
        WHERE a.ApplicantID = %s
        ORDER BY a.ApplyDate DESC
    """, params=(int(app_id),))
    if df.empty:
        st.info("Bạn chưa nộp đơn cho job nào.")
        return

    st.dataframe(
        df.drop(columns=["CoverLetter"]),
        use_container_width=True
    )
    st.caption(f"Tổng: {len(df)} đơn")

    # ── Rút đơn ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🗑️ Rút đơn ứng tuyển")
    pending_apps = df[df["Status"] == "pending"]

    if pending_apps.empty:
        st.info("Không có đơn nào ở trạng thái **pending** để rút.")
    else:
        options = {
            f"{row['ApplicationID']} — {row['JobTitle']}": row["ApplicationID"]
            for _, row in pending_apps.iterrows()
        }
        selected = st.selectbox(
            "Chọn đơn muốn rút (chỉ rút được đơn đang pending)",
            list(options.keys()),
            key="withdraw_sel"
        )
        if st.button("🗑️ Xác nhận rút đơn", type="primary", key="withdraw_btn"):
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE Applications SET Status = 'withdrawn' WHERE ApplicationID = %s AND ApplicantID = %s",
                    (int(options[selected]), int(app_id)))
                conn.commit()
                st.success(f"✅ Đã rút đơn: {selected}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")
# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD  (Analyst + Admin)
# ══════════════════════════════════════════════════════════════════════════════
def page_dashboard(conn):

    # Banner read-only cho Analyst
    if st.session_state["role"] == "📊 Analyst":
        st.markdown('<div class="readonly-banner">👁️ <b>Chế độ xem chỉ đọc</b> — Analyst không thể chỉnh sửa dữ liệu.</div>', unsafe_allow_html=True)

    stats = query_df(conn, """
        SELECT COUNT(*) AS total, SUM(Status='active') AS active,
               SUM(Status='expired') AS expired, SUM(Status='closed') AS closed,
               COUNT(DISTINCT EmployerID) AS employers, COUNT(DISTINCT Country) AS countries
        FROM AcademicJobs
    """).iloc[0]

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("📋 Tổng",     f"{stats['total']:,}")
    c2.metric("✅ Active",   f"{stats['active']:,}")
    c3.metric("⏰ Expired",  f"{stats['expired']:,}")
    c4.metric("🔒 Closed",   f"{stats['closed']:,}")
    c5.metric("🏛️ Trường",   f"{stats['employers']:,}")
    c6.metric("🌍 Quốc gia", f"{stats['countries']:,}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🌍 Top 10 Quốc gia")
        df_c = query_df(conn, """
            SELECT co.CountryName, COUNT(*) AS Jobs
            FROM AcademicJobs j JOIN Countries co ON j.Country = co.ID_Country
            GROUP BY co.CountryName ORDER BY Jobs DESC LIMIT 10
        """)
        st.bar_chart(df_c.set_index("CountryName"))

    with col2:
        st.markdown("#### 💼 Phân bố Category")
        df_cat = query_df(conn, """
            SELECT c.CategoryName, COUNT(jcl.JobID) AS Links
            FROM JobCategoryLinks jcl JOIN JobCategories c ON jcl.CategoryID = c.CategoryID
            GROUP BY c.CategoryName ORDER BY Links DESC
        """)
        st.bar_chart(df_cat.set_index("CategoryName"))

    st.markdown("#### 🏛️ Top 20 Employer")
    df_emp = query_df(conn, """
        SELECT LEFT(e.EmployerName,45) AS Employer, co.CountryName,
               COUNT(j.JobID) AS TotalJobs, SUM(j.Status='active') AS ActiveJobs
        FROM Employers e
        JOIN AcademicJobs j ON e.EmployerID = j.EmployerID
        JOIN Countries co   ON e.Country    = co.ID_Country
        GROUP BY e.EmployerID, e.EmployerName, co.CountryName
        ORDER BY TotalJobs DESC LIMIT 20
    """)
    st.dataframe(df_emp, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: EMPLOYER
# ══════════════════════════════════════════════════════════════════════════════
def page_employer(conn):
    render_header(st.session_state["role"])

    # ── Lấy EmployerID từ session (hỏi 1 lần duy nhất) ────────────────────
    if "employer_id" not in st.session_state:
        st.info("🏛️ Vui lòng nhập EmployerID của trường bạn để bắt đầu.")
        emp_input = st.text_input("EmployerID *", placeholder="vd: EMP-00123")
        if st.button("✅ Xác nhận", type="primary",key="btn_confirm_employer"):
            if emp_input.strip():
                check = query_df(conn,
                    "SELECT EmployerID, EmployerName FROM Employers WHERE EmployerID = %s",
                    params=(emp_input.strip(),))
                if check.empty:
                    st.error("❌ Không tìm thấy EmployerID này trong hệ thống.")
                else:
                    st.session_state["employer_id"]   = emp_input.strip()
                    st.session_state["employer_name"] = check.iloc[0]["EmployerName"]
                    st.rerun()
            else:
                st.error("Vui lòng nhập EmployerID.")
        return

    emp_id   = st.session_state["employer_id"]
    emp_name = st.session_state.get("employer_name", emp_id)

    with st.sidebar:
        st.markdown(f"### 🏛️ {emp_name[:30]}")
        st.caption(f"ID: `{emp_id}`")
        menu = st.radio("", ["📋 Job của tôi", "➕ Đăng job mới", "🔍 Tìm kiếm"])
        sidebar_logout("logout_employer")

    if menu == "📋 Job của tôi":
        st.markdown("#### Danh sách Job của tôi")
        status_filter = st.selectbox("Lọc theo status", ["Tất cả","active","expired","closed"])
        where = "" if status_filter == "Tất cả" else f"AND j.Status = '{status_filter}'"

        df_jobs = query_df(conn, f"""
            SELECT j.JobID, LEFT(j.JobTitle,50) AS Title,
                   c.CategoryName, co.CountryName,
                   j.Status, j.PublishDate, j.ExpiryDate
            FROM AcademicJobs j
            LEFT JOIN JobCategories c  ON j.CategoryID = c.CategoryID
            LEFT JOIN Countries     co ON j.Country    = co.ID_Country
            WHERE j.EmployerID = %s {where}
            ORDER BY j.PublishDate DESC LIMIT 200
        """, params=(emp_id,))

        if df_jobs.empty:
            st.info("Chưa có job nào.")
        else:
            st.dataframe(df_jobs, use_container_width=True)
            st.markdown("---")

            # ── 3 tab hành động ──────────────────────────────────────────
            t1, t2, t3, t4 = st.tabs(["🔒 Đóng / Expire Job", "📬 Đơn ứng tuyển", "✏️ Cập nhật trạng thái đơn", "📝 Sửa Job"])

            # Tab 1: Đóng / Expire
            with t1:
                # Expire hàng loạt
                n_expire = len(df_jobs[
                    (df_jobs["Status"] == "active") &
                    (pd.to_datetime(df_jobs["ExpiryDate"], errors="coerce") < pd.Timestamp.today())
                ])
                st.info(f"Có **{n_expire}** job active đã quá ExpiryDate.")
                if st.button("⚡ Expire tất cả", key="emp_expire_all", disabled=(n_expire == 0)):
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE AcademicJobs SET Status='expired', IsAlive=0
                        WHERE EmployerID=%s AND Status='active'
                        AND ExpiryDate < CURDATE() AND ExpiryDate IS NOT NULL
                    """, (emp_id,))
                    conn.commit()
                    st.success(f"✅ Đã expire {cur.rowcount} job!")
                    st.rerun()

                st.markdown("---")
                # Đóng job cụ thể
                active_jobs = df_jobs[df_jobs["Status"] == "active"]["JobID"].tolist()
                if active_jobs:
                    job_to_close = st.selectbox("Chọn JobID cần đóng", active_jobs, key="emp_close_sel")
                    if st.button("🔒 Xác nhận đóng", type="primary", key="emp_close_btn"):
                        try:
                            cur = conn.cursor()
                            args = [job_to_close, ""]
                            cur.callproc("sp_CloseJob", args)                       
                            conn.commit()
                            st.success(f"✅ Job `{job_to_close}` đã đóng!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")
                else:
                    st.info("Không có job active nào để đóng.")

            # Tab 2: Đơn ứng tuyển
            with t2:
                my_job_ids = df_jobs["JobID"].tolist()
                if my_job_ids:
                    ph = ",".join(["%s"] * len(my_job_ids))
                    df_apps = query_df(conn, f"""
                        SELECT a.ApplicationID, a.JobID, LEFT(j.JobTitle,35) AS JobTitle,
                               ap.ApplicantName, ap.Email, ap.PhoneNumber, ap.CVLink,
                               a.ApplyDate, a.Status,
                               LEFT(a.CoverLetter,80) AS CoverLetter
                        FROM Applications a
                        JOIN AcademicJobs j   ON a.JobID       = j.JobID
                        JOIN Applicants   ap  ON a.ApplicantID = ap.ApplicantID
                        WHERE a.JobID IN ({ph})
                        ORDER BY a.ApplyDate DESC
                    """, params=my_job_ids)
                    if df_apps.empty:
                        st.info("Chưa có đơn nào.")
                    else:
                        job_filter = st.selectbox("Lọc theo Job",
                            ["Tất cả"] + df_apps["JobID"].unique().tolist(), key="emp_app_filter")
                        df_show = df_apps if job_filter == "Tất cả" \
                                  else df_apps[df_apps["JobID"] == job_filter]
                        st.dataframe(df_show, use_container_width=True)
                        st.caption(f"{len(df_show)} đơn")

            # Tab 3: Cập nhật trạng thái đơn
            with t3:
                c1, c2, c3 = st.columns(3)
                app_id_upd = c1.number_input("ApplicationID", min_value=1, step=1, key="emp_upd_id")
                new_status = c2.selectbox("Trạng thái mới",
                    ["pending","reviewed","shortlisted","rejected","accepted"], key="emp_upd_status")
                if c3.button("✏️ Cập nhật", key="emp_upd_btn", type="primary"):
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE Applications SET Status=%s WHERE ApplicationID=%s",
                            (new_status, int(app_id_upd))
                        )
                        conn.commit()
                        st.success(f"✅ ApplicationID {app_id_upd} → **{new_status}**")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
            
            with t4:
                st.markdown("##### ✏️ Chỉnh sửa thông tin Job")
                job_ids_all = df_jobs["JobID"].tolist()
                job_to_edit = st.selectbox("Chọn JobID cần sửa", job_ids_all, key="emp_edit_sel")

                # Load thông tin hiện tại
                job_cur = query_df(conn, """
                    SELECT j.*, c.CategoryName, co.CountryName
                    FROM AcademicJobs j
                    LEFT JOIN JobCategories c  ON j.CategoryID = c.CategoryID
                    LEFT JOIN Countries     co ON j.Country    = co.ID_Country
                    WHERE j.JobID = %s
                """, params=(job_to_edit,)).iloc[0]

                with st.form("edit_job_form"):
                    cats     = query_df(conn, "SELECT CategoryID, CategoryName FROM JobCategories")
                    countries = query_df(conn, "SELECT ID_Country, CountryName FROM Countries ORDER BY CountryName")

                    c1, c2   = st.columns(2)
                    new_title = c1.text_input("JobTitle *", value=str(job_cur["JobTitle"]))
                    cat_opts  = cats.apply(lambda r: f"{r['CategoryID']} — {r['CategoryName']}", axis=1).tolist()
                    cur_cat   = f"{job_cur['CategoryID']} — {job_cur['CategoryName']}"
                    cat_sel   = c2.selectbox("Category", cat_opts,
                                    index=cat_opts.index(cur_cat) if cur_cat in cat_opts else 0)

                    c3, c4   = st.columns(2)
                    co_opts  = countries.apply(lambda r: f"{r['ID_Country']} — {r['CountryName']}", axis=1).tolist()
                    cur_co   = f"{job_cur['Country']} — {job_cur['CountryName']}"
                    co_sel   = c3.selectbox("Quốc gia", co_opts,
                                    index=co_opts.index(cur_co) if cur_co in co_opts else 0)
                    new_expiry = c4.date_input("Expiry Date",
                                    value=pd.to_datetime(job_cur["ExpiryDate"]).date())

                    c5, c6    = st.columns(2)
                    wt_opts   = ["Full Time","Part Time","Negotiation"]
                    new_wt    = c5.selectbox("WorkingTime", wt_opts,
                                    index=wt_opts.index(job_cur["WorkingTime"]) if job_cur["WorkingTime"] in wt_opts else 0)
                    ct_opts   = ["Fixed-term","Permanent","Temporary","Other"]
                    new_ct    = c6.selectbox("ContractType", ct_opts,
                                    index=ct_opts.index(job_cur["ContractType"]) if job_cur["ContractType"] in ct_opts else 0)
                    new_salary = st.text_input("Salary", value=str(job_cur["Salary"] or ""))
                    
                    new_desc = st.text_area("Mô tả công việc chi tiết (Job Description) *", 
                                          value=str(job_cur["JobDescription"] or ""), 
                                          height=300)
                    if st.form_submit_button("💾 Lưu thay đổi", type="primary"):
                        try:
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE AcademicJobs
                                SET JobTitle=%s, CategoryID=%s, Country=%s,
                                    ExpiryDate=%s, WorkingTime=%s, JobDescription=%s, 
                                    ContractType=%s, Salary=%s
                                WHERE JobID=%s AND EmployerID=%s
                            """, (new_title, cat_sel.split(" — ")[0], co_sel.split(" — ")[0],
                                  new_expiry, new_wt, new_desc, new_ct, new_salary or None,
                                  job_to_edit, emp_id))
                            conn.commit()
                            st.success(f"✅ Đã cập nhật job `{job_to_edit}`!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")

    # ── Menu 3: Đăng job mới ──────────────────────────────────────────────
    elif menu == "➕ Đăng job mới":
        st.markdown("#### Đăng Job Mới")
        with st.form("post_job_form"):
            # EmployerID lấy từ session, không để người dùng tự nhập
            st.info(f"🏛️ Đăng dưới tên: **{emp_name}** (`{emp_id}`)")
            c1, c2 = st.columns(2)
            cats    = query_df(conn, "SELECT CategoryID, CategoryName FROM JobCategories")
            cat_sel = c1.selectbox("Category *",
                cats.apply(lambda r: f"{r['CategoryID']} — {r['CategoryName']}", axis=1).tolist())
            countries = query_df(conn, "SELECT ID_Country, CountryName FROM Countries ORDER BY CountryName")
            country = c2.selectbox("Quốc gia *",
                countries.apply(lambda r: f"{r['ID_Country']} — {r['CountryName']}", axis=1).tolist())
            title    = st.text_input("JobTitle *")
            description = st.text_area("Mô tả công việc chi tiết (Job Description) *", 
                                     placeholder="Nhập yêu cầu, kỹ năng và mô tả chi tiết tại đây...",
                                     height=300)
            expiry   = st.date_input("Expiry Date")
            c3, c4   = st.columns(2)
            working  = c3.selectbox("WorkingTime", ["Full Time","Part Time","Negotiation"])
            contract = c4.selectbox("ContractType", ["Fixed-term","Permanent","Temporary","Other"])
            salary   = st.text_input("Salary (vd: £45,000 p.a.)")
            submitted = st.form_submit_button("📤 Đăng job", type="primary")

            if submitted:
                if not title:
                    st.error("Vui lòng điền JobTitle.")
                else:
                    job_id = "WEB-" + str(uuid.uuid4())[:8].upper()
                    cat_id = cat_sel.split(" — ")[0]
                    c_id   = country.split(" — ")[0]
                    try:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO AcademicJobs
                                (JobID, EmployerID, CategoryID, Country, JobTitle,JobDescription,
                                 PublishDate, ExpiryDate, WorkingTime, ContractType,
                                 Salary, Status, IsAlive, JobStatus)
                            VALUES (%s,%s,%s,%s,%s,%s,CURDATE(),%s,%s,%s,,%s,'active',1,1)
                        """, (job_id, emp_id, cat_id, c_id, title, description,
                              expiry, working, contract, salary or None))
                        conn.commit()
                        st.success(f"✅ Job đã được đăng! JobID: `{job_id}`")
                        with st.spinner("🔄 Đang cập nhật vào hệ thống..."):
                            ok = add_job_to_index(
                                job_id=job_id,
                                job_title=title,
                                country=c_id,
                                category_id=cat_id,
                            )
                        if ok:
                            st.info("✅ Job đã được cập nhật ")
                    except Exception as e:
                        st.error(f"❌ Lỗi: {e}")

    # ── Menu 4: Tìm kiếm ──────────────────────────────────────────────────
    elif menu == "🔍 Tìm kiếm":
        page_search(conn, show_apply_button=False)  # Employer chỉ xem, không nộp đơn


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADMIN — USER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def page_admin_users(conn):
    st.markdown("#### 👥 Quản lý User & Phân quyền")
    st.caption("Admin có GRANT OPTION — có thể cấp/thu hồi quyền cho user khác.")

    # Hiển thị danh sách user hiện tại
    try:
        df_users = query_df(conn, """
            SELECT User, Host, account_locked, password_expired
            FROM mysql.user
            WHERE User IN ('admin_portal','employer_portal','readonly_portal','app_user')
        """)
        st.markdown("##### Danh sách user trong hệ thống")
        st.dataframe(df_users, use_container_width=True)
    except Exception as e:
        st.warning(f"Không thể đọc mysql.user: {e}")

    st.markdown("---")
    st.markdown("##### 🔑 Cấp / Thu hồi quyền")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Cấp thêm quyền SELECT cho user**")
        target_user  = st.selectbox("User", ["employer_portal","readonly_portal","app_user"], key="grant_user")
        target_table = st.text_input("Tên bảng", placeholder="vd: AcademicJobs", key="grant_table")
        if st.button("✅ GRANT SELECT", key="btn_grant"):
            ALLOWED_TABLES = [
            "AcademicJobs", "Employers", "Applicants", "Applications",
            "Countries", "JobCategories", "ResearchAreas",
            "JobCategoryLinks", "JobResearchAreas"
            ]
            if target_table.strip() not in ALLOWED_TABLES:
                st.error("❌ Tên bảng không hợp lệ!")
                try:
                    cur = conn.cursor()
                    cur.execute(f"GRANT SELECT ON {DB_NAME}.{target_table} TO '{target_user}'@'localhost'")
                    cur.execute("FLUSH PRIVILEGES")
                    conn.commit()
                    st.success(f"✅ Đã GRANT SELECT ON {target_table} TO {target_user}")
                except Exception as e:
                    st.error(f"❌ {e}")

    with col2:
        st.markdown("**Thu hồi quyền SELECT của user**")
        revoke_user  = st.selectbox("User", ["employer_portal","readonly_portal","app_user"], key="revoke_user")
        revoke_table = st.text_input("Tên bảng", placeholder="vd: AcademicJobs", key="revoke_table")
        if st.button("🚫 REVOKE SELECT", key="btn_revoke"):
            ALLOWED_TABLES = [
            "AcademicJobs", "Employers", "Applicants", "Applications",
            "Countries", "JobCategories", "ResearchAreas",
            "JobCategoryLinks", "JobResearchAreas"
            ]
            if revoke_table.strip() not in ALLOWED_TABLES:
                st.error("❌ Tên bảng không hợp lệ!")
                try:
                    cur = conn.cursor()
                    cur.execute(f"REVOKE SELECT ON {DB_NAME}.{revoke_table} FROM '{revoke_user}'@'localhost'")
                    cur.execute("FLUSH PRIVILEGES")
                    conn.commit()
                    st.success(f"✅ Đã REVOKE SELECT ON {revoke_table} FROM {revoke_user}")
                except Exception as e:
                    st.error(f"❌ {e}")

    st.markdown("---")
    st.markdown("##### 🔒 Khoá / Mở khoá tài khoản")
    lock_user   = st.selectbox("Chọn user", ["employer_portal","readonly_portal","app_user"], key="lock_user")
    col3, col4  = st.columns(2)
    if col3.button("🔒 Khoá tài khoản", key="btn_lock"):
        try:
            cur = conn.cursor()
            cur.execute(f"ALTER USER '{lock_user}'@'localhost' ACCOUNT LOCK")
            conn.commit()
            st.success(f"✅ Đã khoá {lock_user}")
        except Exception as e:
            st.error(f"❌ {e}")
    if col4.button("🔓 Mở khoá tài khoản", key="btn_unlock"):
        try:
            cur = conn.cursor()
            cur.execute(f"ALTER USER '{lock_user}'@'localhost' ACCOUNT UNLOCK")
            conn.commit()
            st.success(f"✅ Đã mở khoá {lock_user}")
        except Exception as e:
            st.error(f"❌ {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADMIN — JOB MANAGEMENT (xóa, force-close, xem tất cả)
# ══════════════════════════════════════════════════════════════════════════════
def page_admin_jobs(conn):
    st.markdown("#### 🗑️ Quản lý Job (Admin only)")
    st.markdown('<div class="readonly-banner">⚠️ Khu vực này cho phép xóa vĩnh viễn dữ liệu khỏi DB. Thao tác cẩn thận.</div>', unsafe_allow_html=True)

    # ── Tìm job cần xóa ───────────────────────────────────────────────────
    st.markdown("##### 🔍 Tìm job theo JobID hoặc từ khóa")
    col1, col2 = st.columns([2, 1])
    search_term = col1.text_input("Nhập JobID hoặc từ khóa tiêu đề", placeholder="vd: WEB-A1B2C3D4 hoặc professor")
    status_f    = col2.selectbox("Status", ["Tất cả", "active", "expired", "closed"])

    if search_term.strip():
        where_status = "" if status_f == "Tất cả" else f"AND j.Status = '{status_f}'"
        df_jobs = query_df(conn, f"""
            SELECT j.JobID, LEFT(j.JobTitle,50) AS Title,
                   e.EmployerName, co.CountryName,
                   j.Status, j.PublishDate, j.ExpiryDate
            FROM AcademicJobs j
            LEFT JOIN Employers e  ON j.EmployerID = e.EmployerID
            LEFT JOIN Countries co ON j.Country    = co.ID_Country
            WHERE (j.JobID LIKE %s OR j.JobTitle LIKE %s) {where_status}
            ORDER BY j.PublishDate DESC LIMIT 50
        """, params=(f"%{search_term}%", f"%{search_term}%"))

        if df_jobs.empty:
            st.info("Không tìm thấy job nào.")
        else:
            st.dataframe(df_jobs, use_container_width=True)

            st.markdown("---")

            # ── Xóa job ───────────────────────────────────────────────────
            st.markdown("##### 🗑️ Xóa Job vĩnh viễn")
            st.caption("Xóa sẽ xóa cả các bản ghi liên quan (Applications, JobCategoryLinks, JobResearchAreas) nếu có ON DELETE CASCADE. Không thể hoàn tác.")

            job_ids_found = df_jobs["JobID"].tolist()
            job_to_delete = st.selectbox("Chọn JobID cần xóa", job_ids_found)

            # Hiển thị thông tin job trước khi xóa
            job_info = df_jobs[df_jobs["JobID"] == job_to_delete].iloc[0]
            st.warning(
                f"**Job sắp xóa:**  \n"
                f"🆔 `{job_info['JobID']}`  \n"
                f"📝 {job_info['Title']}  \n"
                f"🏛️ {job_info['EmployerName']}  \n"
                f"📌 Status: `{job_info['Status']}`"
            )

            # Xác nhận 2 bước
            confirm = st.checkbox(f"✅ Tôi xác nhận muốn xóa vĩnh viễn job `{job_to_delete}`")
            if confirm:
                if st.button("🗑️ XÓA NGAY", type="primary",key="btn_delete_job"):
                    try:
                        cur = conn.cursor()
                        # Xóa bridge tables trước (phòng trường hợp không có CASCADE)
                        cur.execute("DELETE FROM JobCategoryLinks  WHERE JobID = %s", (job_to_delete,))
                        cur.execute("DELETE FROM JobResearchAreas  WHERE JobID = %s", (job_to_delete,))
                        cur.execute("DELETE FROM Applications       WHERE JobID = %s", (job_to_delete,))
                        cur.execute("DELETE FROM JobStatusLog       WHERE JobID = %s", (job_to_delete,))
                        # Xóa job chính
                        cur.execute("DELETE FROM AcademicJobs WHERE JobID = %s", (job_to_delete,))
                        conn.commit()
                        st.success(f"✅ Đã xóa vĩnh viễn job `{job_to_delete}` và các dữ liệu liên quan.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi khi xóa: {e}")
    else:
        st.info("Nhập từ khóa để tìm job cần xóa.")

    # ── Force-close hàng loạt ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### ⚡ Force-close job hết hạn (batch)")
    st.caption("Đóng tất cả job có ExpiryDate < hôm nay nhưng vẫn đang active.")

    df_expired = query_df(conn, """
        SELECT COUNT(*) AS cnt FROM AcademicJobs
        WHERE Status = 'active' AND ExpiryDate < CURDATE()
    """)
    expired_cnt = int(df_expired.iloc[0]["cnt"])

    if expired_cnt > 0:
        st.warning(f"Có **{expired_cnt} job** đã hết hạn nhưng vẫn đang active.")
        if st.button(f"⚡ Đóng tất cả {expired_cnt} job hết hạn",key="btn_force_expire"):
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE AcademicJobs
                    SET Status = 'expired', IsAlive = 0, JobStatus = 1
                    WHERE Status = 'active' AND ExpiryDate < CURDATE()
                """)
                conn.commit()
                st.success(f"✅ Đã đóng {cur.rowcount} job hết hạn.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")
    else:
        st.success("✅ Không có job nào hết hạn còn active.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADMIN — EMPLOYER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def page_admin_employers(conn):
    st.markdown("#### 🏛️ Quản lý Employer")

    tab_list, tab_add, tab_edit, tab_del = st.tabs(
        ["📋 Danh sách", "➕ Thêm mới", "✏️ Sửa", "🗑️ Xóa"])

    # ── Danh sách ─────────────────────────────────────────────────────────
    with tab_list:
        df_emp = query_df(conn, """
            SELECT e.EmployerID, e.EmployerName, co.CountryName,
                   e.Website, COUNT(j.JobID) AS TotalJobs
            FROM Employers e
            LEFT JOIN Countries    co ON e.Country   = co.ID_Country
            LEFT JOIN AcademicJobs j  ON e.EmployerID = j.EmployerID
            GROUP BY e.EmployerID, e.EmployerName, co.CountryName, e.Website
            ORDER BY TotalJobs DESC
        """)
        st.dataframe(df_emp, use_container_width=True)
        st.caption(f"Tổng: {len(df_emp)} employer")

    # ── Thêm mới ──────────────────────────────────────────────────────────
    with tab_add:
        with st.form("add_employer_form"):
            countries = query_df(conn, "SELECT ID_Country, CountryName FROM Countries ORDER BY CountryName")
            c1, c2    = st.columns(2)
            new_name  = c1.text_input("Tên trường *")
            co_opts   = countries.apply(lambda r: f"{r['ID_Country']} — {r['CountryName']}", axis=1).tolist()
            co_sel    = c2.selectbox("Quốc gia *", co_opts)
            website   = st.text_input("Website", placeholder="https://...")
            if st.form_submit_button("➕ Thêm Employer", type="primary"):
                if not new_name:
                    st.error("Vui lòng nhập tên trường.")
                else:
                    try:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO Employers (EmployerName, Country, Website)
                            VALUES (%s, %s, %s)
                        """, (new_name, co_sel.split(" — ")[0], website or None))
                        conn.commit()
                        st.success(f"✅ Đã thêm employer: **{new_name}** (ID: {cur.lastrowid})")
                    except Exception as e:
                        st.error(f"❌ {e}")

    # ── Sửa ───────────────────────────────────────────────────────────────
    with tab_edit:
        emp_id_edit = st.text_input("Nhập EmployerID cần sửa", key="admin_emp_edit_id")
        if emp_id_edit.strip():
            emp_row = query_df(conn,
                "SELECT * FROM Employers WHERE EmployerID = %s",
                params=(emp_id_edit.strip(),))
            if emp_row.empty:
                st.error("Không tìm thấy EmployerID này.")
            else:
                emp_row = emp_row.iloc[0]
                countries = query_df(conn, "SELECT ID_Country, CountryName FROM Countries ORDER BY CountryName")
                with st.form("edit_employer_form"):
                    c1, c2    = st.columns(2)
                    upd_name  = c1.text_input("Tên trường *", value=str(emp_row["EmployerName"]))
                    co_opts   = countries.apply(lambda r: f"{r['ID_Country']} — {r['CountryName']}", axis=1).tolist()
                    cur_co    = f"{emp_row['Country']} — " + (
                        countries[countries["ID_Country"] == emp_row["Country"]]["CountryName"].values[0]
                        if emp_row["Country"] in countries["ID_Country"].values else "")
                    co_sel    = c2.selectbox("Quốc gia", co_opts,
                                    index=co_opts.index(cur_co) if cur_co in co_opts else 0)
                    upd_web   = st.text_input("Website", value=str(emp_row.get("Website") or ""))
                    if st.form_submit_button("💾 Lưu", type="primary"):
                        try:
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE Employers
                                SET EmployerName=%s, Country=%s, Website=%s
                                WHERE EmployerID=%s
                            """, (upd_name, co_sel.split(" — ")[0],
                                  upd_web or None, emp_id_edit.strip()))
                            conn.commit()
                            st.success("✅ Đã cập nhật!")
                        except Exception as e:
                            st.error(f"❌ {e}")

    # ── Xóa ───────────────────────────────────────────────────────────────
    with tab_del:
        st.markdown('<div class="readonly-banner">⚠️ Xóa employer sẽ ảnh hưởng đến tất cả job liên quan!</div>', unsafe_allow_html=True)
        emp_id_del = st.text_input("Nhập EmployerID cần xóa", key="admin_emp_del_id")
        if emp_id_del.strip():
            emp_chk = query_df(conn,
                """SELECT e.EmployerName, COUNT(j.JobID) AS JobCount
                   FROM Employers e LEFT JOIN AcademicJobs j ON e.EmployerID = j.EmployerID
                   WHERE e.EmployerID = %s GROUP BY e.EmployerName""",
                params=(emp_id_del.strip(),))
            if emp_chk.empty:
                st.error("Không tìm thấy EmployerID này.")
            else:
                st.warning(f"**{emp_chk.iloc[0]['EmployerName']}** — có {emp_chk.iloc[0]['JobCount']} job liên quan.")
                if st.checkbox(f"✅ Xác nhận xóa employer `{emp_id_del}`"):
                    if st.button("🗑️ XÓA", type="primary", key="admin_del_emp_btn"):
                        try:
                            cur = conn.cursor()
                            cur.execute("DELETE FROM Employers WHERE EmployerID = %s", (emp_id_del.strip(),))
                            conn.commit()
                            st.success("✅ Đã xóa employer!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e} — Có thể còn job liên kết, cần xóa job trước.")
# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADMIN — CATEGORY MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def page_admin_categories(conn):
    st.markdown("#### 💼 Quản lý Job Category")

    tab_list, tab_add, tab_edit, tab_del = st.tabs(
        ["📋 Danh sách", "➕ Thêm mới", "✏️ Sửa", "🗑️ Xóa"])

    with tab_list:
        df_cat = query_df(conn, """
            SELECT c.CategoryID, c.CategoryName, COUNT(jcl.JobID) AS JobLinks
            FROM JobCategories c
            LEFT JOIN JobCategoryLinks jcl ON c.CategoryID = jcl.CategoryID
            GROUP BY c.CategoryID, c.CategoryName ORDER BY JobLinks DESC
        """)
        st.dataframe(df_cat, use_container_width=True)

    with tab_add:
        with st.form("add_cat_form"):
            new_cat = st.text_input("Tên Category *", placeholder="vd: Data Science")
            if st.form_submit_button("➕ Thêm", type="primary"):
                if not new_cat:
                    st.error("Vui lòng nhập tên category.")
                else:
                    try:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO JobCategories (CategoryName) VALUES (%s)", (new_cat,))
                        conn.commit()
                        st.success(f"✅ Đã thêm category: **{new_cat}** (ID: {cur.lastrowid})")
                    except Exception as e:
                        st.error(f"❌ {e}")

    with tab_edit:
        cats = query_df(conn, "SELECT CategoryID, CategoryName FROM JobCategories ORDER BY CategoryName")
        cat_opts = cats.apply(lambda r: f"{r['CategoryID']} — {r['CategoryName']}", axis=1).tolist()
        cat_sel  = st.selectbox("Chọn Category cần sửa", cat_opts, key="admin_cat_edit_sel")
        with st.form("edit_cat_form"):
            new_name = st.text_input("Tên mới *", value=cat_sel.split(" — ", 1)[1] if cat_sel else "")
            if st.form_submit_button("💾 Lưu", type="primary"):
                cat_id = cat_sel.split(" — ")[0]
                try:
                    cur = conn.cursor()
                    cur.execute("UPDATE JobCategories SET CategoryName=%s WHERE CategoryID=%s",
                                (new_name, cat_id))
                    conn.commit()
                    st.success(f"✅ Đã đổi tên category `{cat_id}` → **{new_name}**")
                except Exception as e:
                    st.error(f"❌ {e}")

    with tab_del:
        cats = query_df(conn, "SELECT CategoryID, CategoryName FROM JobCategories ORDER BY CategoryName")
        cat_opts = cats.apply(lambda r: f"{r['CategoryID']} — {r['CategoryName']}", axis=1).tolist()
        cat_del  = st.selectbox("Chọn Category cần xóa", cat_opts, key="admin_cat_del_sel")
        cat_id   = cat_del.split(" — ")[0] if cat_del else None
        if cat_id:
            link_cnt = query_df(conn,
                "SELECT COUNT(*) AS cnt FROM JobCategoryLinks WHERE CategoryID = %s",
                params=(cat_id,)).iloc[0]["cnt"]
            st.warning(f"Category này đang liên kết với **{link_cnt} job**.")
            if st.checkbox(f"✅ Xác nhận xóa `{cat_del}`"):
                if st.button("🗑️ XÓA", type="primary", key="admin_del_cat_btn"):
                    try:
                        cur = conn.cursor()
                        cur.execute("DELETE FROM JobCategoryLinks WHERE CategoryID = %s", (cat_id,))
                        cur.execute("DELETE FROM JobCategories WHERE CategoryID = %s", (cat_id,))
                        conn.commit()
                        st.success("✅ Đã xóa category và các liên kết!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADMIN — BACKUP & RECOVERY
# ══════════════════════════════════════════════════════════════════════════════
def page_admin_backup(conn):
    st.markdown("#### 🔄 Backup & Recovery")

    BACKUP_DIR     = r"C:\Users\Admin\Downloads\AcademicGateDAta\backups"
    MYSQLDUMP_PATH = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
    DB_USER        = "admin_portal"
    DB_PASS        = "Admin@Portal2024!"
    DB_NAME        = "academic_jobs_portal"

    tab_backup, tab_restore, tab_history = st.tabs(
        ["💾 Backup ngay", "🔄 Restore", "📋 Lịch sử"])

    # ── Backup ngay ───────────────────────────────────────────────────────
    with tab_backup:
        st.info("Tạo file backup SQL ngay lập tức — nên làm trước khi xóa dữ liệu lớn.")
        # Thay đoạn try trong tab_backup thành
    if st.button("💾 Chạy Backup", type="primary", key="btn_manual_backup"):
        try:
            import subprocess, datetime
            os.makedirs(BACKUP_DIR, exist_ok=True)
            ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(BACKUP_DIR, f"manual_backup_{ts}.sql")
            cmd = [MYSQLDUMP_PATH,
               f"-u{DB_USER}", f"--password={DB_PASS}",
               "--routines", "--triggers",
               DB_NAME]
        
            # Bắt cả stderr để xem lỗi thực sự
            result = subprocess.run(
                cmd,
                stdout=open(filename, "w", encoding="utf-8"),
                stderr=subprocess.PIPE,
                text=True
            )

            stderr_output = result.stderr or ""
            # Bỏ qua warning password — chỉ là cảnh báo không phải lỗi
            real_errors = "\n".join([
                l for l in stderr_output.splitlines()
                if "Warning" not in l and l.strip()
            ])

            if result.returncode != 0 and real_errors:
                st.error(f"❌ mysqldump báo lỗi:\n\n```\n{real_errors}\n```")
            else:
                size = os.path.getsize(filename) / 1024
                st.success(f"✅ Backup thành công!\n\n📁 `{filename}`\n📦 `{size:.1f} KB`")
        except Exception as e:
            st.error(f"❌ {e}")

    # ── Restore ───────────────────────────────────────────────────────────
    with tab_restore:
        st.markdown('<div class="readonly-banner">⚠️ Restore sẽ ghi đè toàn bộ dữ liệu hiện tại. Không thể hoàn tác — hãy backup trước!</div>',
                    unsafe_allow_html=True)

        files = []
        if os.path.exists(BACKUP_DIR):
            files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")], reverse=True)

        if not files:
            st.warning("Chưa có file backup nào trong thư mục.")
        else:
            selected = st.selectbox("Chọn file backup để restore", files, key="restore_sel")
            st.caption(f"📁 `{os.path.join(BACKUP_DIR, selected)}`")

            if st.checkbox("✅ Tôi hiểu thao tác này sẽ ghi đè toàn bộ dữ liệu hiện tại"):
                if st.button("🔄 Restore ngay", type="primary", key="btn_restore"):
                    try:
                        import subprocess
                        MYSQL_PATH = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
                        filepath   = os.path.join(BACKUP_DIR, selected)
                        cmd = [MYSQL_PATH,
                               f"-u{DB_USER}", f"--password={DB_PASS}",
                               DB_NAME]
                        with open(filepath, "r", encoding="utf-8") as f:
                            subprocess.run(cmd, stdin=f, check=True)
                        st.success(f"✅ Restore thành công từ `{selected}`!")
                    except Exception as e:
                        st.error(f"❌ {e}")

    # ── Lịch sử ───────────────────────────────────────────────────────────
    with tab_history:
        if os.path.exists(BACKUP_DIR):
            import datetime
            rows = []
            for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
                if not f.endswith(".sql"): continue
                fpath = os.path.join(BACKUP_DIR, f)
                size  = os.path.getsize(fpath) / 1024
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
                loai  = "🤖 Tự động" if f.startswith("backup_") else "👤 Thủ công"
                rows.append({"File": f, "Loại": loai,
                             "Size (KB)": f"{size:.1f}", "Thời điểm": mtime})
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                st.caption(f"Tổng: {len(rows)} file backup")
            else:
                st.info("Chưa có file backup nào.")
        else:
            st.info(f"Thư mục backup chưa tồn tại: `{BACKUP_DIR}`")
# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if not st.session_state.get("logged_in"):
        page_login()
        return

    try:
        conn = get_conn(st.session_state["db_user"], st.session_state["db_pass"])
    except Exception as e:
        st.error(f"❌ Mất kết nối database: {e}")
        st.session_state.clear()
        st.rerun()
        return

    role = st.session_state["role"]

    # ── ADMIN: Search + Dashboard + User Management ────────────────────────
    if role == "👑 Admin":
        with st.sidebar:
            st.markdown("### 👑 Admin Menu")
            sidebar_logout("logout_admin")
        render_header(st.session_state["role"])
        # Dòng 982 — thay thế
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🔍 Tìm kiếm", "📊 Dashboard", "🗑️ Quản lý Job",
            "🏛️ Quản lý Employer", "💼 Quản lý Category", "👥 Quản lý User","🔄 Backup & Recovery"
        ])
        with tab1: page_search(conn, show_apply_button=False)
        with tab2: page_dashboard(conn)
        with tab3: page_admin_jobs(conn)
        with tab4: page_admin_employers(conn)
        with tab5: page_admin_categories(conn)
        with tab6: page_admin_users(conn)
        with tab7: page_admin_backup(conn)

    # ── EMPLOYER: Quản lý job + xem đơn ứng tuyển ─────────────────────────
    elif role == "🏛️ Employer":
        page_employer(conn)

    # ── ANALYST: Dashboard read-only ──────────────────────────────────────
    elif role == "📊 Analyst":
        with st.sidebar:
            st.markdown("### 📊 Analyst")
            sidebar_logout("logout_analyst")
        page_dashboard(conn)

    # ── APP USER: Tìm kiếm + Nộp đơn + Đơn của tôi ───────────────────────
    elif role == "🔍 App User":
        with st.sidebar:
            st.markdown("### 🔍 App User")
            sidebar_logout("logout_appuser")
        tab_search, tab_myapps = st.tabs(["🔍 Tìm kiếm & Ứng tuyển", "📬 Đơn của tôi"])
        with tab_search:
            page_search(conn, show_apply_button=True)
        with tab_myapps:
            _page_my_applications(conn)


if __name__ == "__main__":
    main()