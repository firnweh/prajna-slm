CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('central','center','student')),
  branch_name   TEXT,
  student_id    TEXT,
  exam_type     TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS students (
  id          SERIAL PRIMARY KEY,
  student_id  TEXT NOT NULL,
  exam_type   TEXT NOT NULL,
  name        TEXT,
  city        TEXT,
  coaching    TEXT,
  target      TEXT,
  abilities   JSONB,
  metrics     JSONB,
  subjects    JSONB,
  chapters    JSONB,
  slm_focus   JSONB,
  strengths   JSONB,
  UNIQUE(student_id, exam_type)
);

CREATE INDEX IF NOT EXISTS idx_students_coaching  ON students(coaching);
CREATE INDEX IF NOT EXISTS idx_students_exam_type ON students(exam_type);
CREATE INDEX IF NOT EXISTS idx_users_email        ON users(email);
