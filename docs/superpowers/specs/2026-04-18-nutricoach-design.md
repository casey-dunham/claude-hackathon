# NutriCoach — Frontend Design Spec

## Overview

A nutrition-focused personal health coaching app for professionals with unpredictable schedules. Dashboard-driven with a persistent AI coach panel. Minimalist, clean, professional aesthetic.

## Tech Stack

- React 18 + Vite + TypeScript
- Tailwind CSS + shadcn/ui
- React Router (page navigation)
- Recharts (Week view charts)
- Mock service layer (async functions matching future FastAPI + SQLite API shape)

## Layout

### App Shell
- **Icon-only sidebar** (64px) — navigation icons for Dashboard, Meals, Goals, Settings. User avatar at bottom.
- **Header bar** — personalized greeting, date, "+ Log Meal" CTA
- **Content area** — page content on the left (~70%), coach panel on the right (~30%)

### Coach Panel (persistent, right side, 340px)
- Green status indicator + "Coach" label
- Scrollable message area with typed messages:
  - Primary (gray bg) — contextual insights about current nutrition status
  - Highlight (purple bg) — proactive suggestions (travel, patterns)
- Each message has a small type label (NOW, TRAVEL, PATTERN, etc.)
- Text input + send button at bottom
- Minimal — only shows 2-3 most relevant messages at a time

## Pages

### Dashboard (3 sub-views via tabs)

**Today (default)**
- Macro summary row: Calories, Protein, Carbs, Fat — fused cells with values, goals, thin progress bars
- Recent meals: last 2 entries with name, time, calories. "View all" link.
- Hydration: single-line bar with count

**Week**
- 7-day bar chart for calories/protein
- Daily summary cards
- Coach pattern highlights

**Timeline**
- Vertical agenda: morning/midday/evening blocks
- Meal slots with suggestions
- Next meal prompt

### Meals
- Searchable meal log history
- Favorite meals for quick re-logging
- Meal detail with full nutritional breakdown

### Goals
- Daily macro targets
- Dietary preferences
- Travel schedule context for coach

### Settings
- Profile, units, notifications

## Data Architecture (Mock Layer)

```
src/services/mock/
  meals.ts       — CRUD meal entries
  nutrition.ts   — daily macro summaries
  hydration.ts   — water intake
  goals.ts       — user goals/preferences
  coach.ts       — coach messages
  user.ts        — profile data
```

Each module exports async functions returning typed data, structured to match future FastAPI endpoints. Swap mock implementations for fetch calls when backend is ready.

## Visual Design

- **Font:** Inter
- **Base color:** #18181b (near-black)
- **Accent:** #6366f1 (indigo) for protein/interactive elements
- **Background:** #fafafa
- **Borders:** #f0f0f0
- **No emojis** — use subtle dots, thin bars, typography for hierarchy
- **Generous whitespace** — content breathes, nothing competes
- **Principle:** Show minimum needed at a glance. Everything else is one click away.

## Component Structure

```
src/
  components/
    layout/        → AppShell, Sidebar, Header, CoachPanel
    dashboard/     → MacroRow, MealList, HydrationBar
    views/         → TodayView, WeekView, TimelineView
    meals/         → MealLog, MealDetail
    goals/         → GoalSettings
    ui/            → shadcn components
  services/
    mock/          → Mock data modules
    types.ts       → Shared TypeScript interfaces
  pages/           → Dashboard, Meals, Goals, Settings
```
