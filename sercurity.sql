-- ============================================================================
--  07_security.sql  (revised)
--  Phân quyền theo đúng chức năng từng role trong streamlit.py
-- ============================================================================

SELECT DATABASE() AS CurrentDatabase;

-- ============================================================================
-- 1. ADMIN — Toàn quyền + quản lý user
-- ============================================================================
CREATE USER IF NOT EXISTS 'admin_portal'@'localhost'
    IDENTIFIED BY 'Admin@Portal2024!';
GRANT SELECT ON mysql.user TO 'admin_portal'@'localhost';
GRANT ALL PRIVILEGES ON academic_jobs_portal.* TO 'admin_portal'@'localhost'
    WITH GRANT OPTION;   -- Admin có thể cấp quyền cho người khác
GRANT PROCESS ON *.* TO 'admin_portal'@'localhost';
GRANT SHOW_ROUTINE ON *.* TO 'admin_portal'@'localhost';
GRANT CREATE USER ON *.* TO 'admin_portal'@'localhost';
FLUSH PRIVILEGES;


-- ============================================================================
-- 2. EMPLOYER — Chỉ quản lý job & xem đơn ứng tuyển
--    Streamlit: page_employer() → xem job, đăng job mới, tìm kiếm
--    KHÔNG được: xóa, sửa job của trường khác, xem thông tin nhạy cảm
-- ============================================================================
CREATE USER IF NOT EXISTS 'employer_portal'@'localhost'
    IDENTIFIED BY 'Employer@Portal2024!';

-- Đọc các bảng cần thiết
GRANT SELECT ON academic_jobs_portal.AcademicJobs          TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.JobCategories         TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.JobCategoryLinks      TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.JobResearchAreas      TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.ResearchAreas         TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.Countries             TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.Continents            TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.Employers             TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.Applications          TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.Applicants            TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.JobStatusLog          TO 'employer_portal'@'localhost';

-- Đăng & quản lý job (chỉ INSERT/UPDATE, không DELETE)
GRANT INSERT, UPDATE ON academic_jobs_portal.AcademicJobs      TO 'employer_portal'@'localhost';
GRANT INSERT, UPDATE ON academic_jobs_portal.JobCategoryLinks  TO 'employer_portal'@'localhost';
GRANT INSERT, UPDATE ON academic_jobs_portal.JobResearchAreas  TO 'employer_portal'@'localhost';
GRANT SELECT, UPDATE ON academic_jobs_portal.Applications TO 'employer_portal'@'localhost';
-- Views
GRANT SELECT ON academic_jobs_portal.vw_ActiveJobs       TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.vw_ExpiredJobs      TO 'employer_portal'@'localhost';
GRANT SELECT ON academic_jobs_portal.vw_EmployerSummary  TO 'employer_portal'@'localhost';

-- Stored Procedures — chỉ những gì employer cần
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_PostJob        TO 'employer_portal'@'localhost';
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_CloseJob       TO 'employer_portal'@'localhost';
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_EmployerReport TO 'employer_portal'@'localhost';
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_SearchJobs     TO 'employer_portal'@'localhost';

-- Functions
GRANT EXECUTE ON FUNCTION academic_jobs_portal.fn_CountActiveJobs TO 'employer_portal'@'localhost';
GRANT EXECUTE ON FUNCTION academic_jobs_portal.fn_CountTotalJobs  TO 'employer_portal'@'localhost';
GRANT EXECUTE ON FUNCTION academic_jobs_portal.fn_DaysToDeadline  TO 'employer_portal'@'localhost';


-- ============================================================================
-- 3. READONLY (Analyst) — Chỉ xem báo cáo & thống kê
--    Streamlit: page_dashboard() → metrics, charts, top employers
--    KHÔNG được: INSERT, UPDATE, DELETE bất kỳ thứ gì
-- ============================================================================
CREATE USER IF NOT EXISTS 'readonly_portal'@'localhost'
    IDENTIFIED BY 'ReadOnly@Portal2024!';

GRANT SELECT ON academic_jobs_portal.* TO 'readonly_portal'@'localhost';

-- Chỉ chạy các stored procedure báo cáo, không có sp_PostJob/sp_CloseJob
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_SystemReport   TO 'readonly_portal'@'localhost';
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_EmployerReport TO 'readonly_portal'@'localhost';
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_SearchJobs     TO 'readonly_portal'@'localhost';


-- ============================================================================
-- 4. APP_USER — Tìm kiếm việc làm & nộp đơn ứng tuyển
--    Streamlit: page_search() → tìm kiếm, xem chi tiết, nộp đơn
--    KHÔNG được: đăng job, đóng job, xem danh sách applicants của người khác
-- ============================================================================
CREATE USER IF NOT EXISTS 'app_user'@'localhost'
    IDENTIFIED BY 'App@Portal2024!';

-- Chỉ đọc thông tin job, không đọc được thông tin ứng viên khác
GRANT SELECT ON academic_jobs_portal.AcademicJobs      TO 'app_user'@'localhost';
GRANT SELECT ON academic_jobs_portal.JobCategories     TO 'app_user'@'localhost';
GRANT SELECT ON academic_jobs_portal.JobCategoryLinks  TO 'app_user'@'localhost';
GRANT SELECT ON academic_jobs_portal.JobResearchAreas  TO 'app_user'@'localhost';
GRANT SELECT ON academic_jobs_portal.ResearchAreas     TO 'app_user'@'localhost';
GRANT SELECT ON academic_jobs_portal.Countries         TO 'app_user'@'localhost';
GRANT SELECT ON academic_jobs_portal.Continents        TO 'app_user'@'localhost';
GRANT SELECT ON academic_jobs_portal.Employers         TO 'app_user'@'localhost';

-- Chỉ được nộp đơn, không được xem đơn của người khác
GRANT INSERT ON academic_jobs_portal.Applications      TO 'app_user'@'localhost';
GRANT INSERT ON academic_jobs_portal.Applicants        TO 'app_user'@'localhost';

-- Chỉ được tìm kiếm, KHÔNG có sp_PostJob / sp_CloseJob / sp_ExpireJobs
GRANT EXECUTE ON PROCEDURE academic_jobs_portal.sp_SearchJobs   TO 'app_user'@'localhost';

-- Functions cần thiết cho tìm kiếm
GRANT EXECUTE ON FUNCTION academic_jobs_portal.fn_IsJobActive     TO 'app_user'@'localhost';
GRANT EXECUTE ON FUNCTION academic_jobs_portal.fn_DaysToDeadline  TO 'app_user'@'localhost';
GRANT EXECUTE ON FUNCTION academic_jobs_portal.fn_CountActiveJobs TO 'app_user'@'localhost';
-- Gỡ đơn ứng tuyển
GRANT UPDATE ON academic_jobs_portal.Applications TO 'app_user'@'localhost';
FLUSH PRIVILEGES;


-- ── Kiểm tra ──────────────────────────────────────────────────────────────────
SELECT User, Host FROM mysql.user
WHERE User IN ('admin_portal','employer_portal','readonly_portal','app_user');