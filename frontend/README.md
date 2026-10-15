# HireView frontend

The recruiter-facing web app for HireView: paste a job description, see every resume in the pool ranked and marked up ("Red Pen" design), ask questions about the candidates, and manage the resume pool.

Stack: Vite 7, React 19, TypeScript, Tailwind CSS 4, TanStack Query, react-markdown. No component library.

## Run it locally

The backend must be running first (see `../docs/SETUP.md`). It is expected on port 8010.

```bash
npm install
npm run dev        # http://localhost:5173
```

In development, Vite forwards every `/api/*` request to `http://localhost:8010` (see `vite.config.ts`). The backend strips the `/api` prefix itself, the same way it does on Vercel.

The header shows **Connected** once the backend answers `/health`.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Type-check, then build to `dist/` |
| `npm run preview` | Serve the built `dist/` locally |
| `npm run typecheck` | Type-check only |
| `npm test` | Unit tests (Vitest) for `src/lib` |

## Settings

All optional. Set them in `.env.local` for local work, or as Vercel environment variables.

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_BASE` | `/api` | Where the backend lives. Only needed if the backend is on another domain (then add this site to the backend's CORS list) |
| `VITE_COMPANY_ID` | Test Co's id | The company whose pool is ranked |
| `VITE_COMPANY_NAME` | `Test Co` | Name shown in the header |

These are read at build time, so rebuild after changing them.

## Deploying

The repo-root `vercel.json` deploys this folder as the `frontend` service and the backend container as the `backend` service on the same domain: `/api/*` goes to the backend, everything else to this app. See `../documentation/next_session.md` for the step-by-step.

If the backend sets `ACCESS_CODE`, the app asks for it before anything else and sends it as the `X-Access-Code` header.

## Where things are

```
src/
  App.tsx              page state: tab, ranking, open candidate, chat
  styles.css           design tokens (light + dark), the marks, shared component classes
  lib/
    api.ts             every backend call and error-message handling
    format.ts          names, skills, durations, labels
    theme.ts           light / dark / system switch
    toast.tsx          small confirmation messages
  components/
    Header, AccessGate, ErrorBoundary
    RankScreen → JobInput, ResultsList, AskPanel
    CandidatePanel     the slide-in candidate view
    PoolScreen         upload, filter, delete
    Marks              highlighter, strike, circled label, score, initials
    Note, Markdown     AI-written text (Markdown loads on demand)
    Icons              inline SVG icons and the logo
```

## Design notes

- **The marks carry the meaning.** Yellow highlighter = has a required skill. Red strikethrough = missing it. Circled hand-written label = the verdict (Exceptional → Weak). The score out of 100 is secondary.
- **Fonts:** Literata (names, headings, AI text), Schibsted Grotesk (interface), Shantell Sans (the red-pen notes only).
- **Colours** are CSS variables in `styles.css`; dark mode redefines them. The theme follows the system unless the header toggle pins it (`html[data-theme]`).
- **Motion:** rows settle in, the highlighter swipes once, score bars fill. All of it is turned off when the system asks for reduced motion.
- **Honest waiting:** long AI calls show elapsed seconds and placeholders, never a fake percentage.

## Keyboard

| Key | Where | Action |
|---|---|---|
| `Ctrl`/`⌘` + `Enter` | Job description | Rank candidates |
| `/` | Results | Jump to the question box |
| `←` / `→` | Candidate panel | Previous / next candidate |
| `Esc` | Candidate panel, delete confirm | Close / cancel |

## Browser storage

Only conveniences, all safe to lose: the job description draft and theme choice (`localStorage`), the last ranking for this tab (`sessionStorage`, so a refresh keeps it), and the access code (`localStorage`).
