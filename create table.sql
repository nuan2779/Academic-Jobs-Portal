-- ============================================================================
--  01_create_tables.sql
--  Tạo bảng — chỉ các bảng có data từ AcademicGate dataset
--  MySQL 8.0+
--
--  Thứ tự: Continents → Countries → Employers → JobCategories
--          → ResearchAreas → AcademicJobs → JobCategoryLinks → JobResearchAreas
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS JobResearchAreas;
DROP TABLE IF EXISTS JobCategoryLinks;
DROP TABLE IF EXISTS AcademicJobs;
DROP TABLE IF EXISTS ResearchAreas;
DROP TABLE IF EXISTS JobCategories;
DROP TABLE IF EXISTS Employers;
DROP TABLE IF EXISTS Countries;
DROP TABLE IF EXISTS Continents;

SET FOREIGN_KEY_CHECKS = 1;


-- ── 1. Continents ─────────────────────────────────────────────────────────────
CREATE TABLE Continents (
    continent_code  VARCHAR(10)   NOT NULL,
    continent_name  VARCHAR(100)  NOT NULL,

    CONSTRAINT pk_continents PRIMARY KEY (continent_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 2. Countries ──────────────────────────────────────────────────────────────
CREATE TABLE Countries (
    ID_Country      VARCHAR(20)   NOT NULL,
    CountryName     VARCHAR(200)  NOT NULL,
    continent_code  VARCHAR(10)   DEFAULT NULL,

    CONSTRAINT pk_countries    PRIMARY KEY (ID_Country),
    CONSTRAINT fk_country_cont FOREIGN KEY (continent_code)
        REFERENCES Continents(continent_code)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_countries_continent ON Countries(continent_code);


-- ── 3. Employers  (= tbl_university) ─────────────────────────────────────────
CREATE TABLE Employers (
    EmployerID    VARCHAR(50)   NOT NULL,
    EmployerName  VARCHAR(500)  NOT NULL,
    Country       VARCHAR(20)   DEFAULT NULL,
    Website       VARCHAR(500)  DEFAULT NULL,
    ContactEmail  VARCHAR(200)  DEFAULT NULL,

    CONSTRAINT pk_employers        PRIMARY KEY (EmployerID),
    CONSTRAINT fk_employer_country FOREIGN KEY (Country)
        REFERENCES Countries(ID_Country)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_employers_country ON Employers(Country);
CREATE INDEX idx_employers_name    ON Employers(EmployerName(100));


-- ── 4. JobCategories  (= tbl_positiontype) ───────────────────────────────────
CREATE TABLE JobCategories (
    CategoryID    VARCHAR(50)   NOT NULL,
    CategoryName  VARCHAR(200)  NOT NULL,
    Description   TEXT          DEFAULT NULL,
    SortNumber    INT           DEFAULT NULL,

    CONSTRAINT pk_jobcategories PRIMARY KEY (CategoryID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 5. ResearchAreas  (= tbl_researcharea) ───────────────────────────────────
CREATE TABLE ResearchAreas (
    ID_ResearchArea  VARCHAR(50)   NOT NULL,
    ResearchArea     VARCHAR(200)  NOT NULL,
    Description      TEXT          DEFAULT NULL,

    CONSTRAINT pk_researchareas PRIMARY KEY (ID_ResearchArea)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 6. AcademicJobs  (= tbl_positions) ───────────────────────────────────────
CREATE TABLE AcademicJobs (
    JobID          VARCHAR(50)    NOT NULL,
    EmployerID     VARCHAR(50)    DEFAULT NULL,
    CategoryID     VARCHAR(50)    DEFAULT NULL,
    Country        VARCHAR(20)    DEFAULT NULL,
    Source         VARCHAR(10)    DEFAULT NULL,

    JobTitle       VARCHAR(1000)  NOT NULL DEFAULT '',
    JobDescription longtext           DEFAULT NULL,

    Salary         VARCHAR(500)   DEFAULT NULL,

    PublishDate    DATE           DEFAULT NULL,
    ExpiryDate     DATE           DEFAULT NULL,

    WorkingTime    VARCHAR(50)    DEFAULT NULL,
    ContractType   VARCHAR(50)    DEFAULT NULL,

    Status         ENUM('active','expired','closed') NOT NULL DEFAULT 'active',
    IsAlive        TINYINT(1)     DEFAULT 1,
    JobStatus      TINYINT        DEFAULT 1,
    FavoriteCount  INT            DEFAULT 0,

    CONSTRAINT pk_academicjobs  PRIMARY KEY (JobID),
    CONSTRAINT fk_job_employer  FOREIGN KEY (EmployerID)
        REFERENCES Employers(EmployerID)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_job_category  FOREIGN KEY (CategoryID)
        REFERENCES JobCategories(CategoryID)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_job_country   FOREIGN KEY (Country)
        REFERENCES Countries(ID_Country)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_job_employer   ON AcademicJobs(EmployerID);
CREATE INDEX idx_job_category   ON AcademicJobs(CategoryID);
CREATE INDEX idx_job_country    ON AcademicJobs(Country);
CREATE INDEX idx_job_status     ON AcademicJobs(Status);
CREATE INDEX idx_job_publish    ON AcademicJobs(PublishDate);
CREATE INDEX idx_job_expiry     ON AcademicJobs(ExpiryDate);
CREATE FULLTEXT INDEX idx_job_title_ft ON AcademicJobs(JobTitle);


-- ── 7. JobCategoryLinks  (= tbl_job_positiontype) ────────────────────────────
CREATE TABLE JobCategoryLinks (
    JobID       VARCHAR(50)  NOT NULL,
    CategoryID  VARCHAR(50)  NOT NULL,
    Weight      FLOAT        DEFAULT NULL,

    CONSTRAINT pk_jobcategorylinks PRIMARY KEY (JobID, CategoryID),
    CONSTRAINT fk_jcl_job          FOREIGN KEY (JobID)
        REFERENCES AcademicJobs(JobID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_jcl_category     FOREIGN KEY (CategoryID)
        REFERENCES JobCategories(CategoryID)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_jcl_job      ON JobCategoryLinks(JobID);
CREATE INDEX idx_jcl_category ON JobCategoryLinks(CategoryID);


-- ── 8. JobResearchAreas  (= tbl_positions_researchareas) ─────────────────────
CREATE TABLE JobResearchAreas (
    JobID            VARCHAR(50)  NOT NULL,
    ID_ResearchArea  VARCHAR(50)  NOT NULL,
    Weight           FLOAT        DEFAULT NULL,

    CONSTRAINT pk_jobresearchareas PRIMARY KEY (JobID, ID_ResearchArea),
    CONSTRAINT fk_jra_job          FOREIGN KEY (JobID)
        REFERENCES AcademicJobs(JobID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_jra_researcharea FOREIGN KEY (ID_ResearchArea)
        REFERENCES ResearchAreas(ID_ResearchArea)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_jra_job          ON JobResearchAreas(JobID);
CREATE INDEX idx_jra_researcharea ON JobResearchAreas(ID_ResearchArea);