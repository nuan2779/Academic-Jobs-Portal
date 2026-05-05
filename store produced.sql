-- ============================================================================
--  04_stored_procedures.sql
--  Stored Procedures cho Academic Jobs Portal
-- ============================================================================

DELIMITER $$

-- ── SP 1: Tìm kiếm job theo bộ lọc ───────────────────────────────────────────
-- Cách dùng: CALL sp_SearchJobs('UK01', 'POS001', 'professor');
-- Truyền NULL để bỏ qua bộ lọc đó
DROP PROCEDURE IF EXISTS sp_SearchJobs$$
CREATE PROCEDURE sp_SearchJobs(
    IN p_Country     VARCHAR(20),   -- NULL = tất cả quốc gia
    IN p_CategoryID  VARCHAR(50),   -- NULL = tất cả category
    IN p_Keyword     VARCHAR(200)   -- NULL = không lọc từ khóa
)
BEGIN
    SELECT
        j.JobID,
        j.JobTitle,
        j.JobDescription,
        e.EmployerName,
        c.CategoryName,
        co.CountryName,
        j.WorkingTime,
        j.ContractType,
        j.Salary,
        j.PublishDate,
        j.ExpiryDate,
        DATEDIFF(j.ExpiryDate, CURDATE()) AS DaysRemaining
    FROM AcademicJobs  j
    JOIN Employers     e  ON j.EmployerID = e.EmployerID
    JOIN JobCategories c  ON j.CategoryID = c.CategoryID
    JOIN Countries     co ON j.Country    = co.ID_Country
    WHERE j.Status = 'active'
      AND (p_Country    IS NULL OR j.Country    = p_Country)
      AND (p_CategoryID IS NULL OR j.CategoryID = p_CategoryID)
      AND (p_Keyword    IS NULL OR j.JobTitle LIKE CONCAT('%', p_Keyword, '%'))
    ORDER BY j.PublishDate DESC;
END$$


-- ── SP 2: Đăng job mới ────────────────────────────────────────────────────────
-- Cách dùng: CALL sp_PostJob('JOB999', 'UNI001', 'POS001', 'UK01', 'Lecturer', '2025-12-31', 'Full Time', 'Fixed-term', '£45,000', @result); SELECT @result;
DROP PROCEDURE IF EXISTS sp_PostJob$$
CREATE PROCEDURE sp_PostJob(
    IN  p_JobID        VARCHAR(50),
    IN  p_EmployerID   VARCHAR(50),
    IN  p_CategoryID   VARCHAR(50),
    IN  p_Country      VARCHAR(20),
    IN  p_JobTitle     VARCHAR(1000),
    IN  p_ExpiryDate   DATE,
    IN  p_WorkingTime  VARCHAR(50),
    IN  p_ContractType VARCHAR(50),
    IN  p_Salary       VARCHAR(500),
    OUT p_Result       VARCHAR(200)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET p_Result = 'ERROR: Không thể đăng job — kiểm tra lại EmployerID, CategoryID, Country.';
    END;

    INSERT INTO AcademicJobs (
        JobID, EmployerID, CategoryID, Country,
        JobTitle, PublishDate, ExpiryDate,
        WorkingTime, ContractType, Salary,
        Status, IsAlive, JobStatus
    ) VALUES (
        p_JobID, p_EmployerID, p_CategoryID, p_Country,
        p_JobTitle, CURDATE(), p_ExpiryDate,
        p_WorkingTime, p_ContractType, p_Salary,
        'active', 1, 1
    );

    SET p_Result = CONCAT('SUCCESS: Job "', p_JobTitle, '" (', p_JobID, ') đã được đăng.');
END$$


-- ── SP 3: Đóng job ────────────────────────────────────────────────────────────
-- Cách dùng: CALL sp_CloseJob('JOB999', @result); SELECT @result;
DROP PROCEDURE IF EXISTS sp_CloseJob$$
CREATE PROCEDURE sp_CloseJob(
    IN  p_JobID   VARCHAR(50),
    OUT p_Result  VARCHAR(200)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM AcademicJobs WHERE JobID = p_JobID) THEN
        SET p_Result = CONCAT('ERROR: Không tìm thấy JobID = ', p_JobID);
    ELSEIF (SELECT Status FROM AcademicJobs WHERE JobID = p_JobID) = 'closed' THEN
        SET p_Result = CONCAT('WARNING: Job ', p_JobID, ' đã ở trạng thái closed rồi.');
    ELSE
        UPDATE AcademicJobs
        SET Status = 'closed', IsAlive = 0, JobStatus = 9
        WHERE JobID = p_JobID;
        SET p_Result = CONCAT('SUCCESS: Job ', p_JobID, ' đã được đóng.');
    END IF;
END$$


-- ── SP 4: Cập nhật hàng loạt job hết hạn (chạy định kỳ) ──────────────────────
-- Cách dùng: CALL sp_ExpireJobs();
DROP PROCEDURE IF EXISTS sp_ExpireJobs$$
CREATE PROCEDURE sp_ExpireJobs()
BEGIN
    DECLARE v_count INT DEFAULT 0;

    UPDATE AcademicJobs
    SET Status  = 'expired',
        IsAlive = 0
    WHERE Status     = 'active'
      AND ExpiryDate < CURDATE()
      AND ExpiryDate IS NOT NULL;

    SET v_count = ROW_COUNT();
    SELECT v_count AS JobsExpired,
           CONCAT('Đã expire ', v_count, ' job(s) tính đến ', CURDATE()) AS Message;
END$$


-- ── SP 5: Thống kê tổng hợp theo Employer ────────────────────────────────────
-- Cách dùng: CALL sp_EmployerReport('UNI001');
DROP PROCEDURE IF EXISTS sp_EmployerReport$$
CREATE PROCEDURE sp_EmployerReport(
    IN p_EmployerID VARCHAR(50)
)
BEGIN
    -- Thông tin employer
    SELECT
        e.EmployerID,
        e.EmployerName,
        co.CountryName
    FROM Employers e
    JOIN Countries co ON e.Country = co.ID_Country
    WHERE e.EmployerID = p_EmployerID;

    -- Thống kê job
    SELECT
        COUNT(*)                        AS TotalJobs,
        SUM(Status = 'active')          AS ActiveJobs,
        SUM(Status = 'expired')         AS ExpiredJobs,
        SUM(Status = 'closed')          AS ClosedJobs,
        MIN(PublishDate)                AS FirstPosted,
        MAX(PublishDate)                AS LastPosted
    FROM AcademicJobs
    WHERE EmployerID = p_EmployerID;

    -- Top categories của employer này
    SELECT
        c.CategoryName,
        COUNT(*)    AS JobCount
    FROM AcademicJobs     j
    JOIN JobCategoryLinks jcl ON j.JobID      = jcl.JobID
    JOIN JobCategories    c   ON jcl.CategoryID = c.CategoryID
    WHERE j.EmployerID = p_EmployerID
    GROUP BY c.CategoryID, c.CategoryName
    ORDER BY JobCount DESC
    LIMIT 5;
END$$


-- ── SP 6: Thống kê tổng hợp toàn hệ thống ────────────────────────────────────
-- Cách dùng: CALL sp_SystemReport();
DROP PROCEDURE IF EXISTS sp_SystemReport$$
CREATE PROCEDURE sp_SystemReport()
BEGIN
    SELECT
        COUNT(*)                        AS TotalJobs,
        SUM(Status = 'active')          AS ActiveJobs,
        SUM(Status = 'expired')         AS ExpiredJobs,
        SUM(Status = 'closed')          AS ClosedJobs,
        COUNT(DISTINCT EmployerID)      AS TotalEmployers,
        COUNT(DISTINCT Country)         AS TotalCountries,
        MIN(PublishDate)                AS EarliestPost,
        MAX(PublishDate)                AS LatestPost
    FROM AcademicJobs;
END$$

DELIMITER ;


-- ── Kiểm tra ──────────────────────────────────────────────────────────────────
-- Test SP tìm kiếm (NULL = không lọc)
-- CALL sp_SearchJobs(NULL, NULL, 'professor');

-- Test báo cáo hệ thống
CALL sp_SystemReport();