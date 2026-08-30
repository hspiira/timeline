# Tenant creation & password reset — advisory

**Date:** 2026-08-29
**Scope:** How Timeline currently creates tenants and resets passwords, what is painful, and a simpler implementation grounded in the repo and in the five reviewed open-source projects (`frappe/erpnext`, `triggerdotdev/trigger.dev`, `getlago/lago`, `relaticle/relaticle`, `makeplane/plane`).
**Status:** Review/advice. No code changed.

---

## The root cause of the struggle

Two flows feel stuck, but they share **one** root cause and one design tension:

1. **No outbound email exists in the codebase.** Verified: the email connector is inbound-only and even that is stubbed (`app/connectors/email/connector.py`); there is no SMTP/SES/SendGrid code anywhere. Every "reset" today therefore depends on an **out-of-band handoff of a link** (an admin copies a link and gives it to you), because there is no delivery channel to the user.
2. **Tenant creation is really "operator provisioning", not public signup — but the UI labels it "Register".** `POST /tenants` requires a shared secret (`X-Create-Tenant-Secret`) minting an admin user whose password is `never returned`; the admin must then click a one-time `set_password_url`. Public self-signup (`POST /auth/register`) is **disabled** (`auth.py:123`). The frontend `RegisterTenantPage` calls the secret-gated create (`register.tsx` → `auth-store.registerTenant` → `timelineApi.tenants.create`) and would need the secret baked into the client bundle — which `src/env.ts:20` explicitly warns against. So "Register" today only works for an operator who already holds the secret.

**Net:** there is nothing wrong with the primitives; the pain is that (a) there is no delivery channel for links, and (b) the UI presents an operator flow as a self-service flow.

---

## What exists today (grounded)

### Tenant creation
- `POST /api/v1/tenants` (`app/api/v1/endpoints/tenants.py:46`) — shared-secret-gated, rate-limited (`limit_create_tenant`).
- `TenantCreationService.create_tenant` (`app/application/services/tenant_creation_service.py:41`) — one transaction: check code → create tenant → init RBAC → create admin (`admin` / `admin@<code>.timeline`) → assign admin role → mint a set-password token.
- Response carries `set_password_url` (only when `SET_PASSWORD_BASE_URL` is set) + `set_password_expires_at`.
- Frontend `RegisterTenantPage` (`src/routes/register.tsx`) shows the link and offers copy / a same-tab jump to `/set-password`.

### Password set / reset
- **One token store**: `PasswordSetTokenStore` (`app/infrastructure/persistence/repositories/password_set_token_repo.py`), hashed tokens, TTL 24h, atomic one-time redeem via a DB function `redeem_password_set_token` (migration `h6i7j8k9l0m1`). Postgres-only; returns `(user_id, tenant_id)` so the caller can set tenant context before the password write.
- Three endpoints share it:
  - `POST /auth/set-initial-password` (`auth.py:179`) — redeem the tenant-creation token.
  - `POST /auth/admin-reset-password` (`auth.py:201`) — an admin with `user:update` mints a link for an org member; returns the token/URL (not emailed).
  - `POST /auth/reset-password` (`auth.py:247`) — redeem a reset link.
  - `POST /auth/organisations` (`auth.py:270`) and `/auth/login` (`auth.py:293`) resolve org by email to avoid typing a code.
- **Self-service forgot-password does not exist**: `/forgot-password` is a stub (`src/routes/forgot-password.tsx`) reading "Password reset is not yet available. Contact your administrator."

---

## What the five projects do (the pattern to adopt)

| Project | Sign-up / tenant creation | Reset model |
|---|---|---|
| **Plane** | Self-serve: anyone creates a **workspace**; owner is bootstrapped; invites via **email** to join. | Email-delivered reset link (standard) |
| **Frappe/ERPNext** | **Sign-up + invite** (optional domain-gated); workspace via a `Workspace` doctype; owner first-admin. | Email link (or password via invite) |
| **Relaticle** | **Invite-based**: an existing admin invites a user by email; team = a `team_id` on every row (single-tenant-ish). | Standard email reset; a user is tied to a team |
| **Trigger.dev, Lago** | Self-serve sign-up (cloud); **key-based** provisioning for self-host (API tokens/keys, not password-first). | API keys/tokens, not user passwords |

**The converging pattern, adapted to "no email today":**

1. **Tenant creation = invitation, not secret-gated public signup.** The owner-facing flow should be: create a workspace (name + code) → the creator **sets their own password immediately in the same screen** (no random-password-never-returned + second-step token). Frappe/Plane do exactly this: you sign up and choose your password, no emails, no two-step. This removes the entire `set_password_url` round-trip for the person who created the tenant.
2. **Adding members = invite with a one-time link** (that's your existing `admin-reset-password`/`set-initial-password` token flow, which is already correct). The only missing piece is a **delivery channel**; until email lands, the admin copies the link — which already works.
3. **Forgot-password needs either a delivery channel or a verified in-app handoff.** With no email, the honest, simple options are:
   - **Add a minimal outbound email transport** (one provider, e.g. Resend/SES, ~an afternoon) and deliver `admin-reset-password` and forgot-password links. This is the true fix and matches every reviewed product.
   - **Until then, ship "forgot password" as a help desk step**: the user enters their email; an admin (who can see them in `POST /users` / org members) mints the link via the existing `admin-reset-password` — i.e. wire the stub `/forgot-password` page to actually *tell the admin* rather than just say "not available". Or, if you want zero email *and* zero admin, use a **security-question-free proof**: not acceptable for a records product — don't.
4. **Provisioning = key/token, not password** (Trigger.dev/Lago). The operator/API path to create a tenant should use **API keys** (a long-lived operator key in a header), not a shared secret + `never-returned` password. This is a cleaner "platform provisions" story than the current shared-secret.

---

## The simpler implementation (recommended)

### A. Tenant creation — creator sets their own password (removes two-step)
Change `TenantCreationService.create_tenant` so the *creator supplies the admin password* (or a first-login sets it), instead of generating a password it never returns. Concretely:
- Thread `admin_initial_password` through (already supported) **and** make the frontend collect a password + confirm on `/register`, so the creator is fully signed in after creation — matching Frappe/Plane. Keep `set_password_url` only for the **invite** path (below).
- Result: no `set_password_url` round-trip for the owner; `/register` becomes genuinely self-service (with an allow-list/domain rule if you fear abuse — replicate Plane's optional domain-gating).

### B. Two clean flows, sharing the existing token store
Keep the one `PasswordSetTokenStore` (it's good — atomic, hashed, TTL) but give it **two scoped intents** to avoid read-time ambiguity:
- **Invite** (`user:update` perms) → `admin_invite` token intent, expiry e.g. 7 days. This is your current `/auth/admin-reset-password`.
- **Reset** (self-service, needs delivery) → `reset` token intent. Reuses the same redeem function with an `intent` column.
The store already returns `(user_id, tenant_id)` — keep that; it's what lets unauthenticated redemption establish RLS context.

### C. Deliver the links — add one minimal outbound email transport
This is the single highest-value change and the real fix. Add a thin `EmailGateway` behind an interface (mirror Lago's "every external dependency behind a seam"): send invite/reset links. Wire `/forgot-password` and `admin-reset-password` through it. One provider (Resend/SES), one deliverable type (HTML link). This unblocks self-service reset and invites for every future pack. Until it lands, `/forgot-password` should at least route to the org-administrator helpdesk step (B above) instead of a dead-end stub.

### D. (Later) operator provisioning via keys
For the platform-operator path, replace the shared-secret header with **API-key auth** (Trigger.dev/Lago style): a long-lived operator key minted in admin, sent as `Authorization: Bearer <key>` or a dedicated header. The auto-generated `admin@<code>.timeline` + invite link remains for that path. Low priority — the shared secret works; key-based is cleaner.

---

## Minimal change list (in priority order)

1. **Collect a password on tenant creation** (owner sets it at signup) — remove the never-returned-password + `set_password_url` round-trip for the owner. `POST /tenants` keeps accepting `admin_initial_password` (already there); frontend adds the password field on `/register`. *(Backend: `tenant_creation_service.py:74-98`; UI: `register.tsx`.)*
2. **Use the existing admin-reset/invite flow for adding members** — it already works; no change except wording/sharing UX. *(No change needed now.)*
3. **Add a minimal outbound email transport** and deliver reset + invite links. Wire `/forgot-password` to use it. *(New `EmailGateway` behind an interface; endpoints `auth.py:201`/`247`.)*
4. Until email exists, **make `/forgot-password` a helpdesk step** (collect email → tells the org admin to issue a link) rather than a dead stub. *(UI: `forgot-password.tsx`.)*

**Do not** attempt security-question or SMS/OTP password reset without a verified identity channel — for a tamper-evident records product, unverifiable reset is worse than no self-service reset.

---

## The simplest honest option if you want the least code today

Keep the current primitives (they're sound) and just fix the two UX seams:
- On `/register`, have the creator **enter their own password** (kills the two-step for the owner, minimal backend change — the field is already accepted).
- Rewrite `/forgot-password` so that, absent email, it **gives the admin an explicit path** (it already links to admin users; make the message actionable and, when email lands, wire the reset link).

That is a small, safe change that removes most of the perceived friction without new infrastructure. Adding the email transport (C) is the step that makes it fully self-service and consistent with every reviewed project.
