const router       = require('express').Router();
const pool         = require('../db/pool');
const authenticate = require('../middleware/authenticate');
const authorize    = require('../middleware/authorize');

router.use(authenticate);
router.use(authorize('central', 'center'));

// GET /api/branches?exam=neet
router.get('/', async (req, res) => {
  try {
    const { role, branch } = req.user;
    const exam = req.query.exam || 'neet';

    const where  = role === 'center' ? 'AND coaching=$2' : '';
    const params = role === 'center' ? [exam, branch] : [exam];

    const { rows } = await pool.query(
      `SELECT coaching AS branch,
              COUNT(*)::int AS count,
              ROUND(AVG((metrics->>'avg_percentage')::numeric),1) AS avg_score,
              ROUND(AVG((metrics->>'improvement')::numeric),1)    AS avg_improvement,
              SUM(CASE WHEN (metrics->>'avg_percentage')::numeric < 25
                  THEN 1 ELSE 0 END)::int                        AS at_risk
       FROM students
       WHERE exam_type=$1 ${where}
       GROUP BY coaching
       ORDER BY coaching`,
      params
    );
    res.json({ branches: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
