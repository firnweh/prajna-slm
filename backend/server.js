require('dotenv').config();
const express = require('express');
const cors    = require('cors');
const path    = require('path');

const app = express();
app.use(cors({ origin: process.env.FRONTEND_ORIGIN || '*' }));
app.use(express.json());

// Serve static front-end files
app.use(express.static(path.join(__dirname, '../docs')));

// Routes (added in later tasks)
app.use('/api/auth',     require('./routes/auth'));
app.use('/api/students', require('./routes/students'));
app.use('/api/branches', require('./routes/branches'));

// Catch-all → login
app.get('/{*path}', (_req, res) =>
  res.sendFile(path.join(__dirname, '../docs/login.html')));

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`PRAJNA API on :${PORT}`));
