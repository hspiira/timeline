# Tenant creation and password reset — implementation plan

**Date:** 2026-08-29
**Inputs:** `TENANT-AUTH-ADVISORY.md` (other agent) and a second review. Where the two disagreed, the resolution is stated inline with the reason.
**Verification status:** every "Verified" line below was read directly at the cited `file:line` during this pass. Anything not verified is labelled. Two claims from the earlier review were **wrong and are corrected here.**

---

## Corrections to the earlier review

| Earlier claim | Status | Reality |
|---|---|---|
| "`/register` sends no secret header and always 401s" | **WRONG** | `apps/web/src/lib/api-client.ts:120-123` has middleware that reads `VITE_CREATE_TENANT_SECRET` and sets `X-Create-Tenant-Secret`. `/register` works when that env var is set. The call site in `auth-store.ts` sets no header; the middleware does. The error was reading the call site and stopping |
| "Orphan tenant when the token store is absent" | **Imprecise** | `get_tenant_creation_service` (`_core.py:284`) **always** injects a `PasswordSetTokenStore`, so a token is always minted. The real defect is narrower and certain: see B-01 |

The other agent's framing was correct and this plan adopts it: **tenant creation is operator provisioning wearing a "Register" label**, not a broken signup.

---

## Verified current state

| Fact | Evidence |
|---|---|
| `POST /tenants` is gated by `X-Create-Tenant-Secret`; 503 if unset, 401 if mismatched | `app/api/v1/endpoints/tenants.py:56-72` |
| The client sends that header from `VITE_CREATE_TENANT_SECRET` | `apps/web/src/lib/api-client.ts:120-123` |
| That env var is documented as unsafe for production | `apps/web/src/env.ts:20` — "Dev/demo only — never set the real secret in production (it would be exposed in the client bundle)" |
| `POST /auth/register` (public signup) is **disabled** | `app/api/v1/endpoints/auth.py:123`, docstring "Disabled. Use the authenticated `POST /api/v1/users` to add someone." |
| `TenantCreateRequest` accepts **only** `code`, `name`, `admin_initial_password` | `app/schemas/tenant.py:15-35` |
| Admin identity is derived, not supplied: `admin` / `admin@{code}.timeline` | `app/application/services/tenant_creation_service.py` |
| `TenantCreateResponse` has **no token field**; only `set_password_url`, gated on `SET_PASSWORD_BASE_URL` | `app/schemas/tenant.py:51-65`; `tenants.py:102-105` |
| A token **is** always minted (store always injected) | `app/api/v1/dependencies/_core.py:284` |
| `POST /users` **requires** a password, min 8 | `app/schemas/user.py:6-11`; `app/api/v1/endpoints/users.py:33-38` |
| `AdminResetPasswordResponse` always returns `token`; `reset_url` conditional | `app/schemas/auth.py:96-106` |
| Token store: SHA-256 hashed at rest, 24h TTL, single-use claimed atomically in DB function `redeem_password_set_token`, returns `(user_id, tenant_id)` | `app/infrastructure/persistence/repositories/password_set_token_repo.py` |
| `register.tsx` collects **only** tenant code and name | `apps/web/src/routes/register.tsx:33-34` |
| No outbound email exists anywhere. The email module is inbound only | Searched `send_mail`, `smtplib`, `send_email`, `EmailMessage` across `app/` |
| `/forgot-password` is a static dead end | `apps/web/src/routes/forgot-password.tsx` — "Password reset is not yet available." |

**Not verified, do not rely on:** whether `redeem_password_set_token` (migration `h6i7j8k9l0m1`) can be altered without breaking existing rows; whether any test currently covers tenant creation.

---

## The defect list, tightest statement of each

**B-01. Tenant creation can return 201 for a tenant nobody can enter.**
A token is always minted. But `TenantCreateResponse` has no field to carry it, and `set_password_url` is built only when `SET_PASSWORD_BASE_URL` is set (`tenants.py:102-105`). With that unset, the token exists in the database and is disclosed nowhere. The admin password was generated and never returned. The tenant is live and unenterable. `AdminResetPasswordResponse` already solves this correctly by always returning `token` — tenant creation just does not copy that pattern.

**B-02. The admin email is non-routable.** `admin@{code}.timeline` cannot receive mail. This blocks any delivery work before it starts.

**B-03. There is no invite primitive.** `POST /users` requires a password, so "adding a colleague" means an administrator chooses that person's password and tells them. For a records product where the actor on an event is evidence, shared-known passwords undermine attribution.

**B-04. No self-service reset, and no delivery channel for any link.**

---

## Decisions required before coding

| # | Decision | Why it blocks |
|---|---|---|
| **D-1** | **Is signup open, invite-only, or operator-only?** | Determines whether S-02 is wanted at all. `/auth/register` is disabled and `/register` is dev-gated, so the codebase currently says operator-only while the UI says otherwise |
| **D-2** | **Does the derived `admin@{code}.timeline` identity survive anywhere?** | If yes, B-02 persists on that path and delivery can never work for it. Recommendation: no — require a real admin email on every path |
| **D-3** | **When does delivery land, and through what?** | S-05 is useless without it. See the sequencing note under S-06 |

---

## Target model

Three paths, named for what they actually are. One token store, one redeem endpoint, an `intent` column separating them.

| Path | Who | Password | Token |
|---|---|---|---|
| **Owner signup** | Person creating the organisation | **Sets their own, immediately** | None. No round-trip |
| **Member invite** | Admin adds a colleague | **Not set by the admin** | `intent=invite`, longer TTL |
| **Password reset** | Self-service, or admin-initiated | Set by the person | `intent=reset`, short TTL |
| **Operator provisioning** | Platform operator, scripted | Auto, plus an invite token | `intent=invite` |

---

## Steps

Ordered so each is independently shippable and none blocks on delivery except where stated.

### S-01. Stop returning 201 for unenterable tenants
**Fixes:** B-01. **Depends on:** nothing. **Effort:** ~1 hour.

Add `set_password_token: str | None` to `TenantCreateResponse` and populate it always, mirroring `AdminResetPasswordResponse`. Keep `set_password_url` conditional as it is.

Alternative if disclosing the token in the response body is unwanted: fail with 503 when no disclosure channel is configured, rather than creating the tenant. **Do not leave both off.**

**Acceptance:** with `SET_PASSWORD_BASE_URL` unset, the response still carries a usable token; a test creates a tenant with it unset, redeems the returned token, and signs in.

### S-02. Owner signup sets their own password
**Fixes:** the two-step round-trip. **Depends on:** D-1, D-2. **Effort:** ~1 day.

- `TenantCreateRequest`: add `admin_email: EmailStr` (required) and `admin_username: str | None` (default `"admin"`). Keep `admin_initial_password` optional so the operator path still works.
- `TenantCreationService`: use the supplied email and username instead of deriving them. Derive **only** when not supplied, i.e. the operator path.
- `register.tsx`: add email, password and confirm fields to the existing code and name.
- On 201 with a supplied password, call login and land the creator in the app. Show the link **only** when no password was supplied.

**Acceptance:** creating an organisation through the UI ends in an authenticated session with no link handling. The operator path with no password still returns a token per S-01.

This is the other agent's recommendation A and it is the right lead. `admin_initial_password` is already threaded through the service, so most of the backend work is the email and username fields.

### S-03. A real invite primitive
**Fixes:** B-03. **Depends on:** S-04 for intent, or ship with the current single token type and add intent after. **Effort:** ~1 day.

- `UserCreateRequest.password` becomes optional.
- When absent, `POST /users` mints an invite token and returns `token` plus conditional `invite_url`, mirroring `AdminResetPasswordResponse`.
- When present, behaviour is unchanged.

**Acceptance:** an admin creates a colleague with no password and receives a one-time link; the colleague sets their own password; the admin never knows it.

### S-04. `intent` column on `password_set_token`
**Depends on:** nothing. **Effort:** ~1 day. **Risk: highest in this plan.**

Add `intent` with values `initial`, `invite`, `reset`. TTL per intent: invite 7 days, reset 1 hour, initial 24 hours as today.

**The risk is the DB function.** Redemption goes through `redeem_password_set_token` (migration `h6i7j8k9l0m1`), which claims the token atomically and is RLS-aware. Changing it requires a migration that alters the function, and **whether it can be altered without breaking in-flight rows was not verified.** Backfill existing rows to `initial` before making the column non-null. Do not change the claiming semantics while adding the column; those are two migrations, not one.

**Acceptance:** each intent honours its own TTL; a reset token cannot be redeemed as an invite; concurrent redemption still yields exactly one winner (existing behaviour must be re-proved by test, since this is the one place the change could silently weaken a guarantee).

### S-05. Self-service forgot-password
**Depends on:** S-04, and on D-3 for anything visible to happen. **Effort:** ~half a day for the endpoint.

`POST /auth/forgot-password {email}` returns **204 always**, whether or not the account exists, in constant time. Mints an `intent=reset` token and hands it to delivery.

**Sequencing note:** without delivery this endpoint succeeds and does nothing observable, which is worse than the current honest dead end. Until S-06 lands, `/forgot-password` should say what actually happens: the request goes to an administrator, who issues a link via `POST /auth/admin-reset-password`. That is the other agent's interim and it is correct.

### S-06. Delivery
**Fixes:** B-04, the root cause. **Depends on:** B-02 being fixed by S-02. **Effort:** ~2-3 days for the minimal version.

**Resolution of the disagreement between the two reviews.** The other agent proposed a standalone `EmailGateway` behind an interface. The second review argued email belongs in the Phase 3 transactional outbox from `IMPLEMENTATION-ROADMAP.md`. Both are right and they compose:

- Keep the **gateway seam** (their point). One interface, one provider behind it.
- Do **not** send synchronously from the request path (the second point). A bare `await gateway.send(...)` has no retry, and adding retry later means writing the outbox twice.
- Minimal version that is not throwaway: a `pending_notification` table plus a small worker that drains it with backoff and an idempotency key. That is a small outbox, and it is the seed Phase 3 grows rather than replaces.

**Channel:** make the interface `deliver(recipient, template, context, channel)`. Email first. See the security constraint below before adding any second channel.

**Acceptance:** a reset link is delivered without a human copying it; a provider outage retries rather than dropping; the same request twice does not send twice.

### S-07. Operator provisioning by key, and relabel the UI
**Depends on:** D-1. **Effort:** ~1-2 days.

Replace `X-Create-Tenant-Secret` with an operator API key, per Trigger.dev and Lago. Then, per D-1, either make `/register` genuinely self-service or remove it and stop calling an operator flow "Register".

Lower priority than S-01 to S-03 — the shared secret works today.

---

## The security constraint, agreed by both reviews

> Do not build reset on an unverified identity channel. For a records product, an unverifiable reset is worse than no self-service reset.

That warning is correct as written. The nuance the second review adds, and which does not weaken it:

- **SMS as identity proof** — "give us a number, we'll reset it" — is exactly the failure being warned against. Do not do this.
- **SMS as delivery to a number verified and bound to the account at provisioning** is a different thing and is how most of the world sends reset links.

Ugandan institutional users are often more reachable by SMS than by email, so the channel abstraction in S-06 is worth having. But **nothing in the system currently stores or verifies a phone number**, so this is future work with a prerequisite, not a near-term option.

---

## Sequence and effort

| Step | Effort | Blocks on | Ship independently? |
|---|---|---|---|
| S-01 stop unenterable tenants | ~1 hour | — | Yes |
| S-02 owner sets own password | ~1 day | D-1, D-2 | Yes |
| S-03 invite primitive | ~1 day | — | Yes |
| S-04 intent column | ~1 day | — | Yes, highest risk |
| S-05 forgot-password endpoint | ~0.5 day | S-04, D-3 | Only with S-06 or the interim |
| S-06 delivery | ~2-3 days | S-02 for B-02 | Yes |
| S-07 operator key, relabel | ~1-2 days | D-1 | Yes |

**S-01 through S-03 total roughly two days and remove most of the daily friction.** They need no delivery channel and no decisions beyond D-1 and D-2.

---

## Standing rules for this work

1. **S-04 gets its own migration and its own test run.** It is the only step that can silently weaken an existing guarantee, namely single-use atomic redemption.
2. **Do not rewrite the token store.** Hashed at rest, atomic single-use claim, RLS-aware, TTL enforced. It is the strongest part of this subsystem.
3. **Every step ships with the test in its acceptance criteria.** Auth currently has partial coverage; these paths are exactly where a silent regression is most expensive.
4. **Constant-time, non-enumerating responses** on anything taking an email address.
5. **No claim about this subsystem goes in a document without a `file:line`.** Two claims in the earlier review were made from the call site rather than the full path, and one of them was wrong.
