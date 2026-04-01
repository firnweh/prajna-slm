# PRAJNA Portal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a unified Next.js App Router portal that combines student, org, and prediction dashboards with role-based routing, consuming existing Node.js and Python backends.

**Architecture:** Next.js 14 App Router with Tailwind + shadcn/ui. JWT auth stored in httpOnly cookies via Next.js API route. Zustand for client state. TanStack Query for data fetching. Streamlit embedded via iframe for heavy analysis tabs.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts, Zustand, TanStack Query

**Design doc:** `/Users/aman/exam-predictor/docs/plans/2026-04-01-prajna-portal-design.md`

**Backend URLs (env vars):**
- `NEXT_PUBLIC_BACKEND_URL` = `https://web-production-4ef64.up.railway.app`
- `NEXT_PUBLIC_INTEL_URL` = Intelligence API URL (Railway)
- `NEXT_PUBLIC_STREAMLIT_URL` = Streamlit URL (Railway)

---

### Task 1: Scaffold Next.js Project

**Files:**
- Create: `/Users/aman/prajna-portal/` (new repo)

**Step 1: Create the project**

```bash
cd /Users/aman
npx create-next-app@latest prajna-portal --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

**Step 2: Initialize git and install dependencies**

```bash
cd /Users/aman/prajna-portal
npm install zustand @tanstack/react-query recharts
npx shadcn@latest init --defaults
npx shadcn@latest add card badge table collapsible dropdown-menu tabs button input label separator
```

**Step 3: Create .env.local**

Create `/Users/aman/prajna-portal/.env.local`:
```
NEXT_PUBLIC_BACKEND_URL=https://web-production-4ef64.up.railway.app
NEXT_PUBLIC_INTEL_URL=http://localhost:8001
NEXT_PUBLIC_STREAMLIT_URL=http://localhost:8501
```

**Step 4: Set up dark theme in tailwind.config.ts**

Extend the tailwind config with PRAJNA color tokens:
```typescript
// tailwind.config.ts
const config = {
  // ... existing shadcn config
  theme: {
    extend: {
      colors: {
        prajna: {
          bg: '#0f0f1a',
          surface: '#131320',
          card: '#1a1d2e',
          border: '#1e1e3a',
          accent: '#6366f1',
          teal: '#00d4aa',
          warn: '#ff6b6b',
          gold: '#ffd166',
          text: '#e2e8f0',
          muted: '#64748b',
        },
        subject: {
          physics: '#f59e0b',
          chemistry: '#6366f1',
          biology: '#22c55e',
          mathematics: '#a855f7',
          botany: '#22c55e',
          zoology: '#10b981',
        },
      },
    },
  },
};
```

**Step 5: Set dark background in app/globals.css**

Add to globals.css after the tailwind directives:
```css
body {
  background-color: #0f0f1a;
  color: #e2e8f0;
}
```

**Step 6: Verify dev server starts**

```bash
cd /Users/aman/prajna-portal && npm run dev
```
Open http://localhost:3000 — should show Next.js default page with dark background.

**Step 7: Commit**

```bash
git add -A && git commit -m "chore: scaffold Next.js project with Tailwind, shadcn/ui, Zustand, Recharts"
```

---

### Task 2: API Layer + Auth Store

**Files:**
- Create: `lib/api.ts`
- Create: `lib/store.ts`
- Create: `lib/types.ts`
- Create: `app/api/auth/route.ts`

**Step 1: Create types**

Create `lib/types.ts`:
```typescript
export interface User {
  userId: string;
  role: 'student' | 'center' | 'central';
  branch: string | null;
  studentId: string | null;
  exam: string | null;
}

export interface StudentRecord {
  id: string;
  name: string;
  coaching: string;
  city: string;
  target: string;
  metrics: {
    avg_percentage: number;
    best_percentage: number;
    improvement: number;
    consistency_score: number;
    latest_percentage: number;
    trajectory: number[];
  };
  subjects: Record<string, { acc: number }>;
  chapters: Record<string, [number, string, number]>; // [accuracy, level, count]
}

export interface Prediction {
  chapter: string;
  subject: string;
  micro_topic?: string;
  appearance_probability: number;
  expected_questions: number;
  confidence_score: number;
  trend_direction: string;
  signal_breakdown?: Record<string, number>;
  reasons?: string[];
  syllabus_status?: string;
}

export interface BranchStat {
  branch: string;
  count: number;
  avg_score: number;
  avg_improvement: number;
  at_risk: number;
}
```

**Step 2: Create API helpers**

Create `lib/api.ts`:
```typescript
function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('prajna_token='))
    ?.split('=')[1] ?? null;
}

async function fetchWithAuth(url: string, opts: RequestInit = {}) {
  const token = getToken();
  const res = await fetch(url, {
    ...opts,
    headers: {
      ...opts.headers,
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401 && typeof window !== 'undefined') {
    document.cookie = 'prajna_token=; Max-Age=0; path=/';
    window.location.href = '/login';
  }
  return res;
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || '';
const INTEL = process.env.NEXT_PUBLIC_INTEL_URL || '';

export const backend = (path: string, opts?: RequestInit) =>
  fetchWithAuth(`${BACKEND}${path}`, opts);

export const intelligence = (path: string, opts?: RequestInit) =>
  fetchWithAuth(`${INTEL}${path}`, opts);
```

**Step 3: Create Zustand store**

Create `lib/store.ts`:
```typescript
import { create } from 'zustand';
import type { User, Prediction } from './types';

interface PrajnaStore {
  user: User | null;
  exam: 'neet' | 'jee';
  year: number;
  microPreds: Prediction[];
  setUser: (u: User | null) => void;
  setExam: (e: 'neet' | 'jee') => void;
  setYear: (y: number) => void;
  setMicroPreds: (p: Prediction[]) => void;
}

export const useStore = create<PrajnaStore>((set) => ({
  user: null,
  exam: 'neet',
  year: 2026,
  microPreds: [],
  setUser: (user) => set({ user }),
  setExam: (exam) => set({ exam, microPreds: [] }),
  setYear: (year) => set({ year }),
  setMicroPreds: (microPreds) => set({ microPreds }),
}));
```

**Step 4: Create auth API route (cookie handler)**

Create `app/api/auth/route.ts`:
```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const body = await req.json();
  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || '';

  const res = await fetch(`${BACKEND}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await res.json();
  if (!res.ok) return NextResponse.json(data, { status: res.status });

  const response = NextResponse.json(data);
  response.cookies.set('prajna_token', data.token, {
    httpOnly: false, // client needs to read for API calls
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 8, // 8 hours
    path: '/',
  });
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete('prajna_token');
  return response;
}
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: API layer, Zustand store, auth cookie handler, TypeScript types"
```

---

### Task 3: Middleware + Login Page

**Files:**
- Create: `middleware.ts`
- Create: `app/login/page.tsx`

**Step 1: Create auth middleware**

Create `middleware.ts` at project root:
```typescript
import { NextRequest, NextResponse } from 'next/server';

function parseJWT(token: string) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return null;
  }
}

export function middleware(req: NextRequest) {
  const token = req.cookies.get('prajna_token')?.value;
  const path = req.nextUrl.pathname;

  // Public routes
  if (path === '/login' || path.startsWith('/api/') || path.startsWith('/_next/')) {
    // If logged in and visiting /login, redirect to home
    if (path === '/login' && token) {
      const payload = parseJWT(token);
      if (payload && payload.exp * 1000 > Date.now()) {
        const home = payload.role === 'student' ? '/student' : '/org';
        return NextResponse.redirect(new URL(home, req.url));
      }
    }
    return NextResponse.next();
  }

  // No token -> login
  if (!token) {
    return NextResponse.redirect(new URL('/login', req.url));
  }

  const payload = parseJWT(token);
  if (!payload || payload.exp * 1000 < Date.now()) {
    const response = NextResponse.redirect(new URL('/login', req.url));
    response.cookies.delete('prajna_token');
    return response;
  }

  // Role-based access
  const role = payload.role;
  if (path.startsWith('/student') && role !== 'student') {
    return NextResponse.redirect(new URL('/org', req.url));
  }
  if (path.startsWith('/org') && role === 'student') {
    return NextResponse.redirect(new URL('/student', req.url));
  }

  // Root redirect
  if (path === '/') {
    const home = role === 'student' ? '/student' : '/org';
    return NextResponse.redirect(new URL(home, req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

**Step 2: Create login page**

Create `app/login/page.tsx`:
```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Login failed');
        return;
      }
      // JWT is set as cookie by the API route
      const role = data.user?.role;
      router.push(role === 'student' ? '/student' : '/org');
    } catch {
      setError('Cannot connect to server');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-prajna-bg">
      <Card className="w-full max-w-md p-8 bg-prajna-card border-prajna-border">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-prajna-accent">PRAJNA</h1>
          <p className="text-sm text-prajna-muted mt-1">
            Predictive Resource Allocation for JEE/NEET Aspirants
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <Label htmlFor="email" className="text-prajna-muted text-xs uppercase tracking-wider">Email</Label>
            <Input
              id="email" type="email" value={email}
              onChange={e => setEmail(e.target.value)}
              className="bg-prajna-surface border-prajna-border text-prajna-text mt-1"
              placeholder="student@pw.live"
              required
            />
          </div>
          <div>
            <Label htmlFor="password" className="text-prajna-muted text-xs uppercase tracking-wider">Password</Label>
            <Input
              id="password" type="password" value={password}
              onChange={e => setPassword(e.target.value)}
              className="bg-prajna-surface border-prajna-border text-prajna-text mt-1"
              placeholder="Enter password"
              required
            />
          </div>
          {error && <p className="text-prajna-warn text-sm">{error}</p>}
          <Button
            type="submit" disabled={loading}
            className="w-full bg-prajna-accent hover:bg-prajna-accent/90 text-white font-semibold"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
```

**Step 3: Verify login page renders**

Run: `npm run dev`, open http://localhost:3000/login
Expected: Dark login card with PRAJNA branding, email/password fields, sign in button.

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: auth middleware with role-based routing + login page"
```

---

### Task 4: Layout Shell + Sidebar

**Files:**
- Create: `components/layout/Sidebar.tsx`
- Create: `components/layout/Header.tsx`
- Create: `app/student/layout.tsx`
- Create: `app/org/layout.tsx`
- Create: `lib/nav-config.ts`

**Step 1: Create nav config**

Create `lib/nav-config.ts`:
```typescript
export interface NavItem {
  label: string;
  href: string;
  icon: string;
}

export const studentNav: NavItem[] = [
  { label: 'My Dashboard', href: '/student', icon: '📊' },
  { label: 'Predictions', href: '/predictions', icon: '🔮' },
  { label: 'Lesson Plan', href: '/predictions?tab=lesson', icon: '📚' },
  { label: 'Mistake Analysis', href: '/predictions?tab=mistakes', icon: '🧪' },
  { label: 'Deep Analysis', href: '/analysis', icon: '🔬' },
];

export const orgNav: NavItem[] = [
  { label: 'Organisation', href: '/org', icon: '📊' },
  { label: 'Predictions', href: '/predictions', icon: '🔮' },
  { label: 'Lesson Plan', href: '/predictions?tab=lesson', icon: '📚' },
  { label: 'Mistake Analysis', href: '/predictions?tab=mistakes', icon: '🧪' },
  { label: 'Deep Analysis', href: '/analysis', icon: '🔬' },
];

// Subject links are added dynamically in the sidebar based on exam type
export function getSubjectLinks(exam: 'neet' | 'jee'): NavItem[] {
  if (exam === 'jee') {
    return [
      { label: 'Physics', href: '/student/physics', icon: '⚡' },
      { label: 'Chemistry', href: '/student/chemistry', icon: '🧪' },
      { label: 'Mathematics', href: '/student/mathematics', icon: '📐' },
    ];
  }
  return [
    { label: 'Physics', href: '/student/physics', icon: '⚡' },
    { label: 'Chemistry', href: '/student/chemistry', icon: '🧪' },
    { label: 'Biology', href: '/student/biology', icon: '🧬' },
  ];
}
```

**Step 2: Create Sidebar component**

Create `components/layout/Sidebar.tsx`:
```tsx
'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { NavItem, studentNav, orgNav, getSubjectLinks } from '@/lib/nav-config';
import { Separator } from '@/components/ui/separator';

function NavLink({ item }: { item: NavItem }) {
  const path = usePathname();
  const active = path === item.href || (item.href !== '/' && path.startsWith(item.href.split('?')[0]));

  return (
    <Link
      href={item.href}
      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
        active
          ? 'bg-prajna-accent/12 text-prajna-accent font-semibold'
          : 'text-prajna-muted hover:text-prajna-text hover:bg-white/[0.03]'
      }`}
    >
      <span>{item.icon}</span>
      <span>{item.label}</span>
    </Link>
  );
}

export function Sidebar({ role }: { role: 'student' | 'center' | 'central' }) {
  const { exam, year, user } = useStore();
  const router = useRouter();
  const isStudent = role === 'student';
  const mainNav = isStudent ? studentNav : orgNav;
  const subjectLinks = isStudent ? getSubjectLinks(exam) : [];

  async function handleLogout() {
    await fetch('/api/auth', { method: 'DELETE' });
    router.push('/login');
  }

  return (
    <aside className="w-[260px] min-h-screen bg-prajna-surface border-r border-prajna-border flex flex-col shrink-0">
      <div className="p-4">
        <h1 className="text-lg font-bold text-prajna-accent">PRAJNA</h1>
        <p className="text-xs text-prajna-muted italic mt-0.5">
          Predictive Resource Allocation for JEE/NEET Aspirants
        </p>
      </div>

      <Separator className="bg-prajna-border" />

      <nav className="flex-1 p-3 space-y-1">
        {mainNav.map(item => <NavLink key={item.href} item={item} />)}

        {subjectLinks.length > 0 && (
          <>
            <Separator className="bg-prajna-border my-3" />
            <p className="text-[0.65rem] font-bold uppercase tracking-widest text-prajna-muted px-3 mb-1">
              Subjects
            </p>
            {subjectLinks.map(item => <NavLink key={item.href} item={item} />)}
          </>
        )}
      </nav>

      <Separator className="bg-prajna-border" />

      <div className="p-4 space-y-2">
        <p className="text-xs text-prajna-muted">
          {exam.toUpperCase()} · {year}
        </p>
        {user && (
          <p className="text-xs text-prajna-text truncate">{user.userId}</p>
        )}
        <button
          onClick={handleLogout}
          className="text-xs text-prajna-muted hover:text-prajna-warn transition-colors"
        >
          Sign Out
        </button>
      </div>
    </aside>
  );
}
```

**Step 3: Create Header component**

Create `components/layout/Header.tsx`:
```tsx
'use client';

import { useStore } from '@/lib/store';

export function Header({ title }: { title: string }) {
  const { exam, setExam } = useStore();

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-prajna-border bg-prajna-surface sticky top-0 z-50">
      <h2 className="text-sm font-bold text-prajna-text tracking-wide">{title}</h2>
      <div className="flex border border-prajna-border rounded-lg overflow-hidden">
        <button
          onClick={() => setExam('neet')}
          className={`px-3 py-1 text-xs font-bold tracking-wider transition-colors ${
            exam === 'neet' ? 'bg-prajna-accent text-white' : 'text-prajna-muted hover:text-prajna-text'
          }`}
        >
          NEET
        </button>
        <button
          onClick={() => setExam('jee')}
          className={`px-3 py-1 text-xs font-bold tracking-wider transition-colors ${
            exam === 'jee' ? 'bg-prajna-accent text-white' : 'text-prajna-muted hover:text-prajna-text'
          }`}
        >
          JEE
        </button>
      </div>
    </header>
  );
}
```

**Step 4: Create student layout**

Create `app/student/layout.tsx`:
```tsx
import { Sidebar } from '@/components/layout/Sidebar';

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-prajna-bg">
      <Sidebar role="student" />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
```

**Step 5: Create org layout**

Create `app/org/layout.tsx`:
```tsx
import { Sidebar } from '@/components/layout/Sidebar';

export default function OrgLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-prajna-bg">
      <Sidebar role="central" />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
```

**Step 6: Create placeholder pages**

Create `app/student/page.tsx`:
```tsx
import { Header } from '@/components/layout/Header';

export default function StudentDashboard() {
  return (
    <>
      <Header title="PRAJNA · Student Dashboard" />
      <div className="p-6">
        <p className="text-prajna-muted">Student dashboard loading...</p>
      </div>
    </>
  );
}
```

Create `app/org/page.tsx`:
```tsx
import { Header } from '@/components/layout/Header';

export default function OrgDashboard() {
  return (
    <>
      <Header title="PRAJNA · Organisation Dashboard" />
      <div className="p-6">
        <p className="text-prajna-muted">Org dashboard loading...</p>
      </div>
    </>
  );
}
```

**Step 7: Verify layout renders**

Open http://localhost:3000/login, login, verify redirect to /student or /org with sidebar visible.

**Step 8: Commit**

```bash
git add -A && git commit -m "feat: sidebar navigation + role-based layouts for student and org"
```

---

### Task 5: Reusable Dashboard Components

**Files:**
- Create: `components/dashboard/KpiCard.tsx`
- Create: `components/dashboard/KpiStrip.tsx`
- Create: `components/dashboard/SubjectCard.tsx`
- Create: `components/dashboard/ZoneBadge.tsx`
- Create: `components/dashboard/RoiBadge.tsx`
- Create: `components/dashboard/ChapterRow.tsx`
- Create: `components/dashboard/MicroTopicTable.tsx`

These are presentational components. Each takes typed props and renders styled UI. No data fetching.

**KpiCard:** Displays a single metric (value, label, subtitle, accent color, optional trend arrow).
**KpiStrip:** Row of KpiCards with responsive grid.
**SubjectCard:** Clickable card showing subject name, student accuracy, PRAJNA exam load, critical count, "Explore" link.
**ZoneBadge:** Small colored badge for M/S/D/W/C levels.
**RoiBadge:** CRITICAL (red) / FOCUS (amber) / REVIEW (blue) / OK (green) badge.
**ChapterRow:** Collapsible `<details>` with chapter header (name, student acc, PRAJNA prob, trend) and MicroTopicTable inside.
**MicroTopicTable:** Table rows: micro-topic name | student % | PRAJNA % | ROI badge.

Implement each as a small functional component with Tailwind classes matching the PRAJNA dark theme. Use shadcn `Card`, `Badge`, `Collapsible` where appropriate.

**Commit:** `feat: reusable dashboard components — KPI, subject cards, chapter rows, badges`

---

### Task 6: Student Dashboard Page

**Files:**
- Modify: `app/student/page.tsx`
- Create: `lib/hooks/useStudentData.ts`

**Step 1: Create data hook**

Create `lib/hooks/useStudentData.ts`:
```typescript
'use client';

import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { backend, intelligence } from '@/lib/api';
import type { StudentRecord, Prediction } from '@/lib/types';

export function useStudentData() {
  const { exam, user, microPreds, setMicroPreds } = useStore();
  const [student, setStudent] = useState<StudentRecord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        // Load student record
        const sRes = await backend(`/api/students?exam=${exam}`);
        const sData = await sRes.json();
        const students = sData.students || [];
        const me = user?.studentId
          ? students.find((s: StudentRecord) => s.id === user.studentId)
          : students[0];
        setStudent(me || null);

        // Load micro predictions if not cached
        if (!microPreds.length) {
          const examType = exam === 'jee' ? 'jee_main' : 'neet';
          const pRes = await intelligence(
            `/api/v1/data/predict?exam_type=${examType}&year=2026&level=micro&top_n=200`
          );
          if (pRes.ok) {
            const pData = await pRes.json();
            setMicroPreds(pData.predictions || []);
          }
        }
      } catch (e) {
        console.error('Failed to load student data', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [exam]);

  return { student, microPreds, loading };
}
```

**Step 2: Build the student dashboard page**

The page uses `useStudentData` hook, then renders:
1. Hero card (name, ERP, branch, latest %, zone badge)
2. KPI strip (avg score, best score, improvement, consistency)
3. Subject cards grid (clickable, routes to `/student/[subject]`)
4. PRAJNA summary card (X critical, Y focus, Z on track)

Use the components from Task 5. Each subject card computes:
- Student accuracy from `student.subjects[subject].acc` or `student.chapters[subject]`
- PRAJNA exam load from `microPreds.filter(p => p.subject === subject)`
- Critical count from ROI computation

**Commit:** `feat: student dashboard — hero, KPIs, subject cards with PRAJNA fusion`

---

### Task 7: Subject Deep-Dive Page

**Files:**
- Create: `app/student/[subject]/page.tsx`

This page renders the 4 zones from the design:
- **Zone A:** Subject KPI strip (accuracy, PRAJNA load, critical count, chapter count)
- **Zone B:** Top 5 priority actions (highest ROI micro-topics)
- **Zone C:** Chapter breakdown (collapsible ChapterRows with MicroTopicTables)
- **Zone D:** Subject exam history (Recharts bar chart of questions per year — data from predictions)

Data comes from Zustand store (already loaded in Task 6). Filter `microPreds` by subject param. Group by chapter. Compute ROI per micro-topic. Sort chapters by max ROI descending.

**Commit:** `feat: subject deep-dive — 4-zone layout with ROI-ranked chapters and micro-topics`

---

### Task 8: Org Dashboard Page

**Files:**
- Modify: `app/org/page.tsx`
- Create: `lib/hooks/useOrgData.ts`

The org page renders:
1. KPI strip (total students, avg score, critical count, top scorer, most improved)
2. PRAJNA Intel section (top predicted chapters × student gaps — port from org-dashboard.html Section E)
3. Branch cards grid (clickable, shows count, avg, at-risk, weakest subject)
4. Subject health matrix (branch × subject accuracy table)
5. Student leaderboard (sortable table with rank, name, avg%, improvement, zone)

Data hook fetches `/api/students?exam=` and `/api/branches?exam=` from Node.js backend, plus `/api/v1/data/predict?level=chapter&top_n=15` from Intelligence API.

**Commit:** `feat: org dashboard — KPIs, PRAJNA intel, branch cards, matrix, leaderboard`

---

### Task 9: Predictions Page

**Files:**
- Create: `app/predictions/page.tsx`

React-native predictions page with 3 sections:
1. Top predictions list (PredictionCards ranked by probability)
2. Hot/cold topics (HotColdGrid component)
3. Lesson plan table (chapters with priority band A/B/C)

Fetches from Intelligence API:
- `/api/v1/data/predict?level=micro&top_n=100`
- `/api/v1/data/hot-cold-topics`
- `/api/v1/data/lesson-plan`

**Commit:** `feat: predictions page — top predictions, hot/cold topics, lesson plan`

---

### Task 10: Analysis Page (Streamlit Iframe)

**Files:**
- Create: `app/analysis/page.tsx`
- Create: `app/analysis/layout.tsx`
- Create: `components/layout/StreamlitEmbed.tsx`

**Step 1: Create StreamlitEmbed**

```tsx
'use client';

export function StreamlitEmbed({ url }: { url: string }) {
  return (
    <iframe
      src={url}
      className="w-full h-[calc(100vh-48px)] border-none"
      allow="clipboard-write"
    />
  );
}
```

**Step 2: Create analysis page**

```tsx
import { StreamlitEmbed } from '@/components/layout/StreamlitEmbed';

export default function AnalysisPage() {
  const url = process.env.NEXT_PUBLIC_STREAMLIT_URL || 'http://localhost:8501';
  return <StreamlitEmbed url={url} />;
}
```

**Commit:** `feat: analysis page — Streamlit iframe embed for deep analysis tabs`

---

### Task 11: GitHub Repo + Vercel Deploy

**Step 1: Create GitHub repo**

```bash
cd /Users/aman/prajna-portal
gh repo create firnweh/prajna-portal --public --source=. --push
```

**Step 2: Deploy to Vercel**

```bash
vercel --prod --yes
```

Set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_BACKEND_URL`
- `NEXT_PUBLIC_INTEL_URL`
- `NEXT_PUBLIC_STREAMLIT_URL`

**Step 3: Verify end-to-end**

1. Open Vercel URL
2. Login with student credentials → lands on `/student` with sidebar
3. Click subject card → `/student/physics` with 4-zone layout
4. Click "Predictions" in sidebar → predictions page
5. Click "Deep Analysis" → Streamlit iframe
6. Logout → login as center role → lands on `/org`
7. Verify org KPIs, branch cards, leaderboard

**Commit:** `chore: deploy to Vercel with environment variables`

---

Plan complete and saved to `docs/plans/2026-04-01-prajna-portal-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?
