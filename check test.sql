-- Xem tất cả đơn vừa nộp, mới nhất trước
SELECT 
    a.ApplicationID,
    a.JobID,
    LEFT(j.JobTitle, 40)   AS JobTitle,
    ap.ApplicantName,
    ap.Email,
    ap.PhoneNumber,
    ap.CVLink,
    a.ApplyDate,
    a.Status,
    a.CoverLetter
FROM Applications a
JOIN Applicants   ap ON a.ApplicantID = ap.ApplicantID
JOIN AcademicJobs j  ON a.JobID       = j.JobID
ORDER BY a.ApplicationID DESC
LIMIT 20;