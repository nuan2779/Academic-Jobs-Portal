-- ============================================================================
--  06_triggers.sql
--  Triggers cho Academic Jobs Portal (Maintenance Mode Enabled)
-- ============================================================================

DELIMITER $$

-- ── TRIGGER 1: Tự động kiểm tra trạng thái khi INSERT ────────────────────────
-- Mục tiêu: Ngăn chặn việc nạp các Job đã hết hạn vào hệ thống.
DROP TRIGGER IF EXISTS trg_SetJobStatus_Insert$$
CREATE TRIGGER trg_SetJobStatus_Insert
BEFORE INSERT ON AcademicJobs
FOR EACH ROW
BEGIN
    -- Chỉ thực hiện nếu không ở chế độ bảo trì (@disable_triggers IS NULL)
    IF @disable_triggers IS NULL THEN
        IF NEW.ExpiryDate IS NOT NULL AND NEW.ExpiryDate < CURDATE() THEN
            SET NEW.Status  = 'expired';
            SET NEW.IsAlive = 0;
        END IF;
    END IF;
END$$


-- ── TRIGGER 2: Quản lý vòng đời và đồng bộ dữ liệu khi UPDATE ────────────────
-- Mục tiêu: Tự động hóa việc chuyển trạng thái và đồng bộ các cờ hệ thống.
DROP TRIGGER IF EXISTS trg_SetJobStatus_Update$$
CREATE TRIGGER trg_SetJobStatus_Update
BEFORE UPDATE ON AcademicJobs
FOR EACH ROW
BEGIN
    -- Kiểm tra công tắc vô hiệu hóa Trigger
    IF @disable_triggers IS NULL THEN
        
        -- 1. Tự động chuyển sang 'expired' nếu ExpiryDate bị kéo về quá khứ
        IF NEW.ExpiryDate IS NOT NULL
           AND NEW.ExpiryDate < CURDATE()
           AND NEW.Status != 'closed' THEN
            SET NEW.Status  = 'expired';
            SET NEW.IsAlive = 0;
        END IF;

        -- 2. Đồng bộ IsAlive và JobStatus khi đóng bài đăng (closed)
        IF NEW.Status = 'closed' THEN
            SET NEW.IsAlive   = 0;
            SET NEW.JobStatus = 9;
        END IF;

        -- 3. Đồng bộ khi mở lại bài đăng (active)
        IF NEW.Status = 'active' THEN
            SET NEW.IsAlive   = 1;
            SET NEW.JobStatus = 1;
        END IF;
        
    END IF;
END$$


-- ── TRIGGER 3: Ghi nhật ký thay đổi trạng thái (Audit Log) ────────────────────
-- Tạo bảng log nếu chưa có
CREATE TABLE IF NOT EXISTS JobStatusLog (
    LogID       INT          NOT NULL AUTO_INCREMENT,
    JobID       VARCHAR(50)  NOT NULL,
    OldStatus   VARCHAR(20)  DEFAULT NULL,
    NewStatus   VARCHAR(20)  NOT NULL,
    ChangedAt   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_jobstatuslog PRIMARY KEY (LogID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci$$

DROP TRIGGER IF EXISTS trg_LogJobStatusChange$$
CREATE TRIGGER trg_LogJobStatusChange
AFTER UPDATE ON AcademicJobs
FOR EACH ROW
BEGIN
    -- Ghi log ngay cả khi đang bảo trì (hoặc thêm IF @disable_triggers IS NULL nếu muốn)
    IF OLD.Status != NEW.Status THEN
        INSERT INTO JobStatusLog (JobID, OldStatus, NewStatus, ChangedAt)
        VALUES (NEW.JobID, OLD.Status, NEW.Status, NOW());
    END IF;
END$$

DELIMITER ;

-- ── HƯỚNG DẪN SỬ DỤNG "CÔNG TẮC" @disable_triggers ────────────────────────────
-- 1. Để hồi sinh Job cũ mà không bị Trigger quét:
--    SET @disable_triggers = 1;
--    UPDATE AcademicJobs SET Status = 'active' WHERE ...;
--    SET @disable_triggers = NULL;

-- 2. Kiểm tra trạng thái hiện tại:
SELECT 'Triggers consolidated successfully!' AS Status;