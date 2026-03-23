require('dotenv').config({ path: require('path').join(__dirname, '../../backend/.env') });
const bcrypt = require('bcryptjs');
const pool   = require('./pool');
const fs     = require('fs');
const path   = require('path');

const HASH_ROUNDS = 12;
const PW_BRANCHES = [
  'PW Kota','PW Delhi','PW Patna','PW Lucknow','PW Jaipur','PW Mumbai',
  'PW Hyderabad','PW Kolkata','PW Chennai','PW Pune','PW Ahmedabad','PW Bhopal'
];

async function seed() {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // 1. Central admin
    await client.query(
      `INSERT INTO users(email,password_hash,role) VALUES($1,$2,'central')
       ON CONFLICT(email) DO NOTHING`,
      ['admin@prajna.ai', await bcrypt.hash('admin@2025', HASH_ROUNDS)]
    );

    // 2. Center accounts (one per PW branch)
    for (const branch of PW_BRANCHES) {
      const slug  = branch.toLowerCase().replace('pw ','');
      const email = slug + '@pw.in';
      await client.query(
        `INSERT INTO users(email,password_hash,role,branch_name)
         VALUES($1,$2,'center',$3) ON CONFLICT(email) DO NOTHING`,
        [email, await bcrypt.hash('pw@2025', HASH_ROUNDS), branch]
      );
    }

    // 3. Students from both JSON files
    for (const exam of ['neet','jee']) {
      const filePath = path.join(__dirname,'../../docs/student_summary_'+exam+'.json');
      const data     = JSON.parse(fs.readFileSync(filePath));
      for (const s of data.students) {
        await client.query(
          `INSERT INTO students(student_id,exam_type,name,city,coaching,target,
            abilities,metrics,subjects,chapters,slm_focus,strengths)
           VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
           ON CONFLICT(student_id,exam_type) DO UPDATE SET
             metrics=$8, subjects=$9, chapters=$10, slm_focus=$11, strengths=$12`,
          [s.id, exam, s.name, s.city, s.coaching, s.target,
           JSON.stringify(s.abilities||{}),
           JSON.stringify(s.metrics||{}),
           JSON.stringify(s.subjects||{}),
           JSON.stringify(s.chapters||{}),
           JSON.stringify(s.slm_focus||[]),
           JSON.stringify(s.strengths||[])]
        );
        const email = s.id.toLowerCase() + '@prajna.ai';
        await client.query(
          `INSERT INTO users(email,password_hash,role,student_id,exam_type,branch_name)
           VALUES($1,$2,'student',$3,$4,$5) ON CONFLICT(email) DO NOTHING`,
          [email, await bcrypt.hash('prajna@2025', HASH_ROUNDS), s.id, exam, s.coaching]
        );
      }
      console.log('Seeded ' + data.students.length + ' ' + exam.toUpperCase() + ' students');
    }

    await client.query('COMMIT');
    console.log('Seed complete. Run this against your Railway PostgreSQL database.');
  } catch (e) {
    await client.query('ROLLBACK');
    console.error(e);
  } finally {
    client.release();
    pool.end();
  }
}

seed();
