-- SwipeHire schema. Run by init_db.py on every start; every statement is
-- idempotent (IF NOT EXISTS), so it never touches existing data.
-- Statements are split on ";" + newline, so do not put ";" inside comments.

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('seeker', 'employer', 'admin') NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL
);

-- One row per job seeker. The filter columns (min_compensation, job_type,
-- schedule) decide which job cards the seeker sees on the Homepage.
CREATE TABLE IF NOT EXISTS seeker_profiles (
    user_id          INT PRIMARY KEY,
    full_name        VARCHAR(120) NOT NULL DEFAULT '',
    phone            VARCHAR(40)  NOT NULL DEFAULT '',
    contact_email    VARCHAR(255) NOT NULL DEFAULT '',
    resume_file      VARCHAR(255) NULL,
    resume_name      VARCHAR(255) NULL,
    photo_file       VARCHAR(255) NULL,
    preferred_title  VARCHAR(120) NOT NULL DEFAULT '',
    min_compensation INT NULL,
    job_type         ENUM('any', 'remote', 'hybrid', 'in_person') NOT NULL DEFAULT 'any',
    commute_miles    INT NULL,
    schedule         ENUM('any', 'full_time', 'part_time') NOT NULL DEFAULT 'any',
    certifications   TEXT NULL,
    about            TEXT NULL,
    CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- One company per employer account.
CREATE TABLE IF NOT EXISTS companies (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL UNIQUE,
    name          VARCHAR(120) NOT NULL,
    description   TEXT NULL,
    contact_email VARCHAR(255) NOT NULL DEFAULT '',
    website       VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT fk_company_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS jobs (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    company_id       INT NOT NULL,
    title            VARCHAR(120) NOT NULL,
    location         VARCHAR(120) NOT NULL DEFAULT '',
    job_type         ENUM('remote', 'hybrid', 'in_person') NOT NULL,
    schedule         ENUM('full_time', 'part_time') NOT NULL,
    responsibilities TEXT NOT NULL,
    requirements     TEXT NOT NULL,
    pay_min          INT NOT NULL,
    pay_max          INT NOT NULL,
    pay_period       ENUM('year', 'hour') NOT NULL DEFAULT 'year',
    is_open          TINYINT(1) NOT NULL DEFAULT 1,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_job_company FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
    CONSTRAINT chk_pay CHECK (pay_min >= 0 AND pay_max >= pay_min)
);

-- Seeker swiped on a job card. liked = 1 sends the profile to the employer.
CREATE TABLE IF NOT EXISTS seeker_swipes (
    seeker_id  INT NOT NULL,
    job_id     INT NOT NULL,
    liked      TINYINT(1) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (seeker_id, job_id),
    CONSTRAINT fk_ss_seeker FOREIGN KEY (seeker_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_ss_job    FOREIGN KEY (job_id)    REFERENCES jobs (id)  ON DELETE CASCADE
);

-- Employer swiped on an applicant card (only seekers who liked that job).
-- A match = both rows exist with liked = 1.
CREATE TABLE IF NOT EXISTS employer_swipes (
    job_id     INT NOT NULL,
    seeker_id  INT NOT NULL,
    liked      TINYINT(1) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (job_id, seeker_id),
    CONSTRAINT fk_es_job    FOREIGN KEY (job_id)    REFERENCES jobs (id)  ON DELETE CASCADE,
    CONSTRAINT fk_es_seeker FOREIGN KEY (seeker_id) REFERENCES users (id) ON DELETE CASCADE
);
