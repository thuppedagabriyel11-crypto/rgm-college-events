CREATE DATABASE IF NOT EXISTS rgm_events CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- The Flask application creates the tables and indexes through SQLAlchemy.
-- This file documents the intended MariaDB structure for manual inspection.

CREATE TABLE IF NOT EXISTS user (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(160) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL DEFAULT 'student',
  student_id VARCHAR(80) UNIQUE NULL,
  department VARCHAR(120) NULL,
  year VARCHAR(40) NULL,
  phone VARCHAR(40) NULL,
  active BOOLEAN DEFAULT TRUE,
  created_at DATETIME NULL
);

CREATE TABLE IF NOT EXISTS event (
  id INT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  category VARCHAR(100) NOT NULL DEFAULT 'General',
  description TEXT NOT NULL,
  event_date DATE NOT NULL,
  start_time VARCHAR(20) NOT NULL,
  end_time VARCHAR(20) NOT NULL,
  venue VARCHAR(200) NOT NULL,
  registration_start DATE NOT NULL,
  registration_deadline DATE NOT NULL,
  max_participants INT NOT NULL DEFAULT 100,
  rules TEXT NULL,
  organizer_id INT NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  banner VARCHAR(255) NULL,
  fee_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  fee_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
  payment_type VARCHAR(20) NOT NULL DEFAULT 'test',
  payment_upi_id VARCHAR(160) NULL,
  payment_qr VARCHAR(255) NULL,
  payment_note TEXT NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  CONSTRAINT fk_event_organizer FOREIGN KEY (organizer_id) REFERENCES user(id)
);

CREATE TABLE IF NOT EXISTS registration (
  id INT PRIMARY KEY AUTO_INCREMENT,
  registration_code VARCHAR(60) NOT NULL UNIQUE,
  event_id INT NOT NULL,
  student_id INT NOT NULL,
  status VARCHAR(30) DEFAULT 'registered',
  payment_status VARCHAR(30) NOT NULL DEFAULT 'not_required',
  payment_reference VARCHAR(100) UNIQUE NULL,
  payment_paid_at DATETIME NULL,
  receipt_file_name VARCHAR(255) NULL,
  registered_at DATETIME NULL,
  CONSTRAINT fk_reg_event FOREIGN KEY (event_id) REFERENCES event(id),
  CONSTRAINT fk_reg_student FOREIGN KEY (student_id) REFERENCES user(id),
  CONSTRAINT uq_event_student UNIQUE (event_id, student_id)
);

CREATE TABLE IF NOT EXISTS attendance (
  id INT PRIMARY KEY AUTO_INCREMENT,
  event_id INT NOT NULL,
  student_id INT NOT NULL,
  status VARCHAR(30) DEFAULT 'not_marked',
  marked_at DATETIME NULL,
  marked_by INT NULL,
  CONSTRAINT fk_att_event FOREIGN KEY (event_id) REFERENCES event(id),
  CONSTRAINT fk_att_student FOREIGN KEY (student_id) REFERENCES user(id),
  CONSTRAINT fk_att_marker FOREIGN KEY (marked_by) REFERENCES user(id),
  CONSTRAINT uq_att_event_student UNIQUE (event_id, student_id)
);

CREATE TABLE IF NOT EXISTS announcement (
  id INT PRIMARY KEY AUTO_INCREMENT,
  event_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  message TEXT NOT NULL,
  created_by INT NOT NULL,
  created_at DATETIME NULL,
  FOREIGN KEY (event_id) REFERENCES event(id),
  FOREIGN KEY (created_by) REFERENCES user(id)
);

CREATE TABLE IF NOT EXISTS certificate (
  id INT PRIMARY KEY AUTO_INCREMENT,
  certificate_number VARCHAR(80) NOT NULL UNIQUE,
  verification_code VARCHAR(120) NOT NULL UNIQUE,
  event_id INT NOT NULL,
  student_id INT NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  issue_date DATE NOT NULL,
  status VARCHAR(30) DEFAULT 'issued',
  created_at DATETIME NULL,
  FOREIGN KEY (event_id) REFERENCES event(id),
  FOREIGN KEY (student_id) REFERENCES user(id),
  CONSTRAINT uq_cert_event_student UNIQUE (event_id, student_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NULL,
  action VARCHAR(200) NOT NULL,
  resource VARCHAR(120) NULL,
  resource_id VARCHAR(80) NULL,
  created_at DATETIME NULL,
  FOREIGN KEY (user_id) REFERENCES user(id)
);
