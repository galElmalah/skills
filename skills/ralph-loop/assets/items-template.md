# Items Template — Source of Truth

This file shows example formats for different types of source-of-truth documents.
Adapt the structure to match the use case.

---

## Format: Bug Fixes / Sentry Issues

```markdown
# Issues

## ISSUE-001: TypeError in fetchWithTimeout

- **Priority**: High
- **Users affected**: 104
- **Events**: 1,438
- **Link**: https://sentry.io/issues/ISSUE-001
- **Culprit**: `fetchWithTimeout(packages/agent-core/dist/proxies/accomplish-proxy)`
- **Stacktrace**:
  ```
  TypeError: fetch failed
      at fetchWithTimeout (packages/agent-core/dist/opencode/proxies/accomplish-proxy.js:42:11)
  ```
- **Description**: Fetch calls to the proxy timeout under load. Needs retry logic or better timeout handling.

## ISSUE-002: SqliteError: FOREIGN KEY constraint failed

- **Priority**: Medium
- **Users affected**: 15
- **Events**: 282
- **Link**: https://sentry.io/issues/ISSUE-002
- **Culprit**: `anonymous(packages/agent-core/dist/storage/repositories/taskHistory)`
- **Description**: Task history writes fail when referenced parent record doesn't exist yet.
```

---

## Format: PRD Sections

```markdown
# PRD: User Dashboard Redesign

## Section 1: Navigation Sidebar

- **Status**: Not started
- **Priority**: P0
- **Requirements**:
  - Replace horizontal nav with collapsible sidebar
  - Support nested menu items (2 levels deep)
  - Persist collapsed/expanded state in localStorage
  - Mobile: convert to bottom sheet
- **Design**: See figma.com/file/xxx (frame "Sidebar v2")
- **Acceptance criteria**:
  - [ ] Sidebar renders with all menu items from config
  - [ ] Collapse/expand animates smoothly
  - [ ] State persists across page reloads
  - [ ] Mobile breakpoint triggers bottom sheet

## Section 2: Dashboard Cards

- **Status**: Not started
- **Priority**: P0
- **Requirements**:
  - Render metric cards from API response
  - Support drag-to-reorder
  - Each card has: title, value, trend indicator, sparkline
- **API endpoint**: GET /api/v1/dashboard/metrics
- **Acceptance criteria**:
  - [ ] Cards render from API data
  - [ ] Drag-to-reorder works and persists
  - [ ] Loading and error states handled
```

---

## Format: Feature List

```markdown
# Features

## FEAT-01: Dark Mode Support

- **Description**: Add system-aware dark mode with manual toggle
- **Files likely involved**: `src/theme/`, `src/components/ThemeProvider`
- **Notes**: Use CSS custom properties, not Tailwind dark: prefix
- **Acceptance criteria**:
  - [ ] System preference detected on first load
  - [ ] Manual toggle overrides system preference and persists
  - [ ] All components render correctly in both themes
  - [ ] No flash of wrong theme on page load

## FEAT-02: Export to PDF

- **Description**: Allow users to export reports as PDF
- **Files likely involved**: `src/features/reports/`, `src/lib/pdf`
- **Notes**: Use puppeteer for server-side rendering, not client-side libraries
- **Acceptance criteria**:
  - [ ] Export button visible on report pages
  - [ ] PDF output matches on-screen layout
  - [ ] Large reports (50+ pages) export without timeout
  - [ ] Error state shown if export fails
```

---

## Format: Migration / Refactor Tasks

```markdown
# Migration: React Class Components to Hooks

## MIGRATE-01: UserProfile component

- **File**: `src/components/UserProfile.tsx`
- **Complexity**: Medium (uses lifecycle methods + context)
- **Notes**: Has componentDidMount fetch + componentDidUpdate comparison
- **Acceptance criteria**:
  - [ ] Component uses hooks (useState, useEffect, useContext) instead of class lifecycle
  - [ ] All existing tests pass without modification
  - [ ] No behavioral regressions (fetch timing, re-render conditions)

## MIGRATE-02: SettingsPanel component

- **File**: `src/components/SettingsPanel.tsx`
- **Complexity**: Low (simple state + render)
- **Notes**: Straightforward useState conversion
- **Acceptance criteria**:
  - [ ] Component converted to function with useState
  - [ ] All existing tests pass without modification
```

---

## Key Principles

1. **Every item needs a unique identifier** — the agent uses this to track progress
2. **Include enough context** — the agent should be able to act without asking questions
3. **Priority/ordering matters** — items are processed top to bottom unless the agent groups related ones
4. **Link to external resources** — Sentry URLs, Figma frames, API docs, etc.
5. **Acceptance criteria** — every item except bug fixes should have clear acceptance criteria so the agent knows when the work is done
