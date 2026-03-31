# CS4417 — Secure Software Design and Implementation
## Tester Branch: Bahari | User Testing Log

This document tracks all user-facing testing conducted on the secure Flask web application. It covers the evolution from the initial codebase to the current version, all vulnerabilities discovered during testing, and the mitigations implemented. Attacker testing will be documented in a separate section once completed.

## Part 1: User Testing

### Overview

User testing was conducted by systematically testing every user-accessible form and flow in the application. The goal was to attempt every possible input combination, identify where the system failed to handle bad input gracefully, and verify that mitigations were effective after each fix.

---

### 1.1 Registration Form

#### What was tested
- Submitting empty fields
- Usernames shorter than 3 characters
- Registering a username that already exists
- Passwords that do not meet the policy
- Passwords with only letters, only numbers, no symbols, no uppercase
- Mismatched confirm password
- Passwords that match/ has >= 3 consecutive charachters from the username or name

#### Vulnerabilities found in initial version
| # | Issue | Impact |
|---|-------|--------|
| 1 | No first/last name required | Incomplete user identity |
| 2 | No check if password contained the user's name | Weak password policy |
| 3 | No symbol requirement in password | Passwords too easy to brute-force |
| 4 | No password peeking button | Users could not see if they accidentally put wrong password |

#### Mitigations implemented
- Added `first_name` and `last_name` fields as required both in the model and registration route
- Added check: password must not contain the user's first or last name (case-insensitive, min 3 chars)
- Extended `password_ok()` to require at least one special character using ASCII range matching
- Added password peeking button to check the input
- All validation failures return specific, actionable flash messages

#### Test results — all passing after mitigations
- Empty first/last name → blocked with error message
- Username < 3 chars → blocked
- Password `Password1` (no symbol) → blocked
- Password `bahari123!` containing last name → blocked
- Passwords not matching → blocked
- Duplicate username → blocked

---

### 1.2 Login Form

#### What was tested
- Valid credentials → successful login
- Wrong password → error message
- Wrong username → error message
- Repeated wrong passwords to trigger lockout
- Waiting out the lockout timer and retrying
- Attempting login with a locked account before timer expires

#### Vulnerabilities found in initial version
| # | Issue | Impact |
|---|-------|--------|
| 1 | No brute-force protection | Attacker could try unlimited passwords |
| 2 | Login errors revealed whether username existed | Username enumeration |

#### Mitigations implemented
- When the username does not exist, the error message is identical to a wrong-password message ("Invalid credentials.") — prevents user enumeration
- `failed_logins` counter resets on successful login and after lockout period expires

#### Test results — all passing after mitigations
- 5 wrong passwords → account locked, shows lockout message
- Login attempt on locked account before 5 min → blocked
- Login attempt after 5 min timeout → unlocked, allowed
- Non-existent username → same generic error as wrong password

---

### 1.3 Password Reset Flow

#### What was tested
- Accessing reset page without a session token (direct URL access)
- Submitting an invalid username at the verify step
- Answering the security question incorrectly multiple times
- Answering correctly on the first try
- Entering a new password that fails the policy
- Entering mismatched new passwords
- Refreshing the reset page mid-flow
- Navigating directly to `/reset_password` after only completing `/verify_username` (skipping the security question)
- Navigating directly to `/security_question` by pasting the URL without going through `/verify_username`
- Pasting `/reset_password` URL directly after a previous reset flow (stale session keys)

#### Vulnerabilities found in initial version
| # | Issue | Impact |
|---|-------|--------|
| 1 | No session token to authorize the reset flow | Anyone could access `/reset_password` directly |
| 2 | No limit on security question attempts | Attacker could brute-force answers |
| 3 | Invalid username gave a direct "user not found" response | Username enumeration |
| 4 | `/reset_password` only checked `reset_user` + `reset_token` — both set at `/verify_username` before the security question is answered | Security question entirely bypassable by pasting `/reset_password` after entering a valid username |
| 5 | `/security_question` only checked `reset_user` + `reset_token` — both persist in session after a completed flow | Anyone could paste `/security_question` URL and answer questions to reset the last user's password without going through `/verify_username` first |

#### Mitigations implemented
- Session-based reset token (`secrets.token_hex(16)`) generated at start of flow
- Security question attempts limited to 3; exceeding clears session and redirects to login
- Security question randomly selected from 3 possible questions per user
- Failed username lookup returns generic error — prevents enumeration
- **Replaced `reset_verified` flag with `reset_step` state machine** — the session now tracks exactly which step of the flow is active. Each page requires the correct step value and sets the next one on success. Pasting any URL out of order fails immediately

```
/verify_username  →  sets reset_step = "security_question"
/security_question  →  requires reset_step == "security_question"
                    →  on correct answer: sets reset_step = "reset_password"
/reset_password   →  requires reset_step == "reset_password"
                    →  on success: session.clear()
```

- `reset_step` is cleared at the start of every new flow via `session.pop("reset_verified", None)` and overwritten with `"security_question"`

#### Test results — all passing after mitigations
- Direct GET to `/security_question` without session → redirected to login ✓
- Direct GET to `/security_question` after a previous completed flow (stale session) → blocked, `reset_step` is gone ✓
- Complete `/verify_username` then paste `/reset_password` directly (skip security question) → blocked, `reset_step` is `"security_question"` not `"reset_password"` ✓
- Full correct flow: verify → answer question → reset → blocked on re-paste (session cleared) ✓
- Wrong security answer 3 times → session cleared, redirected to login ✓
- New password failing policy → blocked ✓
- Mismatched new passwords → blocked ✓

---

### 1.4 Password Peeking (Show/Hide Password)

#### What was implemented
- Added a show/hide password toggle (eye icon) on login, registration, and reset password forms
- Implemented using a JavaScript toggle on the `type` attribute of the password input (`type="password"` ↔ `type="text"`)
- Eye icon from Boxicons (`bx-hide` / `bx-show`) toggles visually to reflect current state

#### What was tested
- Click eye icon → password becomes visible
- Click again → password hidden again
- Works on all password fields: login, register, confirm password, reset password
- Does not interfere with form submission

#### Test results — all passing
- Show/hide works on all password fields across all pages
- Icon state reflects the current visibility correctly

---

### 1.5 Feedback Form

#### What was tested
- Submitting with all valid fields → success message shown
- Submitting with an incomplete email (`abcd`, `abcd@`, `abcd@gmail`) → should be rejected
- Submitting a message that exceeds the 2000-character limit → should be rejected
- Submitting with an empty name, email, or message → should be blocked by `required` attribute
- Typing in the message box to verify live character countdown

#### Vulnerabilities / UX issues found in initial version
| # | Issue | Impact |
|---|-------|--------|
| 1 | Invalid email format (e.g. `abcd@gmail`, `abcd@`) was not caught client-side | Feedback logged without a valid contact email |
| 2 | No maximum length enforced on the message field | Oversized input could be submitted, potentially causing database issues |
| 3 | No visual feedback for character limit | User had no way to know they were approaching or exceeding the limit |
| 4 | Server-side validation errors were not rendered back to the page | Errors silently swallowed, user had no feedback |

#### Mitigations implemented
- Added client-side email validation on `blur` using regex `/^[^@]+@[^@]+\.[^@]+$/`; a red label appears below the field for incomplete formats
- Error label hides again as soon as the user starts correcting the input
- Added `maxlength="2000"` to the textarea (hard browser-level cap)
- Added live character countdown: starts at `2000 characters remaining`, counts down per keystroke, turns red under 100
- Template now renders `{{ error }}` and `{{ success }}` from the route's context, so server-side validation errors (e.g. "Message too long") are displayed on-page

#### Test results — all passing after mitigations
- `abcd` in email, click away → red error label appears
- `abcd@gmail` in email, click away → red error label appears
- `abcd@gmail.com` → label does not appear
- Typing in message box → countdown decrements correctly
- Typing 1950+ characters → counter turns red
- Pasting text beyond 2000 chars → browser hard-stops at 2000
- Submitting feedback that fails server validation → error message rendered on page
- Successful submission → "Feedback submitted successfully!" shown on page

---

### 1.6 Session and Access Control

#### What was tested
- Accessing `/dashboard` without being logged in
- Accessing `/feedback-page` without being logged in
- Logging out and attempting to navigate back using browser back button
- Accessing protected routes with an expired session
- Copy-pasting `/feedback-page` URL into a new browser tab while logged in
- Copy-pasting `/reset_password` URL into a new browser tab mid-flow
- Reloading the page during the password reset flow

#### What was verified
- `@login_required` decorator on dashboard and both feedback routes redirects unauthenticated users to login
- `logout_user()` properly invalidates the session
- Session cookie is `HttpOnly` and `SameSite=Lax` protected (configured in `Config`)
- Closing a single tab does not log the user out — the session cookie persists in the browser until the entire browser is closed or the user explicitly logs out (expected behavior, not a vulnerability)

#### Test results — all passing
- Unauthenticated access to `/dashboard` → redirected to `/login`
- After logout, back-button to dashboard → redirected to login (session invalidated)
- Close tab, reopen URL → still logged in (session cookie still in browser — correct)
- Close entire browser, reopen URL → redirected to login (session cookie expired — correct)

> **Note:** Session hijacking (stealing a valid session cookie to impersonate a logged-in user) is an attacker-level technique and is documented in Part 2: Attacker Testing.

---

### 1.7 URL Copy-Paste and Mid-Flow Navigation Testing

#### What was tested
- Copying `/feedback-page` URL and opening it in a new browser tab while not logged in
- Copying `/feedback-page` URL and opening it in a new browser tab while logged in (same browser)
- Copying `/reset_password` URL mid-flow (after answering security question) and pasting into a new tab
- Reloading `/reset_password` mid-flow after already submitting a new password
- Reloading `/security_question` after it was already answered

#### Findings and analysis

**Feedback page — unauthenticated access (Issue confirmed by live test)**

The `/feedback-page` GET route and `/feedback` POST route both had no authentication requirement. Tested by opening `/feedback-page` in a completely separate browser (no session, no cookies) — the form loaded and feedback was successfully submitted without being logged in at all. This is a violation of **CWE-287: Improper Authentication**.

Two routes were vulnerable, not just one:
- `GET /feedback-page` — page loads without login
- `POST /feedback` — submission succeeds without login (direct POST also possible)

> Note: Opening `/feedback-page` in a new tab **while already logged in** (same browser) is **not** a vulnerability. The browser shares the same session cookie across tabs — the server correctly identifies you as the same authenticated user.

**Reset password URL — different browser test (Behaved correctly)**

Opening `/reset_password` in a completely different browser (no session) correctly returned "Unauthorized password reset attempt." and redirected to login. This is the expected behavior — the reset token only exists in the original browser's session, so a different browser has no token and is blocked.

**Reloading mid-flow**

Reloading `/security_question` mid-flow keeps the user on the same question because the session preserves `current_question` and `correct_answer`. This is by design and not a vulnerability — the same authenticated session is continuing the same flow.

#### Relevant CWE references

| ID | Name | How it applies here |
|----|------|---------------------|
| CWE-287 | Improper Authentication | Feedback page and submit route accessible without any login |
| CWE-306 | Missing Authentication for Critical Function | Feedback submission is a write operation with no auth check on either route |
| CWE-613 | Insufficient Session Expiration | Reset session must be cleared after use (already done via `session.clear()`) |

#### Mitigations implemented

**Fix — Both feedback routes now require login**

Added `@login_required` to both `feedback_page()` (GET) and `submit_feedback()` (POST) in `feedback_routes.py`. Also added `from flask_login import login_required` to the imports. Unauthenticated users are now redirected to the login page on both routes.

```python
@feedback_bp.route("/feedback-page", methods=["GET"])
@login_required
def feedback_page():
    ...

@feedback_bp.route("/feedback", methods=["POST"])
@login_required
def submit_feedback():
    ...
```

**Reset flow — already secure**

Confirmed via live test: opening `/reset_password` in a different browser with no session correctly blocks the request. The existing `session.clear()` after a successful reset also prevents token reuse within the same browser.

#### Test results — all passing after mitigations
- Open `/feedback-page` in different browser (not logged in) → redirected to login ✓
- Direct POST to `/feedback` without session → redirected to login ✓
- Open `/feedback-page` in new tab while logged in (same browser) → allowed (correct) ✓
- Open `/reset_password` in different browser → blocked, "Unauthorized" message ✓
- Reload `/reset_password` after successful reset → blocked (session cleared) ✓
- Reload `/security_question` mid-flow → stays on question (expected, same session) ✓

---

### Summary: User Testing Complete

| Area | Issues Found | Mitigated | Status |
|------|-------------|-----------|--------|
| Registration | 4 | 4 | ✓ Done |
| Login / Brute-force | 2 | 2 | ✓ Done |
| Password Reset Flow | 5 | 5 | ✓ Done |
| Password Peeking | 0 (new feature) | N/A | ✓ Done |
| Feedback Form | 4 | 4 | ✓ Done |
| Session / Access Control | 0 | N/A | ✓ Done |
| URL Copy-Paste & Mid-Flow Navigation | 2 | 2 | ✓ Done |

All user-facing attack surfaces have been tested with every practical input combination. Vulnerabilities found were mitigated by enhancing the codebase before moving on to the next area.

---

### Code Audit — Verified Implementation (2026-03-27)

A full read of all source files was conducted to confirm every mitigation is actually present in the current code. Results below.

#### `routes/feedback_routes.py`
| Check | Status | Evidence |
|-------|--------|----------|
| `@login_required` on GET `/feedback-page` | ✓ Confirmed | Line 10 |
| `@login_required` on POST `/feedback` | ✓ Confirmed | Line 16 |
| `login_required` imported from `flask_login` | ✓ Confirmed | Line 2 |

#### `routes/auth.py`
| Check | Status | Evidence |
|-------|--------|----------|
| Brute-force lockout after 5 failed attempts | ✓ Confirmed | `MAX_LOGIN_ATTEMPTS = 5`, line 11 |
| 5-minute lockout timer | ✓ Confirmed | `LOCKOUT_TIME = timedelta(minutes=5)`, line 12 |
| Generic error message for wrong username (no enumeration) | ✓ Confirmed | `"Invalid credentials."` shown regardless of whether user exists |
| Password policy: 8+ chars, uppercase, number, symbol | ✓ Confirmed | `password_ok()` lines 15–24 |
| Password must not contain first/last name | ✓ Confirmed | Lines 60–65 |
| Confirm password match check | ✓ Confirmed | Lines 52–54 |
| Reset token generated with `secrets.token_hex(16)` | ✓ Confirmed | Line 176 |
| `reset_step` state machine enforces page ordering across all reset routes | ✓ Confirmed | Lines 175, 195, 242, 266 |
| `session.clear()` after successful password reset | ✓ Confirmed | Line 292 |
| Security question attempts limited to 3 | ✓ Confirmed | Lines 223–229 |
| `session.clear()` on exceeding security question attempts | ✓ Confirmed | Line 227 |
| `@login_required` on logout route | ✓ Confirmed | Line 152 |

#### `models.py`
| Check | Status | Evidence |
|-------|--------|----------|
| Passwords stored as bcrypt hash, never plaintext | ✓ Confirmed | `set_password()` uses `bcrypt.generate_password_hash()` |
| `check_password()` uses bcrypt comparison | ✓ Confirmed | `bcrypt.check_password_hash()` |
| SQLAlchemy ORM used (no raw SQL) | ✓ Confirmed | All queries via `User.query.filter_by()` — parameterized |
| `failed_logins` and `last_login` tracked in DB | ✓ Confirmed | Lines 26–27 |

#### `app.py`
| Check | Status | Evidence |
|-------|--------|----------|
| `@login_required` on `/dashboard` | ✓ Confirmed | Line 42 |
| `LoginManager.login_view` set to redirect unauthenticated users to login | ✓ Confirmed | `login_manager.login_view = "auth.login"` line 22 |
| Home route redirects based on auth state | ✓ Confirmed | `current_user.is_authenticated` check line 37 |

#### `config.py`
| Check | Status | Evidence |
|-------|--------|----------|
| `SESSION_COOKIE_HTTPONLY = True` | ✓ Confirmed | Line 9 — cookie not accessible via JavaScript |
| `SESSION_COOKIE_SAMESITE = "Lax"` | ✓ Confirmed | Line 10 — CSRF protection for cross-site requests |
| `SESSION_COOKIE_SECURE = False` | ⚠ Expected for dev | Line 11 — HTTP only; must be set to `True` in production (HTTPS) |

> **Note on `SESSION_COOKIE_SECURE`:** Currently `False` because the app runs on HTTP locally. This is correct for development. In a production deployment over HTTPS this must be changed to `True`, otherwise the session cookie could be transmitted over unencrypted connections — violating **CWE-614: Sensitive Cookie in HTTPS Session Without Secure Attribute**.

---

### CWE / CVE Resolution Log

This section records every CWE addressed in the codebase, confirmed by code audit.

| CWE ID | Name | Where Fixed | How | Status |
|--------|------|-------------|-----|--------|
| CWE-287 | Improper Authentication | `feedback_routes.py` lines 10, 16 | `@login_required` on both feedback routes | ✓ Resolved |
| CWE-306 | Missing Authentication for Critical Function | `feedback_routes.py` lines 10, 16 | Both GET and POST routes require active session | ✓ Resolved |
| CWE-307 | Improper Restriction of Excessive Authentication Attempts | `auth.py` lines 107–115 | Lockout after 5 failed logins, 5-min timer | ✓ Resolved |
| CWE-521 | Weak Password Requirements | `auth.py` lines 15–24 | Enforces 8+ chars, uppercase, number, symbol | ✓ Resolved |
| CWE-620 | Unverified Password Change | `auth.py` lines 262–267 | Reset requires `reset_user` + `reset_token` + `reset_verified` — all three must be present in session | ✓ Resolved |
| CWE-288 | Authentication Bypass Using an Alternate Path | `auth.py` all reset routes | `reset_step` state machine enforces strict ordering: each page requires the correct step value set by the previous page only | ✓ Resolved |
| CWE-613 | Insufficient Session Expiration | `auth.py` line 291 | `session.clear()` after reset; session cleared on lockout too | ✓ Resolved (reset flow) |
| CWE-598 | Use of GET Request Method With Sensitive Query Strings | `auth.py` | All sensitive operations use POST | ✓ Resolved |
| CWE-209 | Information Exposure Through an Error Message | `auth.py` line 132 | Generic "Invalid credentials." regardless of whether user exists | ✓ Resolved |
| CWE-916 | Use of Password Hash With Insufficient Computational Effort | `models.py` lines 31–34 | bcrypt used for all password hashing | ✓ Resolved |
| CWE-89 | SQL Injection | `models.py` / all routes | SQLAlchemy ORM with parameterized queries throughout | ✓ Resolved |
| CWE-1004 | Sensitive Cookie Without HttpOnly Flag | `config.py` line 9 | `SESSION_COOKIE_HTTPONLY = True` | ✓ Resolved |
| CWE-352 | Cross-Site Request Forgery (CSRF) | `config.py` line 10 | `SESSION_COOKIE_SAMESITE = "Lax"` | ⚠ Partial — SameSite=Lax mitigates most CSRF; full protection requires CSRF tokens (Flask-WTF) |
| CWE-614 | Sensitive Cookie in HTTPS Session Without Secure Attribute | `config.py` line 11 | `SESSION_COOKIE_SECURE = False` (dev only) | ⚠ Pending — must be `True` in production |

---

## Part 2: Attacker Testing

Attacker testing was conducted by simulating the 13 threats identified in the security analyst's threat model. Each threat was tested against the current codebase. Results show whether the threat is fully mitigated, partially mitigated, or still open.

---

### Threat 1 — Valid Username Enumeration
**CWE-203 / CWE-204: Information Exposure Through Discrepancy**

#### Description
An attacker observes system responses to determine whether a username exists. Different error messages for "wrong username" vs "wrong password" reveal which usernames are registered.

#### Tests performed
| Test | Input | Expected | Result |
|------|-------|----------|--------|
| Login with non-existent username | `notauser` / any password | Generic error | ✓ "Invalid credentials." |
| Login with real username + wrong password | `Bahari` / `wrongpass` | Generic error | ✓ "Invalid credentials. 4 attempts remaining." |
| Verify username (reset flow) with unknown username | `ghost` | Generic error | ✓ "If that username exists, you will be prompted to answer a security question." |
| Verify username (reset flow) with valid username | `Bahari` | Advance to security question | ✓ Redirects to security question page |

#### Finding
Login and reset flow both now return identical, non-revealing responses regardless of whether the username exists. Fixed on 2026-03-31 — `/verify_username` now always shows the same info message and stays on the same page whether the username is valid or not.

#### Status: ✓ Mitigated
- Login: ✓ Mitigated — generic message
- Reset flow (`/verify_username`): ✓ Mitigated — same response regardless of username validity

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-203 | Observable Discrepancy | ✓ Resolved — generic message on both login and reset flow |

---

### Threat 2 — Password Guessing / Brute Force
**CWE-307: Improper Restriction of Excessive Authentication Attempts**

#### Description
Attacker submits repeated login attempts with different passwords until gaining access.

#### Tests performed
| Test | Action | Expected | Result |
|------|--------|----------|--------|
| 5 consecutive wrong passwords | Manual login attempts | Lockout triggered | ✓ Locked after 5 |
| Login attempt while locked | Attempt before timer | Blocked with time shown | ✓ "Account locked. Try again in X minute(s)." |
| Wait out lockout, retry | Wait 5 mins, attempt | Unlocked | ✓ Access restored |
| Trigger lockout again (2nd time) | 5 more wrong attempts | Longer lockout | ✓ 15 min lockout (× 3 multiplier) |
| Trigger lockout 3rd time | 5 more wrong attempts | Even longer | ✓ 60 min lockout (× 4 multiplier) |

#### Finding
Progressive lockout is fully implemented. Each successive lockout tier is longer (5 → 15 → 60 → 300 mins). Failed attempts counter resets on each lockout so the 5-attempt window restarts each tier.

#### Status: ✓ Mitigated

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-307 | Improper Restriction of Excessive Authentication Attempts | ✓ Resolved — progressive lockout |

---

### Threat 3 — Stored Credentials in Database
**CWE-522: Insufficiently Protected Credentials**

#### Description
Credentials stored in plaintext are exposed if the database is compromised.

#### Tests performed
| Test | Method | Expected | Result |
|------|--------|----------|--------|
| Inspect `password_hash` column directly in DB | `sqlite3` query | Bcrypt hash | ✓ `$2b$12$...` — bcrypt hash |
| Inspect `security_answer1/2/3` columns | `sqlite3` query | Bcrypt hash | ✓ All `$2b$12$...` after migration |
| Attempt to reverse a bcrypt hash | Manual inspection | Not reversible | ✓ Bcrypt with salt — not reversible |

#### Finding
All passwords and security answers are stored as bcrypt hashes. Plaintext is never written to the database. Pre-existing users with plaintext security answers were migrated (2026-03-29).

#### Status: ✓ Mitigated

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-522 | Insufficiently Protected Credentials | ✓ Resolved — bcrypt for passwords and security answers |
| CWE-256 | Plaintext Storage of a Password | ✓ Resolved — bcrypt hashing applied to all credential fields |
| CWE-916 | Use of Password Hash With Insufficient Computational Effort | ✓ Resolved — bcrypt (work factor 12) used |

---

### Threat 4 — Password Recovery Abuse
**CWE-640: Weak Password Recovery Mechanism for Forgotten Password**

#### Description
The password recovery mechanism is weak — answers may be generic, and unlimited attempts allow brute force of security questions.

#### Tests performed
| Test | Action | Expected | Result |
|------|--------|----------|--------|
| Answer security question incorrectly 3 times | Submit wrong answer × 3 | Session cleared, redirect to login | ✓ Blocked after 3 attempts |
| Paste `/security_question` directly without going through `/verify_username` | URL paste | Redirect to login | ✓ `reset_step` check blocks it |
| Paste `/reset_password` after only completing `/verify_username` | URL paste | Redirect to login | ✓ `reset_step` requires `"reset_password"` value |
| Complete full flow then replay `/reset_password` URL | URL paste after reset | Blocked | ✓ `session.clear()` invalidates all keys |
| Answer question correctly on first try | Submit correct answer | Advance to reset | ✓ Works |

#### Finding
The `reset_step` state machine enforces strict page ordering. Attempts limit (3) is enforced per question. However, only **1 out of 3** security questions is asked — the analyst recommends requiring all questions. This remains an open weakness.

#### Status: ⚠ Partial
- Step ordering and attempt limiting: ✓ Mitigated
- Only 1 question asked (not all 3): ✗ Open — answers to a single question may be guessable

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-640 | Weak Password Recovery Mechanism | ⚠ Partial — flow is protected but only 1 of 3 questions asked |
| CWE-288 | Authentication Bypass Using an Alternate Path | ✓ Resolved — `reset_step` state machine |

---

### Threat 5 — Credential Stuffing
**CWE-307: Improper Restriction of Excessive Authentication Attempts**

#### Description
Attackers use leaked username/password pairs from other breaches to gain access.

#### Tests performed
| Test | Action | Expected | Result |
|------|--------|----------|--------|
| Attempt login with common weak credentials | `admin/admin`, `test/password123` | Blocked by lockout after 5 tries | ✓ Locked out after 5 failed attempts |
| Register with a weak password | `password1` (no symbol) | Rejected | ✓ Blocked by `password_ok()` |
| Register with name in password | `Bahari123!` | Rejected | ✓ Blocked — name detected in password |
| Register with username in password | `Bobby@123` (username = Bobby) | Rejected | ✓ Blocked — username detected |

#### Finding
Strong password requirements at registration reduce the likelihood that user passwords appear in common leaked credential lists. Progressive lockout limits the speed of stuffing attempts. No IP-level rate limiting or CAPTCHA exists, so automated tools could still cycle through usernames before triggering per-account lockouts.

#### Status: ⚠ Partial
- Password strength enforcement: ✓ Mitigated
- Per-account lockout: ✓ Mitigated
- IP-level rate limiting: ✗ Not implemented — automated tooling can target many accounts in parallel

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-307 | Improper Restriction of Excessive Authentication Attempts | ⚠ Partial — per-account lockout exists, no IP-level limiting |
| CWE-521 | Weak Password Requirements | ✓ Resolved — enforced at registration and reset |

---

### Threat 6 — SQL Injection
**CWE-89: SQL Injection**

#### Description
Attacker injects SQL syntax into input fields to manipulate database queries.

#### Tests performed
| Test | Input | Field | Expected | Result |
|------|-------|-------|----------|--------|
| Classic OR injection | `' OR '1'='1` | Username (login) | Rejected / no effect | ✓ No effect — ORM parameterized |
| Comment injection | `admin'--` | Username (login) | Rejected / no effect | ✓ No effect |
| Tautology in password | `' OR 1=1--` | Password (login) | Rejected | ✓ No effect |
| SQL in feedback message | `'; DROP TABLE feedback;--` | Feedback message | Stored as literal text | ✓ Stored safely — no execution |
| SQL in email field | `test@test.com'; DROP TABLE users;--` | Email (feedback) | Rejected or sanitized | ✓ Sanitizer strips it; email validator rejects format |

#### Finding
All database queries use SQLAlchemy ORM with parameterized queries — no raw SQL strings anywhere in the codebase. SQL injection is fully mitigated at the data access layer. Sanitizer (`Sanitizer.sanitize_text()`) provides an additional layer on feedback fields.

#### Status: ✓ Mitigated

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-89 | SQL Injection | ✓ Resolved — SQLAlchemy ORM, parameterized queries throughout |

---

### Threat 7 — Oversized Input
**CWE-20: Improper Input Validation**

#### Description
Attacker submits unexpectedly large or malformed input to crash the system or cause unintended behavior.

#### Tests performed
| Test | Input | Field | Expected | Result |
|------|-------|-------|----------|--------|
| 2001-character message | Paste 2001 chars | Feedback message | Blocked | ✓ `maxlength="2000"` hard-caps in browser; server-side `MAX_MESSAGE_LENGTH=2000` also enforced |
| 256-character email | 256-char string@domain | Email | Rejected | ✓ `MAX_EMAIL_LENGTH=255` enforced |
| 101-character name | 101 chars | Feedback name (now username) | Rejected | ✓ `MAX_NAME_LENGTH=100` enforced |
| Empty message | Submit blank message | Blocked | ✓ `required` attribute + server validation |
| Extremely long username at registration | 500-char username | Username | Accepted (no server limit) | ✗ No max length on username field |

#### Finding
Feedback fields are well-protected with both client-side (`maxlength`) and server-side (`MAX_*_LENGTH`) limits. However, the username field at registration has no maximum length enforced server-side — a very long username would be accepted and stored.

#### Status: ⚠ Partial
- Feedback fields: ✓ Mitigated
- Username field: ✗ No maximum length enforced

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-20 | Improper Input Validation | ⚠ Partial — feedback protected, username max length missing |

---

### Threat 8 — CSRF Attack (Login / Register / Reset)
**CWE-352: Cross-Site Request Forgery**

#### Description
Attacker tricks an authenticated user into submitting an unintended request (e.g. password change) from a malicious page.

#### Tests performed
| Test | Method | Expected | Result |
|------|--------|----------|--------|
| Inspect session cookie `SameSite` attribute | Browser DevTools → Application → Cookies | `SameSite=Lax` | ✓ Confirmed |
| Simulate cross-origin POST to `/feedback` | Cross-origin form submit (different origin) | Blocked by SameSite | ✓ Browser blocks cross-site cookie sending with `Lax` |
| Check for CSRF tokens in any form | View page source of login, register, reset forms | Token present or absent | ✗ No CSRF tokens in any form | 

#### Finding
`SESSION_COOKIE_SAMESITE = "Lax"` provides partial CSRF protection — the browser will not send the session cookie on cross-site POST requests initiated by third-party pages in most modern browsers. However, `Lax` does not cover all CSRF vectors (e.g. top-level navigations with GET, or older browsers). No CSRF tokens (Flask-WTF) are implemented.

#### Status: ⚠ Partial
- `SameSite=Lax` cookie: ✓ Mitigates most CSRF in modern browsers
- CSRF tokens (Flask-WTF): ✗ Not implemented — full protection requires tokens

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-352 | Cross-Site Request Forgery | ⚠ Partial — SameSite=Lax mitigates most; no CSRF tokens |

---

### Threat 9 — Forge Session Cookies
**CWE-565: Reliance on Cookies Without Validation and Integrity Checking**

#### Description
If the `SECRET_KEY` is weak or exposed, an attacker can forge a valid Flask session cookie and impersonate any user.

#### Tests performed
| Test | Method | Expected | Result |
|------|--------|----------|--------|
| Inspect `SECRET_KEY` in config | Read `config.py` | Strong random key | ✗ `"dev-secret-change-me"` fallback hardcoded |
| Inspect `.env` file SECRET_KEY value | Read `.env` | Long random string | ✗ Value is `3414690219112` — short, numeric only |
| Attempt to forge session cookie using known key | Use `flask-unsign` with known key | Cookie accepted | ✓ (Theoretical) — weak key makes this feasible |

#### Finding
The `SECRET_KEY` in `.env` is `3414690219112` — only 13 characters, entirely numeric, and predictable. The fallback in `config.py` is `"dev-secret-change-me"` — also weak and publicly known. An attacker who knows or guesses the key can use tools like `flask-unsign` to forge session cookies and impersonate any user including setting `user_id` to an admin account.

#### Status: ✗ Not Mitigated

#### Mitigation required
Replace `SECRET_KEY` with a cryptographically random value:
```python
import secrets
print(secrets.token_urlsafe(32))
```
Store the result in `.env` and remove the hardcoded fallback in `config.py`.

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-565 | Reliance on Cookies Without Validation | ✗ Open — weak SECRET_KEY allows cookie forgery |
| CWE-321 | Use of Hard-coded Cryptographic Key | ✗ Open — fallback key hardcoded in config.py |

---

### Threat 10 — Session Hijacking
**CWE-384: Session Fixation / Session Hijacking**

#### Description
Attacker steals a valid session cookie from an authenticated user and replays it in their own browser to impersonate the victim.

#### Tests performed
| Test | Method | Expected | Result |
|------|--------|----------|--------|
| Copy session cookie from DevTools, paste into different browser | Browser DevTools → copy `session` cookie value → set in new browser | Access granted as victim | ✓ Access granted — session cookie replayed successfully |
| Check if session ID regenerates after login | Compare cookie before and after login | New cookie issued | ✗ Flask does not regenerate session on login by default |
| Check `HttpOnly` flag on session cookie | Browser DevTools → Application → Cookies | `HttpOnly` = true | ✓ Confirmed — JS cannot read the cookie |
| Check `Secure` flag | DevTools | `Secure` = true | ✗ `SESSION_COOKIE_SECURE = False` — cookie sent over HTTP |
| Logout and replay old cookie | Copy cookie before logout, paste after logout | Session invalid | ✗ `logout_user()` clears client-side only — server does not invalidate the token |

#### Finding
Session hijacking via cookie replay is possible. The `HttpOnly` flag prevents JavaScript from reading the cookie, but the `Secure` flag is off (dev only), meaning cookies travel over plain HTTP. Flask's default session implementation is stateless (signed cookie) — `logout_user()` only clears the client-side cookie; if an attacker copied the cookie before logout, it remains valid until the `SECRET_KEY` changes or the cookie expires.

#### Status: ⚠ Partial
- `HttpOnly`: ✓ Mitigated — JS cannot steal cookie
- `Secure` flag: ✗ Off (dev) — must be `True` in production
- Session regeneration on login: ✗ Not implemented
- Server-side session invalidation on logout: ✗ Not possible with Flask's default signed-cookie sessions

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-384 | Session Fixation | ✗ Open — session ID not regenerated after login |
| CWE-613 | Insufficient Session Expiration | ✗ Open — logout does not invalidate cookie server-side |
| CWE-614 | Sensitive Cookie Without Secure Flag | ⚠ Dev only — must be True in production |
| CWE-1004 | Sensitive Cookie Without HttpOnly Flag | ✓ Resolved — HttpOnly=True |

---

### Threat 11 — Exploit Insecure Cookie / Debug Configuration
**CWE-16: Configuration**

#### Description
Insecure configuration settings (debug mode, insecure cookies) expose internal details and increase attack surface.

#### Tests performed
| Test | Method | Expected | Result |
|------|--------|----------|--------|
| Trigger a runtime error while app is running | Navigate to a broken URL / submit bad data | Generic error page in production | ✗ `debug=True` in `app.py` — full Werkzeug stack trace shown |
| Attempt to access Werkzeug interactive debugger | Trigger error, click console icon on error page | PIN required | ✓ PIN required (but PIN can be computed if attacker has server access) |
| Check `SESSION_COOKIE_SECURE` | Config + DevTools | `True` in production | ✗ `False` hardcoded — must be env-toggled |

#### Finding
`debug=True` is hardcoded in `app.py`. In a production or shared environment this exposes full stack traces, source code snippets, and the Werkzeug interactive debugger (which allows arbitrary Python execution with the right PIN). `SESSION_COOKIE_SECURE = False` means session cookies are sent over plain HTTP.

#### Status: ✗ Not Mitigated (for production)

#### Mitigation required
```python
# app.py
app.run(debug=os.getenv("FLASK_ENV") == "development")

# config.py
SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") != "development"
```

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-16 | Configuration | ✗ Open — debug=True hardcoded, SECURE cookie off |
| CWE-215 | Information Exposure Through Debug Information | ✗ Open — stack traces exposed via debug mode |
| CWE-614 | Sensitive Cookie in HTTPS Session Without Secure Attribute | ⚠ Dev only — must be True in production |

---

### Threat 12 — Malicious / Spam Feedback Submission
**CWE-400: Uncontrolled Resource Consumption**

#### Description
Attacker submits excessive or malicious content through the feedback form to consume resources or flood the database.

#### Tests performed
| Test | Action | Expected | Result |
|------|--------|----------|--------|
| Submit feedback 5 times in one day | Submit feedback × 5 | 5th succeeds, 6th blocked | ✓ Blocked: "You have reached the maximum of 5 feedback submissions." |
| Submit feedback on day 2 | Submit after midnight | Counter resets | ✓ `feedback_date` check resets count on new calendar day |
| Submit 2000-character message | Paste max content | Accepted at limit | ✓ Accepted — within limit |
| Submit 2001-character message | Bypass `maxlength` via curl/Postman | Rejected server-side | ✓ Rejected — `MAX_MESSAGE_LENGTH=2000` enforced server-side |
| Submit XSS payload in message | `<script>alert(1)</script>` | Sanitized or stored as text | ✓ `Sanitizer.sanitize_text()` strips HTML tags |
| Access feedback page without login | Paste URL in different browser | Redirect to login | ✓ `@login_required` on both routes |

#### Finding
Feedback spam is well-controlled. Per-user daily limit (5/day), message length cap (2000 chars), and authentication requirement all prevent abuse. Sanitizer strips HTML/script tags before storage.

#### Status: ✓ Mitigated

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-400 | Uncontrolled Resource Consumption | ✓ Resolved — 5/day limit, 2000-char cap, auth required |
| CWE-770 | Allocation of Resources Without Limits or Throttling | ✓ Resolved — daily submission cap implemented |

---

### Threat 13 — CSRF on Feedback Submission
**CWE-352: Cross-Site Request Forgery (Feedback)**

#### Description
Attacker tricks an authenticated user into submitting feedback from a malicious external page.

#### Tests performed
| Test | Method | Expected | Result |
|------|--------|----------|--------|
| Cross-origin POST to `/feedback` | Simulate cross-origin form with valid session | Blocked by SameSite | ✓ `SameSite=Lax` prevents cross-site cookie |
| Check for CSRF token in feedback form | View source of `feedback.html` | Token field present | ✗ No CSRF token in form |

#### Finding
Same as Threat 8 — `SameSite=Lax` provides partial protection. No CSRF tokens implemented. For the feedback form specifically, a successful CSRF attack would allow an attacker to submit feedback on behalf of a logged-in user from an external page (in browsers that don't enforce `Lax` strictly, or via same-site subdomains).

#### Status: ⚠ Partial

#### CWE reference
| CWE ID | Name | Status |
|--------|------|--------|
| CWE-352 | Cross-Site Request Forgery | ⚠ Partial — SameSite=Lax only; no CSRF tokens |

---

### Part 2 Summary

| # | Threat | CWE | Status |
|---|--------|-----|--------|
| 1 | Username Enumeration | CWE-203 | ✓ Mitigated — generic message on login and reset flow |
| 2 | Password Guessing / Brute Force | CWE-307 | ✓ Mitigated — progressive lockout |
| 3 | Stored Credentials in DB | CWE-522 | ✓ Mitigated — bcrypt everywhere |
| 4 | Password Recovery Abuse | CWE-640 | ⚠ Partial — flow protected, only 1 of 3 questions asked |
| 5 | Credential Stuffing | CWE-307 | ⚠ Partial — per-account lockout, no IP-level limiting |
| 6 | SQL Injection | CWE-89 | ✓ Mitigated — SQLAlchemy ORM throughout |
| 7 | Oversized Input | CWE-20 | ⚠ Partial — feedback protected, username has no max length |
| 8 | CSRF (Auth Forms) | CWE-352 | ⚠ Partial — SameSite=Lax only, no CSRF tokens |
| 9 | Forge Session Cookies | CWE-565 | ✗ Not Mitigated — weak SECRET_KEY |
| 10 | Session Hijacking | CWE-384 | ⚠ Partial — HttpOnly set, Secure off, no server-side invalidation |
| 11 | Insecure Configuration | CWE-16 | ✗ Not Mitigated — debug=True, SECURE cookie off |
| 12 | Spam / Malicious Feedback | CWE-400 | ✓ Mitigated — 5/day limit, length cap, auth required |
| 13 | CSRF (Feedback) | CWE-352 | ⚠ Partial — SameSite=Lax only, no CSRF tokens |

**Legend:** ✓ Mitigated &nbsp;|&nbsp; ⚠ Partial &nbsp;|&nbsp; ✗ Not Mitigated

### Open items requiring further action
| Priority | Issue | Fix |
|----------|-------|-----|
| Critical | Weak `SECRET_KEY` (Threat 9) | Generate with `secrets.token_urlsafe(32)`, store in `.env` |
| High | `debug=True` hardcoded (Threat 11) | Toggle via `FLASK_ENV` environment variable |
| High | No CSRF tokens (Threats 8, 13) | Implement Flask-WTF `CSRFProtect` |
| Medium | `/verify_username` enumerates usernames (Threat 1) | ✓ Fixed — generic message regardless of outcome |
| Medium | Only 1 of 3 security questions asked (Threat 4) | Require answers to all 3 |
| Medium | No IP-level rate limiting (Threat 5) | Implement `flask-limiter` |
| Low | Username field has no max length (Threat 7) | Add `maxlength` to HTML input + server-side check |
| Low | `SESSION_COOKIE_SECURE = False` (Threat 10, 11) | Set `True` in production via env toggle |

---

---

## Changelog

### 2026-03-29

#### Security answers now hashed with bcrypt (CWE-256)

**Issue:** Security answers (pet name, school, city) were stored as plaintext in the database. Any database breach would instantly expose all answers, allowing full account takeover via password reset.

**Fix:**
- Added `set_security_answers()` to `User` model — hashes all 3 answers with bcrypt before storing
- Added `check_security_answer()` to `User` model — uses `bcrypt.check_password_hash()` for verification
- Registration now calls `set_security_answers()` instead of assigning raw strings
- Security question route now stores the field name (`answer1/2/3`) in session instead of the plaintext answer — the hash never enters the session
- `check_security_answer()` wrapped in `try/except ValueError` so a non-bcrypt value (legacy plaintext) never crashes Flask — returns `False` safely
- **DB migration:** All 5 pre-existing users with plaintext answers were updated via a one-time Python script using the `secapp` conda environment

**CWE resolved:** CWE-256 (Plaintext Storage of a Password)

---

#### Database column reorder — first_name, last_name moved to columns 1 & 2

**Issue:** `first_name` and `last_name` were the last columns in the `users` table, placed after all other fields.

**Fix:** Recreated the `users` table with `first_name` and `last_name` as columns 1 and 2 (right after `id`) using SQLite's create-copy-drop-rename migration pattern. All existing data preserved.

---

#### Feedback form — name field removed, username auto-filled from session

**Issue:** The feedback form had a free-text "Your Name" field. There was no reason to ask for it since the user is already logged in.

**Fix:**
- Removed the name input from `feedback.html`
- `username` is now pulled directly from `current_user` in `feedback_routes.py` and stored in the DB
- `Feedback` model updated: replaced `name` column with `username` (linked to logged-in user)

---

#### Feedback submission limit — 5 per user per day (DDoS prevention)

**Issue:** A logged-in user could submit unlimited feedback entries, making the endpoint a potential DoS vector against the database.

**Fix:**
- Added `feedback_count` (Integer) and `feedback_date` (Date) columns to the `users` table
- On each submission, the route checks if `feedback_date` matches today — if not (new day), `feedback_count` resets to 0
- Submissions blocked with an error message once `feedback_count >= 5`
- Count increments in `FeedbackService.create_feedback()` after a successful insert

**CWE resolved:** CWE-770 (Allocation of Resources Without Limits or Throttling)

---

#### Account lockout now uses `locked_until` correctly

**Issue:** The lockout check was using `last_login` to calculate the lockout window — semantically wrong, since `last_login` is updated on every failed attempt and has a different purpose. The `locked_until` column existed in the model but was never written to.

**Fix:**
- Lockout check now reads `locked_until` directly: if `locked_until > now`, block login
- On 5th failed attempt: `locked_until = now + lockout_duration` is written to DB
- On expiry: `locked_until` is reset to `NULL` and `failed_logins` reset to `0`

---

#### Progressive lockout — brute force escalation

**Issue:** Lockout was a flat 5 minutes regardless of how many times an attacker had been locked out before.

**Fix:** Implemented progressive lockout with an escalating multiplier:

| Lockout # | Multiplier | Duration |
|---|---|---|
| 1st | — | 5 mins |
| 2nd | × 3 | 15 mins |
| 3rd | × 4 | 60 mins |
| 4th | × 5 | 300 mins |

- Added `lockout_count` (Integer) and `last_lockout_minutes` (Integer) columns to `users` table
- `get_lockout_duration(lockout_count, last_minutes)` computes next duration: 1st lockout = 5 mins base; each subsequent = `previous × (lockout_count + 2)`
- `last_lockout_minutes` stores the previous duration so the next lockout always multiplies from the correct value
- Lockout flash message now shows the actual duration in minutes

**CWE resolved:** CWE-307 (Improper Restriction of Excessive Authentication Attempts) — enhanced

---

### 2026-03-30

#### Password reset — password must not contain username

**Issue:** The name-in-password check (first/last name) was applied at registration but not at password reset. Additionally, neither registration nor reset blocked passwords containing the username itself.

**Fix:**
- Registration: added username check — `if username.lower() in password.lower()` → blocked
- Reset password: added both name check and username check using the `user` object already loaded from session

---

#### Feedback form — email icon alignment fix

**Issue:** When the red email validation error label appeared below the email input, the envelope icon shifted downward because it was vertically centered relative to the entire `.input-box` container (which grew taller when the error text appeared).

**Fix:**
- Icon positioned with `top: 22px` (fixed, tied to input height) instead of `top: 50%`
- Error span changed from `display: none/block` to `visibility: hidden/visible` — span always occupies space in the layout so the box height never changes, keeping the icon position stable

---

#### Feedback form — `name` column removed from DB, `user_id` removed

**Issue:** After replacing the name field with username, the DB still had the old `name` column as `NOT NULL`, causing every feedback insert to fail with an integrity error (showing "Unexpected error occurred"). Also, `user_id` was added but created a confusing extra column in the viewer.

**Fix:**
- Recreated `feedback` table with columns: `id, username, email, message, created_at` — `name` and `user_id` both removed
- All existing rows migrated; old `name` values preserved via `COALESCE(username, name, 'unknown')` during migration

---

#### Feedback daily limit — resets each calendar day

**Issue:** `feedback_count` was a lifetime counter — once a user hit 5 submissions, they were permanently blocked.

**Fix:**
- Added `feedback_date` (Date) column to `users` table
- On every submission attempt, if `feedback_date != today`, count resets to 0 and date updates to today
- Users now get exactly 5 submissions per calendar day; the counter auto-resets at midnight

---

*Branch: Bahari | Tester: M. A. Bahari | Last updated: 2026-03-30*
