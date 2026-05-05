-- ============================================================================
--  03_views.sql
--  Views cho Academic Jobs Portal
-- ============================================================================

-- ── 1. Active Jobs ─────────────────────────────────────────────────────────────
-- Tất cả bài đăng còn hiệu lực, kèm tên trường và category
CREATE OR REPLACE VIEW vw_ActiveJobs AS
SELECT
    j.JobID,
    j.JobTitle,
    j.JobDescription,
    e.EmployerName,
    c.CategoryName,
    co.CountryName,
    cn.continent_name       AS Continent,
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
JOIN Continents    cn ON co.continent_code = cn.continent_code
WHERE j.Status = 'active';


-- ── 2. Expired Jobs ────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_ExpiredJobs AS
SELECT
    j.JobID,
    j.JobTitle,
    e.EmployerName,
    c.CategoryName,
    co.CountryName,
    j.PublishDate,
    j.ExpiryDate,
    DATEDIFF(CURDATE(), j.ExpiryDate) AS DaysExpired
FROM AcademicJobs  j
JOIN Employers     e  ON j.EmployerID = e.EmployerID
JOIN JobCategories c  ON j.CategoryID = c.CategoryID
JOIN Countries     co ON j.Country    = co.ID_Country
WHERE j.Status = 'expired';


-- ── 3. Jobs by Country ─────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_JobsByCountry AS
SELECT
    co.CountryName,
    cn.continent_name               AS Continent,
    COUNT(j.JobID)                  AS TotalJobs,
    SUM(j.Status = 'active')        AS ActiveJobs,
    SUM(j.Status = 'expired')       AS ExpiredJobs,
    SUM(j.Status = 'closed')        AS ClosedJobs
FROM AcademicJobs j
JOIN Countries  co ON j.Country         = co.ID_Country
JOIN Continents cn ON co.continent_code = cn.continent_code
GROUP BY co.ID_Country, co.CountryName, cn.continent_name
ORDER BY TotalJobs DESC;


-- ── 4. Employer Posting Summary ────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_EmployerSummary AS
SELECT
    e.EmployerID,
    e.EmployerName,
    co.CountryName,
    COUNT(j.JobID)              AS TotalJobs,
    SUM(j.Status = 'active')    AS ActiveJobs,
    SUM(j.Status = 'expired')   AS ExpiredJobs,
    SUM(j.Status = 'closed')    AS ClosedJobs,
    MIN(j.PublishDate)          AS FirstPosted,
    MAX(j.PublishDate)          AS LastPosted
FROM Employers e
LEFT JOIN AcademicJobs j  ON e.EmployerID = j.EmployerID
LEFT JOIN Countries    co ON e.Country    = co.ID_Country
GROUP BY e.EmployerID, e.EmployerName, co.CountryName
ORDER BY TotalJobs DESC;


-- ── 5. Jobs by Research Area ───────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_JobsByResearchArea AS
SELECT
    ra.ResearchArea,
    COUNT(jra.JobID)            AS TotalJobs,
    SUM(j.Status = 'active')    AS ActiveJobs,
    AVG(jra.Weight)             AS AvgWeight
FROM JobResearchAreas jra
JOIN ResearchAreas    ra ON jra.ID_ResearchArea = ra.ID_ResearchArea
JOIN AcademicJobs     j  ON jra.JobID           = j.JobID
GROUP BY ra.ID_ResearchArea, ra.ResearchArea
ORDER BY TotalJobs DESC;


-- ── 6. Jobs by Category ────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_JobsByCategory AS
SELECT
    c.CategoryName,
    COUNT(jcl.JobID)            AS TotalJobs,
    SUM(j.Status = 'active')    AS ActiveJobs,
    AVG(jcl.Weight)             AS AvgWeight
FROM JobCategoryLinks jcl
JOIN JobCategories    c  ON jcl.CategoryID = c.CategoryID
JOIN AcademicJobs     j  ON jcl.JobID      = j.JobID
GROUP BY c.CategoryID, c.CategoryName
ORDER BY TotalJobs DESC;


-- ── Kiểm tra ───────────────────────────────────────────────────────────────────
SELECT 'vw_ActiveJobs'          AS View_Name, COUNT(*) AS SoDong FROM vw_ActiveJobs
UNION ALL
SELECT 'vw_ExpiredJobs',          COUNT(*) FROM vw_ExpiredJobs
UNION ALL
SELECT 'vw_JobsByCountry',        COUNT(*) FROM vw_JobsByCountry
UNION ALL
SELECT 'vw_EmployerSummary',      COUNT(*) FROM vw_EmployerSummary
UNION ALL
SELECT 'vw_JobsByResearchArea',   COUNT(*) FROM vw_JobsByResearchArea
UNION ALL
SELECT 'vw_JobsByCategory',       COUNT(*) FROM vw_JobsByCategory;
