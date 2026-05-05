-- ============================================================================
--  05_functions.sql
--  User Defined Functions cho Academic Jobs Portal
-- ============================================================================

DELIMITER $$

-- ── UDF 1: Đếm số active jobs của một Employer ────────────────────────────────
-- Cách dùng: SELECT fn_CountActiveJobs('UNI001');
DROP FUNCTION IF EXISTS fn_CountActiveJobs$$
CREATE FUNCTION fn_CountActiveJobs(p_EmployerID VARCHAR(50))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count
    FROM AcademicJobs
    WHERE EmployerID = p_EmployerID
      AND Status = 'active';
    RETURN v_count;
END$$


-- ── UDF 2: Đếm tổng jobs của một Employer (tất cả trạng thái) ─────────────────
-- Cách dùng: SELECT fn_CountTotalJobs('UNI001');
DROP FUNCTION IF EXISTS fn_CountTotalJobs$$
CREATE FUNCTION fn_CountTotalJobs(p_EmployerID VARCHAR(50))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count
    FROM AcademicJobs
    WHERE EmployerID = p_EmployerID;
    RETURN v_count;
END$$


-- ── UDF 3: Kiểm tra job còn active không ──────────────────────────────────────
-- Cách dùng: SELECT fn_IsJobActive('JOB001');
-- Trả về: 1 = còn active, 0 = không
DROP FUNCTION IF EXISTS fn_IsJobActive$$
CREATE FUNCTION fn_IsJobActive(p_JobID VARCHAR(50))
RETURNS TINYINT(1)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_status VARCHAR(20);
    SELECT Status INTO v_status
    FROM AcademicJobs WHERE JobID = p_JobID;
    RETURN IF(v_status = 'active', 1, 0);
END$$


-- ── UDF 4: Tính số ngày còn lại đến deadline ──────────────────────────────────
-- Cách dùng: SELECT fn_DaysToDeadline('JOB001');
-- Trả về: số ngày dương = còn hạn, âm = đã quá hạn, NULL = không có deadline
DROP FUNCTION IF EXISTS fn_DaysToDeadline$$
CREATE FUNCTION fn_DaysToDeadline(p_JobID VARCHAR(50))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_expiry DATE;
    SELECT ExpiryDate INTO v_expiry
    FROM AcademicJobs WHERE JobID = p_JobID;
    IF v_expiry IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN DATEDIFF(v_expiry, CURDATE());
END$$


-- ── UDF 5: Đếm số jobs theo Research Area ────────────────────────────────────
-- Cách dùng: SELECT fn_CountJobsByResearchArea('RA001');
DROP FUNCTION IF EXISTS fn_CountJobsByResearchArea$$
CREATE FUNCTION fn_CountJobsByResearchArea(p_ResearchAreaID VARCHAR(50))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count
    FROM JobResearchAreas
    WHERE ID_ResearchArea = p_ResearchAreaID;
    RETURN v_count;
END$$


-- ── UDF 6: Đếm số jobs theo Country ──────────────────────────────────────────
-- Cách dùng: SELECT fn_CountJobsByCountry('UK01');
DROP FUNCTION IF EXISTS fn_CountJobsByCountry$$
CREATE FUNCTION fn_CountJobsByCountry(p_CountryID VARCHAR(20))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count
    FROM AcademicJobs
    WHERE Country = p_CountryID
      AND Status  = 'active';
    RETURN v_count;
END$$

DELIMITER ;


-- ── Kiểm tra ──────────────────────────────────────────────────────────────────
-- Lấy 1 EmployerID và JobID thực tế để test
SELECT EmployerID FROM Employers  LIMIT 10;
SELECT JobID      FROM AcademicJobs LIMIT 10;