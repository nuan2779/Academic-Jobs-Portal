-- ============================================================================
--  08_missing_tables_and_data.sql
--  1. Tạo 4 bảng còn thiếu (Applicants, Applications, Blogs, News)
--  2. Import sample data từ các file CSV sạch
--  3. Applications: Tự động map JobID thực tế từ bảng AcademicJobs
-- ============================================================================

USE academic_jobs_portal;

-- Tắt kiểm tra khóa ngoại để thực hiện Reset dữ liệu sạch sẽ
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS Applications;
DROP TABLE IF EXISTS Applicants;
DROP TABLE IF EXISTS Blogs;
DROP TABLE IF EXISTS News;

SET FOREIGN_KEY_CHECKS = 1;

-- ── 1. Tạo bảng Applicants ───────────────────────────────────────────────────
-- Lưu thông tin người tìm việc
CREATE TABLE Applicants (
    ApplicantID   INT           NOT NULL AUTO_INCREMENT,
    ApplicantName VARCHAR(200)  NOT NULL,
    Email         VARCHAR(200)  NOT NULL,
    PhoneNumber   VARCHAR(50)   DEFAULT NULL,
    CVLink        VARCHAR(500)  DEFAULT NULL,
    CreatedAt     DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_applicants        PRIMARY KEY (ApplicantID),
    CONSTRAINT uq_applicant_email  UNIQUE (Email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_applicant_name ON Applicants(ApplicantName(100));


-- ── 2. Tạo bảng Applications ─────────────────────────────────────────────────
-- Quản lý đơn ứng tuyển, kết nối giữa Job và Applicant
CREATE TABLE Applications (
    ApplicationID INT           NOT NULL AUTO_INCREMENT,
    JobID         VARCHAR(50)   NOT NULL,
    ApplicantID   INT           NOT NULL,
    ApplyDate     DATE          NOT NULL,
    Status        ENUM('pending','reviewed','shortlisted','rejected','accepted') 
                                NOT NULL DEFAULT 'pending',
    CoverLetter   TEXT          DEFAULT NULL,
    UpdatedAt     DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_applications  PRIMARY KEY (ApplicationID),
    CONSTRAINT uq_application   UNIQUE (JobID, ApplicantID),
    CONSTRAINT fk_app_job       FOREIGN KEY (JobID) 
        REFERENCES AcademicJobs(JobID) 
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_app_applicant FOREIGN KEY (ApplicantID) 
        REFERENCES Applicants(ApplicantID) 
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_app_status  ON Applications(Status);
CREATE INDEX idx_app_date    ON Applications(ApplyDate);


-- ── 3. Tạo bảng Blogs (Dữ liệu bổ trợ cho portal) ───────────────────────────────
CREATE TABLE Blogs (
    BlogID      INT           NOT NULL AUTO_INCREMENT,
    Title       VARCHAR(500)  NOT NULL,
    AuthorName  VARCHAR(200)  NOT NULL,
    PublishDate DATE          DEFAULT NULL,
    CreatedAt   DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_blogs PRIMARY KEY (BlogID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 4. Tạo bảng News (Tin tức học thuật) ────────────────────────────────────────
CREATE TABLE News (
    NewsID      INT           NOT NULL AUTO_INCREMENT,
    Title       VARCHAR(500)  NOT NULL,
    SourceName  VARCHAR(200)  NOT NULL,
    PublishDate DATE          DEFAULT NULL,
    CreatedAt   DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_news PRIMARY KEY (NewsID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- IMPORT DATA TỪ CSV (SỬ DỤNG ĐƯỜNG DẪN CỦA LUÂN)
-- ============================================================================

-- ── Nạp dữ liệu Applicants ────────────────────────────────────────────────────
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/applicants.csv'
INTO TABLE Applicants
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(ApplicantID, ApplicantName, Email, PhoneNumber, CVLink);

-- ── Nạp dữ liệu Blogs ─────────────────────────────────────────────────────────
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/blogs.csv'
INTO TABLE Blogs
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(BlogID, Title, AuthorName, PublishDate);

-- ── Nạp dữ liệu News ──────────────────────────────────────────────────────────
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/news.csv'
INTO TABLE News
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(NewsID, Title, SourceName, PublishDate);


-- ============================================================================
-- GENERATE APPLICATIONS (KHẮC PHỤC LỖI 1064 BẰNG CÚ PHÁP MYSQL)
-- ============================================================================

-- 1. Tạo bảng tạm để lấy danh sách mã Job thực tế từ dataset
DROP TEMPORARY TABLE IF EXISTS tmp_job_ids;
CREATE TEMPORARY TABLE tmp_job_ids (
    seq    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    JobID  VARCHAR(50) NOT NULL
);

-- Lấy ngẫu nhiên 500 JobID từ bảng AcademicJobs (đã nạp 41.635 dòng)
INSERT INTO tmp_job_ids (JobID)
SELECT JobID FROM AcademicJobs ORDER BY RAND() LIMIT 500;

-- 2. Khởi tạo biến dòng để map dữ liệu
SET @row := 0;

-- 3. Tạo 400 đơn ứng tuyển giả lập cho báo cáo
INSERT INTO Applications (JobID, ApplicantID, ApplyDate, Status, CoverLetter)
SELECT 
    t.JobID,
    a.ApplicantID,
    a.ApplyDate,
    a.Status,
    a.CoverLetter
FROM (
    SELECT 
        (@row := @row + 1) AS rn,
        ap.ApplicantID,
        ((@row - 1) % 500) + 1 AS job_seq,
        -- Sử dụng RAND() chuẩn MySQL để tạo ngày ngẫu nhiên trong vòng 2 năm
        DATE_ADD('2024-01-01', INTERVAL FLOOR(RAND() * 730) DAY) AS ApplyDate,
        -- Ngẫu nhiên chọn 1 trong 5 trạng thái đơn
        ELT(1 + FLOOR(RAND() * 5), 'pending','reviewed','shortlisted','rejected','accepted') AS Status,
        -- Ngẫu nhiên chọn nội dung thư ứng tuyển
        ELT(1 + FLOOR(RAND() * 4), 
            'I am very interested in this position and believe my background aligns well.',
            'With my research experience in this field, I am confident I can contribute.',
            'This opportunity aligns perfectly with my career goals and expertise.',
            'I have extensive experience in this area and am eager to join your team.'
        ) AS CoverLetter
    FROM Applicants ap
    ORDER BY RAND()
    LIMIT 400
) a
JOIN tmp_job_ids t ON t.seq = a.job_seq
ON DUPLICATE KEY UPDATE Status = a.Status;

DROP TEMPORARY TABLE IF EXISTS tmp_job_ids;


-- ============================================================================
-- KIỂM TRA TỔNG KẾT SAU KHI CHẠY
-- ============================================================================
SELECT 'Applicants'   AS Bảng, COUNT(*) AS Số_Dòng FROM Applicants
UNION ALL
SELECT 'Applications', COUNT(*) FROM Applications
UNION ALL
SELECT 'Blogs',        COUNT(*) FROM Blogs
UNION ALL
SELECT 'News',         COUNT(*) FROM News;