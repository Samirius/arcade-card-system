# Sindbad (سندباد) — Frontend Design Spec

**Date:** 27 June 2026  
**Status:** Draft → Pending Approval  
**Owner:** Samir George  
**Stack:** Vue 3 + Vite + PrimeVue + Pinia + vue-i18n  

---

## 1. Product Identity

**Name:** Sindbad (سندباد)  
**Tagline (AR):** نظام إدارة ألعابك  
**Tagline (EN):** Run your arcade  
**Primary language:** Arabic (RTL-first)  
**Secondary language:** English (LTR toggle)  
**Brand color:** Deep teal + warm gold (adventure + premium feel)  

**Product positioning:** Cloud-native, Arabic-first cashless card system for MENA arcades and entertainment venues.

---

## 2. Architecture Principles

1. **Design system is the foundation** — every color, spacing, font size, shadow, radius is a token. Change a token → entire app updates. No hardcoded values anywhere.
2. **RTL-first, not RTL-adapted** — layouts are designed from the right. LTR (English) is a mirror, not the default.
3. **Role-based surfaces** — one app, three surfaces (Admin, Cashier, Portal). Role guard redirects on login.
4. **Mobile-first for floor staff** — cashier panel is designed for tablets (7-10"). Admin is desktop-first. Portal is phone-only.
5. **Every screen connects to a real API** — no mock data, no dead UI. If backend doesn't support it yet, it's not in Phase 1.
6. **Security baked in** — httpOnly cookies for tokens (not localStorage), all output escaped via Vue templating (no v-html), CSP headers.

---

## 3. Tech Stack & Project Structure

```
frontend/                          # Replaces existing HTML files
├── public/
│   ├── favicon.ico
│   └── locales/
│       ├── ar.json                # Arabic translations (primary)
│       └── en.json                # English translations (secondary)
├── src/
│   ├── main.ts                    # App bootstrap
│   ├── App.vue                    # Root: layout router + RTL provider
│   │
│   ├── assets/
│   │   └── styles/
│   │       ├── tokens.scss        # Design system tokens (colors, spacing, etc.)
│   │       ├── theme.scss         # PrimeVue theme overrides
│   │       ├── rtl.scss           # RTL-specific adjustments
│   │       └── global.scss        # Reset + base styles
│   │
│   ├── config/
│   │   ├── api.ts                 # Axios instance + interceptors
│   │   ├── routes.ts              # Route definitions with role guards
│   │   └── env.ts                 # Environment config (API base, etc.)
│   │
│   ├── stores/                    # Pinia stores
│   │   ├── auth.ts                # Login state, user, tokens, role
│   │   ├── locale.ts              # i18n state (ar/en), RTL direction
│   │   ├── theme.ts               # Dark/light, density
│   │   └── company.ts             # Active company/tenant context
│   │
│   ├── composables/               # Reusable logic
│   │   ├── useAuth.ts             # Auth helpers (login, logout, refresh)
│   │   ├── useApi.ts              # API call wrapper with loading/error
│   │   ├── useCards.ts            # Card CRUD + balance operations
│   │   ├── useTransactions.ts     # Transaction list + filters
│   │   ├── useOffline.ts          # Offline token management
│   │   └── usePermissions.ts      # Role-based permission checks
│   │
│   ├── components/                # Shared UI components
│   │   ├── layout/
│   │   │   ├── AppSidebar.vue     # Navigation sidebar (admin)
│   │   │   ├── AppTopbar.vue      # Top bar: search, lang toggle, profile
│   │   │   ├── AppFooter.vue
│   │   │   └── PageHeader.vue     # Title + breadcrumb + actions
│   │   ├── ui/
│   │   │   ├── StatCard.vue       # Dashboard metric card
│   │   │   ├── BalanceBadge.vue   # Balance pill (green/red)
│   │   │   ├── CardChip.vue       # Card type indicator
│   │   │   ├── StatusBadge.vue    # Universal status indicator
│   │   │   ├── EmptyState.vue     # No data placeholder
│   │   │   ├── LoadingSkeleton.vue
│   │   │   ├── ConfirmDialog.vue  # Reusable confirm modal
│   │   │   └── AmountInput.vue    # Currency input (EGP/SAR)
│   │   └── cards/
│   │       ├── CardSearch.vue     # Search by UID / customer name
│   │       ├── CardDetails.vue    # Card info panel
│   │       ├── AddCreditForm.vue  # Add credits form
│   │       ├── ChargeCardForm.vue # Deduct/charge form
│   │       └── RegisterCardForm.vue
│   │
│   ├── views/                     # Page-level components
│   │   ├── auth/
│   │   │   ├── LoginView.vue
│   │   │   ├── MfaVerifyView.vue
│   │   │   └── VerifyEmailView.vue
│   │   │
│   │   ├── admin/                 # Admin surface (desktop-first)
│   │   │   ├── DashboardView.vue          → GET /dashboard/stats, /dashboard/revenue
│   │   │   ├── CardsView.vue              → GET /cards/, /cards/{uid}
│   │   │   ├── CardDetailView.vue         → GET /cards/{uid}, /cards/{uid}/transactions
│   │   │   ├── TransactionsView.vue       → GET /transactions/
│   │   │   ├── TransactionDetailView.vue  → GET /transactions/{id}
│   │   │   ├── StaffView.vue              → (Phase 2 — stubbed route)
│   │   │   ├── LocationsView.vue          → (Phase 2 — stubbed route)
│   │   │   ├── MachinesView.vue           → (Phase 2 — stubbed route)
│   │   │   ├── CustomersView.vue          → (Phase 2 — stubbed route)
│   │   │   ├── MaintenanceView.vue        → (Phase 2 — stubbed route)
│   │   │   └── ReportsView.vue            → (Phase 2 — stubbed route)
│   │   │
│   │   ├── cashier/               # Cashier surface (tablet-first)
│   │   │   ├── CashierHome.vue            → Card search + quick actions
│   │   │   ├── CashierBalance.vue         → Balance check + add credit
│   │   │   ├── CashierRegister.vue        → New card registration
│   │   │   └── CashierHistory.vue         → Recent transactions
│   │   │
│   │   ├── portal/                # Customer portal (phone-first)
│   │   │   ├── PortalBalance.vue          → Card balance display
│   │   │   └── PortalHistory.vue          → Transaction history
│   │   │
│   │   └── shared/
│   │       ├── NotFoundView.vue
│   │       ├── UnauthorizedView.vue
│   │       └── SettingsView.vue           # Profile, language, security
│   │
│   ├── router/
│   │   └── index.ts               # Vue Router with role guards
│   │
│   ├── plugins/
│   │   ├── primevue.ts            # PrimeVue component registration
│   │   ├── i18n.ts                # vue-i18n setup (ar default)
│   │   └── toast.ts               # Toast notification config
│   │
│   └── types/
│       ├── api.ts                 # API response types
│       ├── models.ts              # Domain models (Card, Transaction, etc.)
│       └── auth.ts                # Auth types (User, Role, Token)
│
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── tailwind.config.js             # Tailwind for utility classes alongside PrimeVue
```

---

## 4. Design System

### 4.1 Color Tokens

```scss
// ============================================
// SINDBAD DESIGN TOKENS
// Single source of truth. Never use raw values.
// ============================================

// --- Brand ---
$color-brand-primary:    #0D9488;   // Deep teal — trust, professionalism
$color-brand-primary-dark: #0F766E;
$color-brand-primary-light: #14B8A6;
$color-brand-accent:     #F59E0B;   // Warm gold — energy, fun, arcade
$color-brand-accent-dark: #D97706;

// --- Semantic ---
$color-success:  #22C55E;
$color-warning:  #F59E0B;
$color-danger:   #EF4444;
$color-info:     #3B82F6;

// --- Neutral (warm grey palette) ---
$color-bg-base:     #FAFAF9;   // App background
$color-bg-surface:  #FFFFFF;   // Cards, panels
$color-bg-muted:    #F5F5F4;   // Table headers, hover
$color-bg-dark:     #1C1917;   // Dark mode bg

$color-text-primary:   #1C1917;
$color-text-secondary: #57534E;
$color-text-muted:     #A8A29E;
$color-text-inverse:   #FAFAF9;

$color-border:     #E7E5E4;
$color-border-strong: #D6D3D1;

// --- Status (domain-specific) ---
$color-card-active:    $color-success;
$color-card-inactive:  $color-text-muted;
$color-card-lost:      $color-danger;
$color-card-stolen:    #7C2D12;
$color-card-damaged:   $color-warning;

// --- Dark mode overrides ---
$color-bg-base-dark:     #1C1917;
$color-bg-surface-dark:  #292524;
$color-text-primary-dark: #FAFAF9;
$color-border-dark:      #44403C;
```

### 4.2 Typography

```scss
// --- Font families ---
$font-arabic:  'Tajawal', 'Noto Kufi Arabic', sans-serif;  // Arabic
$font-latin:   'Inter', 'Tajawal', sans-serif;              // English
$font-mono:    'JetBrains Mono', monospace;                  // Card UIDs, codes

// --- Font scale (modular) ---
$text-xs:    0.75rem;   // 12px — captions, badges
$text-sm:    0.875rem;  // 14px — secondary text, table cells
$text-base:  1rem;      // 16px — body text (default)
$text-lg:    1.125rem;  // 18px — section headers
$text-xl:    1.25rem;   // 20px — page titles
$text-2xl:   1.5rem;    // 24px — hero numbers (balance)
$text-3xl:   2rem;      // 32px — dashboard stats
$text-4xl:   2.5rem;    // 40px — login title
```

Arabic uses **Tajawal** (clean, modern, excellent RTL). English falls back to **Inter**. Both loaded via Google Fonts / self-hosted.

### 4.3 Spacing & Layout

```scss
// --- Spacing scale (4px base) ---
$space-1:  0.25rem;   // 4px
$space-2:  0.5rem;    // 8px
$space-3:  0.75rem;   // 12px
$space-4:  1rem;      // 16px — default
$space-5:  1.5rem;    // 24px
$space-6:  2rem;      // 32px
$space-7:  3rem;      // 48px
$space-8:  4rem;      // 64px

// --- Border radius ---
$radius-sm:   6px;
$radius-md:   10px;   // Default for cards, inputs
$radius-lg:   16px;   // Modals, panels
$radius-full: 9999px; // Pills, badges

// --- Shadows ---
$shadow-sm:  0 1px 2px rgba(0,0,0,0.05);
$shadow-md:  0 4px 6px -1px rgba(0,0,0,0.1);
$shadow-lg:  0 10px 15px -3px rgba(0,0,0,0.1);

// --- Layout ---
$sidebar-width:        260px;
$sidebar-collapsed:    64px;
$topbar-height:        64px;
$content-max-width:    1440px;
```

### 4.4 Component Patterns

All built as reusable Vue components on top of PrimeVue, themed with tokens:

| Pattern | Component | Usage |
|---------|-----------|-------|
| Stat card | `StatCard` | Dashboard metrics (revenue, cards, txns) |
| Data table | PrimeVue DataTable + custom theme | All list views |
| Balance display | `BalanceBadge` | Inline balance with color (green > 0, red = 0) |
| Card type chip | `CardChip` | VIP (gold), REGULAR (teal), STAFF (purple), TEST (grey) |
| Status badge | `StatusBadge` | Universal status (active/inactive/lost/etc.) |
| Amount input | `AmountInput` | Currency-aware, validates > 0, Decimal-safe |
| Search & select | `CardSearch` | Debounced search by UID or customer |
| Confirm dialog | `ConfirmDialog` | Destructive action confirmation |
| Empty state | `EmptyState` | "لا توجد بطاقات" illustration + CTA |
| Loading | `LoadingSkeleton` | Skeleton screens (not spinners) |

---

## 5. Internationalization (i18n) Architecture

### 5.1 Strategy

- **Default locale:** `ar` (Arabic) — always loads first
- **Fallback locale:** `en` (English)
- **Direction:** `dir="rtl"` on `<html>` by default → switches to `dir="ltr"` on EN
- **No hardcoded text in components** — every string goes through `$t('key')`
- **Number/date formatting:** `Intl.NumberFormat` with `ar-EG` / `en-US`
- **Currency:** displayed as "ج.م" (EGP) or "ر.س" (SAR) based on locale

### 5.2 Translation key structure

```json
// ar.json (excerpt)
{
  "app": {
    "name": "سندباد",
    "tagline": "نظام إدارة ألعابك"
  },
  "nav": {
    "dashboard": "الرئيسية",
    "cards": "البطاقات",
    "transactions": "المعاملات",
    "staff": "الموظفون",
    "locations": "المواقع",
    "machines": "الأجهزة",
    "customers": "العملاء",
    "maintenance": "الصيانة",
    "reports": "التقارير",
    "settings": "الإعدادات"
  },
  "card": {
    "uid": "رقم البطاقة",
    "balance": "الرصيد",
    "type": "النوع",
    "status": "الحالة",
    "types": {
      "regular": "عادية",
      "vip": "VIP",
      "staff": "موظف",
      "test": "اختبار"
    },
    "statuses": {
      "active": "نشطة",
      "inactive": "غير نشطة",
      "lost": "مفقودة",
      "stolen": "مسروقة",
      "damaged": "تالفة"
    }
  },
  "actions": {
    "add": "إضافة",
    "charge": "خصم",
    "save": "حفظ",
    "cancel": "إلغاء",
    "search": "بحث",
    "register": "تسجيل بطاقة",
    "activate": "تفعيل",
    "deactivate": "إلغاء التفعيل"
  }
}
```

### 5.3 RTL handling

PrimeVue has built-in RTL support. We set direction at the app level:

```vue
<!-- App.vue -->
<template>
  <div :dir="direction" :class="localeClass">
    <RouterView />
  </div>
</template>
```

- When `dir="rtl"`: sidebar on right, text flows right-to-left, icons mirror
- When `dir="ltr"`: standard Western layout
- All spacing uses logical properties (`padding-inline-start`, not `padding-left`)

---

## 6. Authentication & Role Routing

### 6.1 Login flow

```
User visits / 
  → Not authenticated? → /login
  → Authenticated:
    → OWNER/ADMIN/SUPERVISOR → /admin/dashboard
    → STAFF → /cashier
    → CUSTOMER → /portal/balance
```

### 6.2 Role matrix

| Surface | Routes | Allowed Roles |
|---------|--------|---------------|
| Admin | `/admin/*` | OWNER, ADMIN, REGIONAL_MGR |
| Cashier | `/cashier/*` | STAFF, SUPERVISOR, ADMIN, OWNER |
| Portal | `/portal/*` | CUSTOMER |
| Shared | `/login`, `/settings` | All |

### 6.3 Token handling

- **Access token:** in memory (Axios default header) — 30 min
- **Refresh token:** httpOnly cookie — 7 days
- **On 401:** attempt refresh → if fails → redirect to `/login`
- **On logout:** call `/logout` → clear in-memory token → redirect
- **No localStorage for tokens** (fixes audit H5 XSS issue)

---

## 7. Surface Designs

### 7.1 Admin Dashboard (desktop-first)

**Layout:** Fixed right sidebar (RTL) + top bar + content area

**Sidebar items:**
1. الرئيسية (Dashboard)
2. البطاقات (Cards)
3. المعاملات (Transactions)
4. الموظفون (Staff) — Phase 2
5. المواقع (Locations) — Phase 2
6. الأجهزة (Machines) — Phase 2
7. العملاء (Customers) — Phase 2
8. الصيانة (Maintenance) — Phase 2
9. التقارير (Reports) — Phase 2
10. الإعدادات (Settings)

**Top bar:** Global search · Language toggle (ع/EN) · Notifications · Profile menu

**Dashboard view (`/admin/dashboard`):**
- Row 1: 4 StatCards (Revenue today, Active cards, Transactions today, Cards issued)
- Row 2: Revenue chart (7-day line) + Cards breakdown (donut by type)
- Row 3: Recent transactions table (10 latest)

**Cards view (`/admin/cards`):**
- Filter bar: status, type, search by UID
- DataTable: UID (mono), customer, type (chip), balance (badge), status, actions
- Row click → Card detail view

**Card detail (`/admin/cards/:uid`):**
- Header: UID, type chip, status badge, balance (large)
- Tabs: Overview | Transactions | Balance History
- Actions: Add credit, Charge, Activate/Deactivate

**Transactions view (`/admin/transactions`):**
- Filter bar: date range, type (ADD/DEDUCT/REFUND), card UID
- DataTable: ID, date, card UID, type, amount, status, user
- Row click → Transaction detail

### 7.2 Cashier Panel (tablet-first, 7-10")

**Layout:** Minimal — no sidebar. Top bar with logo + lang toggle + logout.

**Home (`/cashier`):**
- Large search bar (50% screen) — search by card UID or scan
- Quick actions below: "تسجيل بطاقة جديدة" / "معاملات اليوم"
- Recent activity list (last 5 transactions by this cashier)

**Card found → Balance view (`/cashier/balance/:uid`):**
- Huge balance display (centered, 2xl font)
- Card type chip + status
- Two big buttons: "إضافة رصيد" (green) / "خصم" (orange)
- Recent transactions for this card (last 5)

**Add credit flow:**
- Amount pad (large touch targets, TND-style)
- Confirmation dialog: "إضافة 50 ج.م للبطاقة 1234؟"
- Success toast + return to balance

**Register card (`/cashier/register`):**
- Form: tap card on reader (or manual UID entry) → customer name (optional) → card type → submit
- Success: show balance (0) + quick "add credit" button

### 7.3 Customer Portal (phone-first)

**Layout:** Clean, no navigation. Card-based.

**Balance (`/portal/balance`):**
- Card number display
- Big balance number with currency
- "تحديث" refresh button
- Link to history

**History (`/portal/history`):**
- Timeline-style list (date, type, amount, resulting balance)
- Color: green for ADD, red for DEDUCT
- Infinite scroll (20 at a time)

---

## 8. API Mapping (Phase 1 — real endpoints only)

| Screen | API Endpoint | Method |
|--------|-------------|--------|
| Login | `/api/v1/auth/login` | POST |
| MFA Verify | `/api/v1/auth/login/mfa` | POST |
| Refresh | `/api/v1/auth/refresh` | POST |
| Logout | `/api/v1/auth/logout` | POST |
| Current User | `/api/v1/auth/me` | GET |
| Dashboard stats | `/api/v1/dashboard/stats` | GET |
| Dashboard revenue | `/api/v1/dashboard/revenue` | GET |
| Recent transactions | `/api/v1/dashboard/transactions/recent` | GET |
| List cards | `/api/v1/cards/` | GET |
| Card detail | `/api/v1/cards/{uid}` | GET |
| Card balance | `/api/v1/cards/{uid}/balance` | GET |
| Card transactions | `/api/v1/cards/{uid}/transactions` | GET |
| Add credit | `/api/v1/cards/{uid}/add-credit` | POST |
| Charge card | `/api/v1/cards/{uid}/charge` | POST |
| Activate card | `/api/v1/cards/{uid}/activate` | POST |
| Deactivate card | `/api/v1/cards/{uid}/deactivate` | POST |
| Create card | `/api/v1/cards/` | POST |
| List transactions | `/api/v1/transactions/` | GET |
| Transaction detail | `/api/v1/transactions/{id}` | GET |
| Balance history | `/api/v1/balance/history/{uid}` | GET |
| Company stats | `/api/v1/companies/{id}/stats` | GET |

---

## 9. Build Phases

### Phase 1 — Foundation + Core (what we build now)

**Sprint A: Project scaffolding + design system**
- Vite + Vue 3 + TypeScript setup
- PrimeVue + theme + tokens
- i18n (ar/en) with RTL/LTR switching
- Auth store + login flow + role routing
- Axios setup with interceptors
- Layout shells (admin sidebar/topbar, cashier minimal, portal clean)

**Sprint B: Admin core pages**
- Dashboard (stats, revenue chart, recent transactions)
- Cards list + detail
- Transactions list + detail
- Settings (profile, language toggle)

**Sprint C: Cashier panel**
- Card search + balance
- Add credit flow
- Register new card
- Cashier history

**Sprint D: Customer portal**
- Balance display
- Transaction history

### Phase 2 — Management depth (when backend is ready)
- Staff management
- Locations & zones
- Machine inventory + monitoring
- Customer profiles
- Maintenance scheduling
- Reports & analytics

### Phase 3 — Platform
- Payments integration (Paymob)
- Multi-venue dashboards
- Advanced BI
- Mobile app foundation

---

## 10. Security Requirements (from audit)

| Audit Item | How we fix it |
|-----------|---------------|
| H5: Stored XSS via innerHTML | Vue auto-escapes `{{ }}`. No `v-html` anywhere. CSP headers. |
| H5: JWT in localStorage | In-memory access token + httpOnly refresh cookie |
| IN-1: CORS from env | API CORS configured server-side, frontend reads from same origin |
| M5: Security info endpoint | Not exposed in frontend |
| CSP | `script-src 'self'` — no unsafe-inline/unsafe-eval |

---

## 11. Testing Strategy

- **Unit tests:** Vitest — composables, stores, utility functions
- **Component tests:** Vue Test Utils — form validation, role guards
- **E2E tests:** Playwright — login flow, card operations, balance changes
- **Visual regression:** (Phase 2) — Percy/Chromatic on key pages

---

## 12. Open Decisions

1. **Logo/brand identity** — need a designer or use a typographic logo for now?
2. **Font hosting** — Google Fonts CDN or self-hosted? (Self-hosted better for offline/EGY latency)
3. **Dark mode in Phase 1?** — Easy with tokens, but adds testing surface.
4. **PWA?** — Customer portal could be installable. Adds manifest + service worker.
5. **Backend API prefix** — currently inconsistent (`/cards/` vs `/api/v1/cards/`). Need to standardize.

---

## 13. What's NOT in This Spec

- Firmware/reader UI (separate concern — ESP32 TFT display)
- Mobile native app (Stage 3+)
- Payment gateway UI (Stage 3 — Paymob hosted checkout)
- White-label/theming for multiple brands (Stage 4+)
- Multi-currency display (Stage 3+)
