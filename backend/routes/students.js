const router       = require('express').Router();
const pool         = require('../db/pool');
const authenticate = require('../middleware/authenticate');

// Apply auth to all routes in this file
router.use(authenticate);

// GET /api/students?exam=neet
router.get('/', async (req, res) => {
  try {
    const { role, branch, studentId } = req.user;
    const exam = req.query.exam || 'neet';

    let query, params;

    if (role === 'central') {
      query  = 'SELECT * FROM students WHERE exam_type=$1 ORDER BY student_id';
      params = [exam];
    } else if (role === 'center') {
      query  = 'SELECT * FROM students WHERE exam_type=$1 AND coaching=$2 ORDER BY student_id';
      params = [exam, branch];
    } else {
      // student — return only their own record
      query  = 'SELECT * FROM students WHERE exam_type=$1 AND student_id=$2';
      params = [exam, studentId];
    }

    const { rows } = await pool.query(query, params);
    res.json({ exam_type: exam, students: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

// GET /api/students/:id?exam=neet
router.get('/:id', async (req, res) => {
  try {
    const { role, branch, studentId } = req.user;
    const { id } = req.params;
    const exam   = req.query.exam || 'neet';

    // Students can only fetch themselves
    if (role === 'student' && studentId !== id)
      return res.status(403).json({ error: 'Forbidden' });

    const { rows } = await pool.query(
      'SELECT * FROM students WHERE student_id=$1 AND exam_type=$2',
      [id, exam]
    );
    if (!rows.length) return res.status(404).json({ error: 'Not found' });

    const student = rows[0];

    // Center can only see their own branch
    if (role === 'center' && student.coaching !== branch)
      return res.status(403).json({ error: 'Forbidden' });

    res.json(student);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
