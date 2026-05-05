USE academic_jobs_portal;

-- BƯỚC 1: Tắt kiểm tra khóa ngoại để có thể xóa và nạp dữ liệu nhanh
SET FOREIGN_KEY_CHECKS = 0;

-- BƯỚC 2: Xóa sạch dữ liệu cũ trong tất cả các bảng (Reset về 0 dòng)[cite: 1]
TRUNCATE TABLE JobResearchAreas;
TRUNCATE TABLE JobCategoryLinks;
TRUNCATE TABLE AcademicJobs;
TRUNCATE TABLE ResearchAreas;
TRUNCATE TABLE JobCategories;
TRUNCATE TABLE Employers;
TRUNCATE TABLE Countries;
TRUNCATE TABLE Continents;

-- BƯỚC 3: Nạp lại dữ liệu mới từ các file CSV sạch (Sử dụng Column Mapping)

-- 1. Continents
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_continents_clean.csv'
INTO TABLE Continents FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1, @v2) SET continent_code = @v1, continent_name = @v2;

-- 2. Countries
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_country_clean.csv'
INTO TABLE Countries FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1, @v2, @v3, @v4, @v5, @v6, @v7) SET ID_Country = @v2, CountryName = @v3, continent_code = @v6;

-- 3. Employers (3,053 dòng chuẩn)
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_university_clean.csv'
INTO TABLE Employers FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1, @v2, @v3, @v4, @v5, @v6, @v7, @v8, @v9, @v10, @v11, @v12, @v13, @v14, @v15)
SET EmployerID = @v2, EmployerName = @v3, Country = @v1, Website = @v5;

-- 4. JobCategories
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_positiontype_clean.csv'
INTO TABLE JobCategories FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1, @v2, @v3, @v4) SET CategoryID = @v1, CategoryName = @v2, Description = @v3, SortNumber = @v4;

-- 5. ResearchAreas
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_researcharea_clean.csv'
INTO TABLE ResearchAreas FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1, @v2, @v3) SET ID_ResearchArea = @v1, ResearchArea = @v2, Description = @v3;

-- 6. AcademicJobs (41,635 dòng chuẩn)[cite: 2]
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_positions_clean.csv'
INTO TABLE AcademicJobs FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1,@v2,@v3,@v4,@v5,@v6,@v7,@v8,@v9,@v10,@v11,@v12,@v13,@v14,@v15,@v16,@v17,@v18,@v19,@v20)
SET JobID = @v2, EmployerID = @v5, CategoryID = @v6, Country = @v4, Source = @v3, 
    JobTitle = @v7, JobDescription = @v8, ExpiryDate = @v10, PublishDate = @v11, 
    IsAlive = @v13, FavoriteCount = @v15, JobStatus = @v16, WorkingTime = @v17, 
    Salary = @v18, ContractType = @v19,
    Status = IF(@v13 = 1, 'active', 'expired');

-- 7. JobCategoryLinks
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_job_positiontype_clean.csv'
INTO TABLE JobCategoryLinks FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1, @v2, @v3, @v4) SET JobID = @v1, CategoryID = @v2, Weight = @v3;

-- 8. JobResearchAreas
LOAD DATA LOCAL INFILE 'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql/tbl_positions_researchareas_clean.csv'
INTO TABLE JobResearchAreas FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 ROWS
(@v1, @v2, @v3, @v4, @v5) SET JobID = @v2, ID_ResearchArea = @v1, Weight = @v5;

-- BƯỚC 4: Bật lại kiểm tra khóa ngoại và kiểm tra số lượng dòng[cite: 1]
SET FOREIGN_KEY_CHECKS = 1;

-- Hiển thị báo cáo tổng kết để kiểm tra độ khớp với EDA[cite: 2]
SELECT 'Employers' as TableName, COUNT(*) as Count FROM Employers
UNION ALL
SELECT 'AcademicJobs', COUNT(*) FROM AcademicJobs
UNION ALL
SELECT 'Countries', COUNT(*) FROM Countries
UNION ALL
SELECT 'JobResearchAreas', COUNT(*) FROM JobResearchAreas;