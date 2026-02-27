# Website — Definitive Architecture Decisions

## Design/Build Workflow

**Tooling decision:** Claude.ai Artifacts + Cursor.

Claude Code doesn’t have a click-around preview. The correct workflow is:
1. Design in Claude.ai Artifacts (instant visual preview, rapid iteration)
2. Export to Cursor for Next.js implementation

This gives the speed of visual iteration plus production-grade code.

Cursor also supports one-click Stripe setup via its integrations panel.

---

## Core Platform Decisions

- **Framework:** Next.js (correct call)
  - API routes handle iOS enrollment form server-side
  - No separate backend needed for website layer
- **Backend separation:**
  - Railway server remains iOS profile engine + macOS config endpoint
- **Hosting:** Vercel (not Railway)
  - Purpose-built for Next.js
  - Generous free tier
  - Fast GitHub deploys
  - Preview URLs on every PR
  - Native Stripe integration

**Clean separation:**
- Vercel = website
- Railway = API

---

## Domain Routing

- `finallyfreeai.com` → Vercel (Next.js website)
- `api.finallyfreeai.com` → Railway (Python backend, already live)

---

## Website Structure

```text
finallyfreeai.com/
├── /            Hero + product explanation
├── /download    macOS + iOS unified download page
├── /ios/setup   iOS onboarding form → generates profile
├── /partner     Partner setup guide
└── /pricing     Subscription tiers
```

### Unified Download Flow

- **Desktop visitor:**
  - Sees macOS download button
  - Sees “Protect your iPhone too” section
  - Scans QR code linking to `finallyfreeai.com/ios/setup`
  - Completes setup on phone, profile downloads directly in Safari
  - No manual URL transfer

- **Mobile visitor:**
  - Lands directly on iOS setup flow

---

## Payment Architecture — Maximum Conversion

### Conversion Psychology

Recovery users are highly motivated at the decision moment. Friction kills conversion.
Every extra click loses users.

### Recommended Tier Structure

| Tier | Price | What it covers | Positioning |
|---|---|---|---|
| Guardian | $9/mo or $79/yr | macOS only | Entry point |
| Covenant | $19/mo or $149/yr | macOS + iOS | Primary offer |
| Transformation | $299 lifetime | Everything + supervised iOS (future) | Anchor price |

**Why include lifetime:**
- Makes $149/yr feel more reasonable (anchoring)
- Captures high-intent users immediately

### Ethical, High-Performance Conversion Tactics

1. **Annual billing default**
   - Show monthly equivalent (e.g., “just $12.42/mo”)
   - Bill annually
   - Transparent and standard

2. **Free trial, not free tier**
   - 14-day full trial, card required
   - Frame as “cancel anytime in 14 days”

3. **Partner gifting**
   - “Gift protection to someone you love” purchase option
   - Matches target market emotionally
   - Creates additional revenue + viral distribution

---

## Stripe Implementation (Next.js)

In Cursor:
- Install `@stripe/stripe-js` and `stripe`
- Use **Payment Element** (not Checkout)
  - Native inline payment UI
  - Apple Pay / Google Pay support
  - 135+ currencies
  - Link one-click returning checkout

### Required API routes

- `/app/api/create-checkout/route.ts` → creates Stripe session
- `/app/api/webhook/route.ts` → handles subscription events

### Apple Pay conversion moment

Using Payment Element, Apple Pay works automatically on iPhone Safari (with proper Stripe setup).
For users installing the iOS profile on their phone, they can pay with Face ID in one tap right after installation.

That post-install moment is the highest-intent conversion window.
