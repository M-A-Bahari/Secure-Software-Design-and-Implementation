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

> **To be completed.** Tests below are planned. Results will be filled in as each is executed.

---

### 2.1 Session Hijacking / Session Fixation

> **To be completed.**

#### What will be tested
- Stealing a valid session cookie (e.g. via browser dev tools) and replaying it in a different browser to impersonate the logged-in user
- Attempting session fixation: forcing a known session ID before login and checking if it is accepted after authentication
- Checking whether the session ID changes after login (session regeneration)
- Inspecting cookie flags (`HttpOnly`, `Secure`, `SameSite`) using browser dev tools and a proxy (e.g. Burp Suite)
- Testing whether the session is invalidated server-side on logout, or just cleared client-side

#### Relevant CWE references
| CWE ID | Name | What to look for |
|--------|------|------------------|
| CWE-384 | Session Fixation | Does the session ID rotate after login? |
| CWE-613 | Insufficient Session Expiration | Is the session invalidated server-side on logout? |
| CWE-1004 | Sensitive Cookie Without HttpOnly Flag | Can JS read the session cookie? |
| CWE-614 | Sensitive Cookie Without Secure Flag | Is the cookie sent over HTTP? (dev only) |

#### Results
> Pending.

---

### 2.2 SQL Injection

> **To be completed.**

---

### 2.3 Cross-Site Scripting (XSS)

> **To be completed.**

---

### 2.4 Cross-Site Request Forgery (CSRF)

> **To be completed.**

---

### 2.5 Privilege Escalation

> **To be completed.**

---

### 2.6 Username / User Enumeration

> **To be completed.**

---

### 2.7 Automated Brute-Force Tooling

> **To be completed.**

---

*Branch: Bahari | Tester: M. A. Bahari | Last updated: 2026-03-27*
