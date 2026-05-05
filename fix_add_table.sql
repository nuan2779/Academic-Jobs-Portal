USE academic_jobs_portal;

-- 1. Xóa dữ liệu cũ trong bảng Applications để làm lại cho chuẩn
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE Applications;
SET FOREIGN_KEY_CHECKS = 1;

-- 2. Tạo bảng tạm chứa 500 JobID ngẫu nhiên
DROP TEMPORARY TABLE IF EXISTS tmp_job_ids;
CREATE TEMPORARY TABLE tmp_job_ids (
    seq    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    JobID  VARCHAR(50) NOT NULL
);

INSERT INTO tmp_job_ids (JobID)
SELECT JobID FROM AcademicJobs ORDER BY RAND() LIMIT 500;

-- 3. Sử dụng Cross Join để nhân bản 100 người x 4 đơn = 400 đơn
INSERT INTO Applications (JobID, ApplicantID, ApplyDate, Status, CoverLetter)
SELECT 
    t.JobID,
    a.ApplicantID,
    a.ApplyDate,
    a.Status,
    a.CoverLetter
FROM (
    SELECT 
        ap.ApplicantID,
        -- Tạo 4 phiên bản cho mỗi ApplicantID
        n.num AS multi,
        -- Tính toán ID công việc để không ai bị trùng Job
        ((ap.ApplicantID - 1) + (n.num - 1) * 100) % 500 + 1 AS job_seq,
        DATE_ADD('2024-01-01', INTERVAL FLOOR(RAND() * 730) DAY) AS ApplyDate,
        ELT(1 + FLOOR(RAND() * 5), 'pending','reviewed','shortlisted','rejected','accepted') AS Status,
        ELT(1 + FLOOR(RAND() * 4), 
            'I am very interested in this position.',
            'My background aligns well with your requirements.',
            'Confident I can contribute to your research team.',
            'Looking forward to an interview opportunity.'
        ) AS CoverLetter
    FROM Applicants ap
    -- Nhân bản mỗi dòng thành 4 dòng
    CROSS JOIN (
        SELECT 1 AS num UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
    ) n
) a
JOIN tmp_job_ids t ON t.seq = a.job_seq
ON DUPLICATE KEY UPDATE Status = a.Status;

DROP TEMPORARY TABLE IF EXISTS tmp_job_ids;

-- 4. Kiểm tra kết quả cuối cùng
SELECT COUNT(*) AS 'Tổng số Applications hiện có' FROM Applications;