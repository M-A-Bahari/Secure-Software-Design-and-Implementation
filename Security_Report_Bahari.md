# CS4417 — Secure Software Design and Implementation
# Security Report: Flask Web Application
**Student:** M. A. Bahari
**Date:** April 1, 2026

---

## Abstract

This report documents the security design, threat modeling, and implementation of a Flask-based web application built for the CS4417 course. The application supports user registration, authenticated login, a security-question-based password reset flow, and a rate-limited feedback form. The project followed an Agile Security Development Lifecycle (SDL) hybrid approach, in which security controls were integrated at every iteration rather than applied retroactively. A total of thirteen distinct threats were identified through pre-implementation threat modeling, each mapped to one or more entries in the Common Weakness Enumeration (CWE) catalog. Controls implemented include bcrypt password hashing with work factor 12, progressive account lockout, session fixation prevention via `session.clear()`, parameterized database queries through the SQLAlchemy ORM, a `reset_step` state machine enforcing correct page ordering in the password reset flow, and per-user daily submission limits on the feedback form. The project was validated through two structured testing phases. All thirteen threats were addressed; seven were fully mitigated, four were partially mitigated by design owing to the local development scope, and two were explicitly deferred as out-of-scope for a non-publicly-hosted environment.

---

## 1. Justification for the Choice of SDLC

The Software Development Lifecycle (SDLC) selected for this project is an Agile-SDL hybrid, drawing from Microsoft's Security Development Lifecycle and adapting its phases to an iterative, sprint-based delivery model. The rationale for this choice is grounded in both the pedagogical objectives of the course and the practical realities of a small, solo-developer project with a defined set of features.

**Why not a purely waterfall SDL?** The traditional SDL as described by Microsoft assumes large teams, dedicated security reviews between formal phases, and the ability to halt development for comprehensive threat model reviews before any code is written. For a project of this scale, a pure waterfall approach would introduce unnecessary overhead and, more critically, would delay security feedback until a late gate review. In contrast, the Agile-SDL hybrid treats each feature as its own mini-cycle: requirements are gathered, a local threat model is constructed, the feature is implemented, security controls are applied, and testing validates the control before the next feature begins.

**Alignment with the project structure.** The application was developed feature by feature: registration, login (with lockout), password reset, feedback, and session hardening. For each feature, a set of relevant threats was identified in advance by the security analyst. This mirrors the Agile-SDL practice of per-sprint threat modeling, where the threat model is a living document rather than a single upfront artifact. The progressive lockout mechanism, for example, was conceived during the login sprint's threat modeling session and implemented before the sprint closed, rather than being retrofitted after all features were complete.

**Security requirements as acceptance criteria.** In the Agile-SDL hybrid, security requirements are treated as first-class acceptance criteria for each user story. For the login story, acceptance criteria included: generic error messages (anti-enumeration), account lockout after five consecutive failures, and bcrypt-hashed credential storage. A feature was not considered complete until all security acceptance criteria passed. This approach ensures that security is never deferred to a future sprint.

**Threat modeling before implementation.** Before a single line of authentication code was written, an attack tree was constructed for the login endpoint. This pre-implementation modeling identified brute force (CWE-307), username enumeration (CWE-203), and session fixation (CWE-384) as the primary risks, allowing their mitigations to be coded as part of the original implementation rather than as patches. OWASP's threat modeling guidance and NIST SP 800-63B's authentication assurance levels informed this early design work.

**Testing integrated into the cycle.** The Agile-SDL hybrid mandates that security testing occurs within the same iteration as implementation. This project formalizes that with two distinct testing phases: a functional user-testing phase and a dedicated attacker-testing phase. Both phases are described in Section 9. This dual-phase testing is consistent with the Agile-SDL's "verify" and "release" stages, compressed into a practical timeline appropriate for a course project.

Overall, the Agile-SDL hybrid was the most appropriate model because it enabled continuous security integration without the ceremonial overhead of a full SDL, while still ensuring that every feature shipped with documented threat coverage, implemented controls, and verified mitigations.

---

## 2. Attack Surface and Attack Trees

### 2.1 Attack Surface Analysis

The attack surface of the application encompasses every externally reachable endpoint and every trust boundary at which untrusted data crosses into the application.

**Authentication endpoints (`/login`, `/register`).** These are the highest-risk endpoints. They accept user-supplied credentials over HTTP POST, interact directly with the user database, and control access to all authenticated functionality. Threats include password guessing, credential stuffing, username enumeration, and SQL injection through form fields.

**Password reset flow (`/verify_username`, `/security_question`, `/reset_password`).** This three-step flow represents a secondary authentication pathway. Its attack surface is wider than it may appear: each step maintains state in the server-side session, meaning that an attacker who can manipulate session variables can potentially bypass steps. The security question endpoint also accepts user-supplied text checked against a stored hash, introducing a brute-force risk analogous to password guessing.

**Feedback form (`/feedback-page`, `/feedback`).** Although protected by `@login_required`, this endpoint still constitutes an attack surface for authenticated attackers. Risks include stored cross-site scripting (XSS) via unsanitized message content, resource exhaustion through repeated submissions, and CSRF if session cookies are interceptable.

**Session cookies.** Flask's session mechanism uses a signed, client-side cookie. The security of the entire authenticated session depends on the secrecy and entropy of `SECRET_KEY`. A weak or hardcoded key allows an attacker to forge arbitrary session cookies, effectively bypassing all authentication.

**Database (SQLite via SQLAlchemy).** The database holds password hashes, security answer hashes, and feedback content. The primary attack vector is SQL injection through ORM misuse; secondary risks include insecure storage if hashing is absent or weak.

**Configuration and environment.** Hardcoded secrets, `debug=True` in production, and committed `.env` files all expand the attack surface by leaking sensitive configuration data.

### 2.2 Attack Trees

**Attack Tree 1: Password Guessing (Threat 2)**

```
Goal: Gain unauthorized access to a user account via login
|
+-- A. Automated brute force (sequential password attempts)
|       |
|       +-- A.1 No lockout mechanism → unlimited attempts [MITIGATED]
|       +-- A.2 Lockout resets too quickly → effective brute force still possible [MITIGATED: progressive]
|       +-- A.3 Lockout applies per-IP, not per-account → attacker uses multiple IPs [PARTIAL: local scope]
|
+-- B. Credential stuffing (breach database reuse)
|       |
|       +-- B.1 User reuses password from breached site
|       +-- B.2 Application accepts credentials without secondary verification [MITIGATED: lockout applies]
|
+-- C. Password spray (common passwords across many accounts)
        |
        +-- C.1 Weak password policy allows common passwords [MITIGATED: strong policy enforced]
        +-- C.2 Lockout per account stops spraying after 5 attempts per account [MITIGATED]
```

**Attack Tree 2: Session Cookie Forgery (Threat 9)**

```
Goal: Forge a valid Flask session cookie to authenticate as any user
|
+-- A. Obtain or derive the SECRET_KEY
|       |
|       +-- A.1 SECRET_KEY is hardcoded in source code → extract from repository [MITIGATED: .gitignore, .env]
|       +-- A.2 SECRET_KEY is weak/guessable → brute force HMAC verification [MITIGATED: 43-char random key]
|       +-- A.3 SECRET_KEY leaked via debug output → debug mode in production [MITIGATED: env-gated debug]
|
+-- B. Steal a legitimate session cookie
        |
        +-- B.1 Cookie lacks HttpOnly → XSS exfiltration possible [MITIGATED: HttpOnly=True]
        +-- B.2 Cookie transmitted over HTTP → network interception [PARTIAL: Secure flag out of scope]
        +-- B.3 Session not invalidated on logout → cookie replay possible [MITIGATED: logout_user()]
```

---

## 3. Explanation of Attack Scenarios

### 3.1 Brute Force Login Attack

An attacker targeting a known username submits automated POST requests to `/login` with a dictionary of common passwords. In the original, pre-hardening version of the application, no rate limiting existed: an attacker could submit thousands of attempts per minute. After hardening, the login route tracks `failed_logins` on the User model. After five consecutive failures, `lockout_count` is incremented and `locked_until` is set to `datetime.utcnow() + get_lockout_duration(...)`. The `get_lockout_duration` function implements a progressive schedule: the first lockout lasts five minutes, the second fifteen minutes (5 × 3), the third sixty minutes (15 × 4), and the fourth three hundred minutes (60 × 5). This exponential escalation makes automated brute force economically infeasible: an attacker who reaches the fourth lockout tier must wait five hours before their next batch of five attempts. Crucially, successful login resets `failed_logins` to zero, and an expired lockout is also cleared on the next login attempt.

### 3.2 SQL Injection

A classic SQL injection attack against a login form involves submitting a payload such as `' OR '1'='1` in the username or password field, with the goal of manipulating the underlying SQL query to bypass authentication or exfiltrate data. This attack is entirely neutralized by the use of the SQLAlchemy ORM throughout the application. All database queries use ORM methods such as `User.query.filter_by(username=username).first()`, which internally generates parameterized queries and never interpolates user input directly into SQL strings. There is no raw SQL anywhere in the codebase. Even if the ORM were somehow bypassed, all fields are length-checked server-side (usernames capped at 30 characters, messages at 2,000 characters), limiting the attack surface further.

### 3.3 Session Fixation

In a session fixation attack, the adversary plants a known session ID in the victim's browser (e.g., via a crafted URL or a pre-authentication cookie), then waits for the victim to log in. If the application does not regenerate the session upon authentication, the attacker's pre-planted session ID becomes a valid authenticated session token that the attacker already possesses. The application mitigates this by calling `session.clear()` immediately before `login_user(user, remember=remember)` in the login route. This ensures that whatever session state existed before authentication — including any attacker-planted values — is discarded, and Flask-Login establishes a fresh session bound to the newly authenticated user.

### 3.4 Credential Stuffing

Credential stuffing exploits the widespread practice of password reuse across services. The attacker obtains a large database of username/password pairs from a prior breach and systematically tests them against the target application. The primary defense is the strong password policy: passwords must be at least eight characters, contain at least one uppercase letter, one digit, and one symbol, and must not contain the user's first name, last name, or username. This policy, enforced both in `password_ok()` in `auth.py` and re-validated during password reset in `reset_password()`, reduces the likelihood that a user's application password matches a previously breached credential. The per-account progressive lockout further limits the rate at which credential stuffing attempts can be made; after five failures per account, the account is locked for an escalating duration, slowing automated stuffing campaigns significantly.

### 3.5 Cross-Site Request Forgery (CSRF) on the Feedback Form

A CSRF attack against the feedback endpoint would involve crafting a malicious web page that, when visited by an authenticated user, silently submits a POST request to `/feedback` using the victim's existing browser cookies. The primary mitigation is `SESSION_COOKIE_SAMESITE = "Lax"` in `config.py`. The `Lax` policy instructs the browser not to send the session cookie on cross-site POST requests initiated by third-party pages, which covers the most common CSRF attack vector. Full CSRF token validation was identified as out of scope for a locally hosted development application; however, the `SameSite=Lax` cookie attribute provides meaningful protection against the majority of CSRF attack patterns without requiring form-level token injection.

---

## 4. Standards and Guidelines Consulted

### 4.1 OWASP Top 10

The OWASP Top 10 (2021 edition) served as the primary reference for identifying and categorizing web application risks. The following OWASP categories are directly addressed in this project:

- **A01 — Broken Access Control**: Addressed via `@login_required` decorators on the dashboard, feedback page, and feedback submission routes, and via the `reset_step` state machine preventing unauthorized access to the password reset completion page.
- **A02 — Cryptographic Failures**: Addressed via bcrypt hashing of passwords and security answers with work factor 12 (CWE-916, CWE-522), and a 43-character cryptographically random `SECRET_KEY`.
- **A03 — Injection**: Addressed via SQLAlchemy ORM parameterized queries (CWE-89) and HTML escaping in `sanitizers.py`.
- **A05 — Security Misconfiguration**: Addressed via environment-variable-gated debug mode, `.gitignore` excluding `.env` and the database instance directory, and removal of the hardcoded `SECRET_KEY` fallback.
- **A07 — Identification and Authentication Failures**: Addressed via progressive lockout, generic error messages, session regeneration on login, and bcrypt credential storage.

### 4.2 CWE / SANS Top 25

The Common Weakness Enumeration was used as the primary taxonomy for threat classification. Each of the thirteen threats identified by the security analyst was mapped to one or more CWE entries. The full resolution table is provided in the Appendix. Key CWEs addressed include CWE-89 (SQL Injection), CWE-307 (Excessive Authentication Attempts), CWE-384 (Session Fixation), CWE-522 (Insufficiently Protected Credentials), and CWE-203 (Observable Discrepancy).

### 4.3 NIST Special Publication 800-63B

NIST SP 800-63B (Digital Identity Guidelines — Authentication and Lifecycle Management) informed the password policy design. The guideline recommends a minimum password length of eight characters, checking submitted passwords against known-breached credential lists, and avoiding complexity rules that encourage predictable patterns (e.g., substituting `@` for `a`). The implemented policy requires length, character diversity, and absence of personally identifiable substrings (name and username), which aligns with SP 800-63B's recommendations while remaining usable.

### 4.4 Microsoft Security Development Lifecycle (SDL)

The Microsoft SDL informed the overall development process, particularly the practices of threat modeling before coding, security requirements as acceptance criteria, and post-implementation security testing. The SDL's concept of a "final security review" is approximated by the attacker-testing phase described in Section 9.

---

## 5. Technical Controls

### 5.1 Bcrypt Password Hashing

All passwords are hashed using Flask-Bcrypt with a work factor of 12. The `set_password()` method on the `User` model calls `bcrypt.generate_password_hash(password).decode("utf-8")` and stores the result in `password_hash`. Verification uses `bcrypt.check_password_hash(self.password_hash, password)`. Work factor 12 means bcrypt performs 2^12 = 4,096 iterations per hash operation, making offline dictionary attacks computationally expensive. The same bcrypt configuration is applied to security answers via `set_security_answers()` and `check_security_answer()`, which normalize input to lowercase and strip whitespace before hashing to ensure consistency.

### 5.2 Parameterized Queries via SQLAlchemy ORM

All database interactions use the SQLAlchemy ORM. Queries such as `User.query.filter_by(username=username).first()` generate parameterized SQL internally, binding user-supplied values as parameters rather than interpolating them into query strings. This categorically eliminates first-order SQL injection. No raw `db.engine.execute()` or `text()` calls exist anywhere in the application.

### 5.3 Session Management

Session security is implemented at multiple layers. The `SECRET_KEY` is loaded exclusively from the environment via `os.getenv("SECRET_KEY")`; if not set, `config.py` raises a `ValueError`, preventing the application from starting with an insecure configuration. The cookie is hardened via `SESSION_COOKIE_HTTPONLY = True` (blocks JavaScript access), `SESSION_COOKIE_SAMESITE = "Lax"` (blocks cross-site POST), and `SESSION_COOKIE_SECURE = False` (appropriate for local HTTP; must be `True` in HTTPS deployment). Session regeneration on login is achieved via `session.clear()` before `login_user()`.

### 5.4 Input Validation and Length Limiting

Server-side validation is enforced in `validators.py` (for feedback fields) and inline in `auth.py` (for authentication fields). Limits include: username 3–30 characters, first and last names up to 50 characters, email up to 255 characters, and feedback messages up to 2,000 characters. HTML `maxlength` attributes on all form fields provide a first-line client-side barrier. `Sanitizer.sanitize_text()` in `sanitizers.py` applies `html.escape()` to email and message content before database storage, preventing stored XSS.

### 5.5 Progressive Account Lockout

The `get_lockout_duration()` function in `auth.py` computes escalating lockout periods based on `lockout_count` and `last_lockout_minutes` stored in the database. This state persists across sessions and server restarts, making it resistant to restart-based circumvention. The lockout check at the top of the login POST handler returns early with a user-visible remaining-time message if `locked_until > datetime.utcnow()`, preventing any further authentication attempts.

---

## 6. Security Mechanisms Implemented

### 6.1 Generic Error Messages (Anti-Enumeration, CWE-203)

Both the login route and the `/verify_username` route return generic messages that do not distinguish between "username not found" and "password incorrect." The login route displays "Invalid credentials" regardless of which check failed. The verify-username route always returns "If that username exists, you will be prompted to answer a security question," even when the username lookup returns `None` and the flow simply redirects back to the same page. This prevents an attacker from using the password reset flow as a username oracle.

### 6.2 Progressive Lockout (CWE-307)

The lockout mechanism tracks state in three database columns: `failed_logins` (resets to zero on success or lockout trigger), `lockout_count` (increments each time a lockout is imposed), and `last_lockout_minutes` (stores the duration of the most recent lockout, used as the base for the next escalation). The escalation schedule produces lockouts of 5 minutes, 15 minutes, 60 minutes, and 300 minutes for the first four lockout events, with further escalation beyond that following the formula `last_minutes × (lockout_count + 2)`.

### 6.3 Bcrypt for Passwords and Security Answers (CWE-522, CWE-916)

Security answers were initially stored in plaintext; the migration to bcrypt hashing represented a significant security improvement. The `set_security_answers()` method normalizes answers (lowercase, stripped) before hashing, and `check_security_answer()` applies the same normalization before verification. This ensures that minor case variations in user input do not cause false negatives while still protecting the stored values against database compromise.

### 6.4 Reset Step State Machine (CWE-640, CWE-288)

The password reset flow uses a `reset_step` session variable as a state machine with three valid states: `"security_question"` and `"reset_password"`. Each route in the reset flow checks that the current `reset_step` matches the expected value and that `reset_user` and `reset_token` session keys are present before proceeding. Accessing `/reset_password` directly without first completing the `/security_question` step results in a redirect to `/login` with an "Unauthorized password reset attempt" flash message. This prevents step-skipping attacks. The `reset_token` (a 16-byte hex value generated via `secrets.token_hex(16)`) provides additional binding of the reset session to a specific initiation event.

### 6.5 Security Question Attempt Limit (CWE-640)

The security question route enforces a maximum of three attempts. The attempt counter is stored in `session["attempts"]` and incremented on each POST. If the counter exceeds three, the session is cleared entirely via `session.clear()` and the user is redirected to login, forcing them to restart the reset flow from the beginning. The random selection of one of three possible questions (first pet, elementary school, birth city) means that an attacker who has obtained the username cannot simply focus on the most guessable answer without also knowing which question was selected.

### 6.6 Strong Password Policy with Name/Username Exclusion (CWE-521)

The `password_ok()` function enforces length (minimum 8 characters), uppercase presence, digit presence, and symbol presence using targeted regular expressions. Following this check, the registration and password reset routes additionally verify that the password does not contain the user's first name, last name, or username as a substring (case-insensitive). This directly addresses the credential stuffing risk: users cannot trivially construct passwords that embed their own identity, which is one of the most common patterns in breached credential databases.

### 6.7 Session Fixation Prevention (CWE-384)

The call to `session.clear()` immediately before `login_user(user, remember=remember)` in the login route ensures that the session is regenerated on every successful authentication event. Any pre-authentication session state — including any session ID that an attacker may have planted — is discarded. Flask-Login then establishes a new session under a fresh session ID.

### 6.8 Per-User Daily Feedback Rate Limiting (CWE-400, CWE-770)

The `Feedback` submission route checks `current_user.feedback_count` against a maximum of five submissions per day. The `feedback_date` column stores the date of the last submission; if it differs from today's date, `feedback_count` is reset to zero before the limit check. This prevents authenticated users from flooding the feedback database. The 2,000-character message cap limits the size of each individual submission, bounding storage growth from any single record. Both routes (`/feedback-page` GET and `/feedback` POST) are decorated with `@login_required`, ensuring unauthenticated users cannot reach the feedback surface at all.

### 6.9 Secret Key Hardening (CWE-321, CWE-565)

The original `SECRET_KEY` was a twelve-digit integer literal hardcoded directly in the configuration. It was replaced with a 43-character key generated via `secrets.token_urlsafe(32)` and stored exclusively in the `.env` file. The `.gitignore` file excludes `.env`, `instance/` (the SQLite database directory), and `__pycache__/`, ensuring that neither the key nor the database is tracked in version control.

### 6.10 Debug Mode Hardening (CWE-16)

The `app.run()` call in `app.py` uses `debug=os.getenv("FLASK_ENV") == "development"` rather than `debug=True`. The interactive Werkzeug debugger — which exposes a REPL to anyone who can trigger an error — is therefore disabled in any environment where `FLASK_ENV` is not explicitly set to `"development"`. The `.env` file on the developer's machine sets `FLASK_ENV=development`; this file is gitignored and never deployed.

---

## 7. Mitigation of Identified Attacks

The following discussion addresses each of the thirteen threats identified by the security analyst, grouped by risk domain.

### 7.1 Identity and Enumeration (Threats 1, 2, 5)

**Threat 1 (Username Enumeration, CWE-203)** was mitigated by standardizing error responses across both the login and reset flows. Previously, distinct messages for "user not found" versus "wrong password" allowed an attacker to confirm valid usernames. After hardening, both conditions return "Invalid credentials" on the login page, and the verify-username page always displays the same informational message regardless of whether the submitted username exists in the database.

**Threat 2 (Password Guessing, CWE-307)** was fully mitigated through the progressive lockout system described in Sections 5.5 and 6.2. The lockout state is persisted in the database, making it robust against client-side manipulation and server restarts. The escalating durations ensure that sustained brute-force campaigns become impractical.

**Threat 5 (Credential Stuffing, CWE-307)** was partially mitigated. The strong password policy reduces the probability that a user's credential appears in a breach database, and the per-account lockout throttles the attack rate. Full IP-level rate limiting was not implemented because, in a local development environment, all requests originate from the same loopback address; applying IP-based blocking would lock the developer out of their own application. This limitation is explicitly acknowledged as out of scope.

### 7.2 Credential Storage (Threats 3, 9)

**Threat 3 (Stored Credentials, CWE-522)** was fully mitigated. All passwords are bcrypt-hashed with work factor 12 at registration and password reset. Security answers, which were initially stored in plaintext, were migrated to bcrypt hashing via `set_security_answers()`. A database compromise reveals only bcrypt digests, which are computationally expensive to crack.

**Threat 9 (Session Cookie Forgery, CWE-565, CWE-321)** was fully mitigated. The previously hardcoded numeric key was replaced with a cryptographically random 43-character key generated by `secrets.token_urlsafe(32)`. Flask uses this key to sign session cookies with HMAC-SHA1; without the key, a forged cookie cannot produce a valid signature. Removing the hardcoded fallback and raising `ValueError` on startup if the key is absent ensures the application cannot run in an insecure configuration.

### 7.3 Injection and Input Handling (Threats 6, 7)

**Threat 6 (SQL Injection, CWE-89)** was fully mitigated by the exclusive use of SQLAlchemy ORM queries throughout the application. No raw SQL is present. ORM-generated queries bind all user input as parameters, not as string fragments of the query.

**Threat 7 (Oversized Input, CWE-20)** was fully mitigated by a two-layer defense: HTML `maxlength` attributes on all form fields provide immediate client-side feedback, and server-side length checks in `auth.py` and `validators.py` enforce the same limits independently. This defense-in-depth approach ensures that an attacker bypassing the browser UI (e.g., with a raw HTTP client) still cannot submit oversized input.

### 7.4 Session and Access Control (Threats 10, 11)

**Threat 10 (Session Hijacking, CWE-384)** was substantially mitigated. `HttpOnly=True` prevents JavaScript from reading the session cookie, blocking XSS-based cookie exfiltration. Session regeneration on login (via `session.clear()`) prevents session fixation. The `Secure` flag (which would restrict cookie transmission to HTTPS) and server-side session invalidation on logout were identified as appropriate only for a deployed, TLS-protected environment; they are deferred as out of scope for local development.

**Threat 11 (Insecure Configuration, CWE-16)** was fully mitigated as described in Section 6.10. Debug mode is controlled by an environment variable, the `.env` file is gitignored, and the application raises an error rather than falling back to an insecure default key.

### 7.5 Application Abuse (Threats 4, 8, 12, 13)

**Threat 4 (Password Recovery Abuse, CWE-640)** was addressed through the `reset_step` state machine and the three-attempt limit on security questions. The random question selection adds further unpredictability. The flow is considered partially mitigated because, in a production system, a time-limited single-use reset token sent to a verified email address would provide stronger guarantees; this was deferred as beyond the scope of the current project.

**Threats 8 and 13 (CSRF on Login and Feedback, CWE-352)** were addressed via `SESSION_COOKIE_SAMESITE = "Lax"`. This attribute prevents the browser from attaching the session cookie to cross-origin POST requests initiated by third-party pages, which is the standard CSRF attack vector. Explicit CSRF token generation and validation (as provided by Flask-WTF or similar) were deferred as out of scope for a local development environment not exposed to the public internet.

**Threat 12 (Spam Feedback, CWE-400)** was fully mitigated. The `@login_required` decorator on both feedback routes prevents unauthenticated submissions entirely. The per-user daily submission limit (five per day, enforced via `feedback_count` and `feedback_date`) prevents authenticated users from flooding the system. The 2,000-character cap limits per-record storage. HTML sanitization via `html.escape()` in `Sanitizer.sanitize_text()` prevents stored XSS in the feedback content.

---

## 8. Testing

### 8.1 Phase 1 — User Testing

The first testing phase simulated normal user behavior to verify that all application features functioned correctly and that security controls did not produce false positives or degrade the user experience.

**Registration.** Valid registration with all required fields was tested, as was registration with mismatched passwords, weak passwords, passwords containing the username or name, usernames below the minimum length, and duplicate usernames. All error paths produced the expected flash messages and redirects.

**Login and lockout.** Successful login, login with incorrect password, and login after account lockout were all verified. The progressive lockout durations were confirmed: after five failures, the remaining-time message was checked against the expected lockout duration. Successful login after lockout expiry was also verified, confirming that `failed_logins` and `locked_until` were properly reset.

**Password reset flow.** The full three-step flow (verify username, answer security question, set new password) was tested end-to-end. Additionally, direct URL navigation to `/security_question` and `/reset_password` without completing prior steps was tested, confirming that the `reset_step` guard correctly redirected unauthorized access to `/login`. The three-attempt limit on the security question was verified by entering three incorrect answers and confirming session clearance.

**Feedback form.** Feedback submission by an authenticated user, submission by an unauthenticated user (expected: redirect to login), and the daily submission limit (verified by submitting five feedback items and confirming the sixth was rejected) were all tested. Oversized message input (beyond 2,000 characters via a raw POST) was tested and confirmed to be rejected.

**Session and access control.** URL copy-paste testing was performed: after logout, previously authenticated URLs (`/dashboard`, `/feedback-page`) were accessed directly, confirming the `@login_required` redirect. The Remember Me checkbox was verified to persist the session cookie across browser restarts.

### 8.2 Phase 2 — Attacker Testing

The second testing phase systematically tested all thirteen analyst-identified threats against the hardened codebase.

**Enumeration testing.** Login and verify-username responses were compared for existing versus non-existing usernames. Both returned identical messages, confirming no observable discrepancy.

**Brute force simulation.** Repeated failed login attempts were submitted programmatically. The lockout trigger at five attempts was confirmed, and the lockout duration matched the expected progressive schedule.

**Injection testing.** SQL injection payloads (`' OR '1'='1`, `1; DROP TABLE users;--`) were submitted in the username and password fields. All were handled without error by the ORM's parameterized queries.

**Oversized input testing.** Fields were submitted with inputs exceeding their defined limits via curl to bypass HTML `maxlength` restrictions. All were rejected by server-side validation.

**Session cookie manipulation.** An attempt to forge a Flask session cookie without knowledge of the `SECRET_KEY` was confirmed to fail (Flask returns a 400 or ignores the cookie).

**Reset flow bypass.** Direct navigation to `/reset_password` without valid `reset_step`, `reset_user`, and `reset_token` session keys was confirmed to redirect to login.

**CSRF simulation.** A cross-origin POST to `/feedback` was simulated using a form hosted on a different origin. With `SameSite=Lax`, the session cookie was not sent and the request was rejected by `@login_required`.

**Results summary.** Seven threats were fully mitigated (Threats 1, 2, 3, 6, 7, 9, 11, 12). Four were partially mitigated by deliberate design decisions tied to the local development scope (Threats 5, 8, 10, 13). Two controls were confirmed as explicitly deferred out of scope (session expiration / CWE-613, HTTPS Secure flag / CWE-614).

---

## 9. Discussion

The project successfully demonstrated that security can be integrated into every phase of development rather than applied retroactively. The Agile-SDL hybrid approach proved effective: because each feature was accompanied by a pre-implementation threat model, no feature shipped without a corresponding security control, and the testing phase confirmed that all controls behaved as designed.

**What worked well.** The `reset_step` state machine was a particularly successful design choice. By making the reset flow stateful at the server side and requiring sequential traversal, it eliminated an entire class of authorization-bypass vulnerabilities without requiring complex logic. Bcrypt for both passwords and security answers, combined with normalization before hashing, ensured that the most critical stored credentials were properly protected. The progressive lockout mechanism, while straightforward in its implementation, provides substantially stronger protection than a simple fixed lockout duration.

**What is partially mitigated.** CSRF mitigation via `SameSite=Lax` is less robust than full CSRF token validation, particularly against same-site attacks and browsers that do not enforce the `Lax` policy consistently. Similarly, IP-level rate limiting for credential stuffing was not implemented due to the local development constraint. In a production deployment, these would be addressed by integrating Flask-WTF for CSRF tokens and deploying behind a reverse proxy or WAF that enforces IP-level rate limiting.

**What is out of scope.** The `Secure` cookie flag (requiring HTTPS), server-side session expiration (CWE-613), and email-based password reset tokens are all standard production security controls that were deliberately deferred. A local HTTP development environment cannot meaningfully enforce the `Secure` flag, and email infrastructure was outside the project's scope. These gaps are documented and would be addressed before any public deployment.

---

## 10. Learning Outcomes

This project provided concrete, hands-on experience with applying security engineering principles to a real application, rather than studying them in the abstract.

**Threat modeling as a design activity.** The most significant learning was the value of conducting threat modeling before writing code. Identifying username enumeration as a risk before implementing the login route meant that the generic error message was part of the original design, not a patch applied after a vulnerability was discovered. This experience reinforces the Agile-SDL principle that security requirements belong in the initial user story, not in a post-release bug fix.

**Depth of authentication complexity.** What initially appeared to be a simple login form revealed substantial complexity on close examination: lockout state management, session regeneration, enumeration prevention, progressive escalation, and credential hashing all interact. Understanding how each control addresses a specific threat — and how a gap in one can undermine another — provided a nuanced understanding of authentication security that no textbook treatment fully conveys.

**The cost of security debt.** The migration of security answer storage from plaintext to bcrypt illustrated the concept of security debt: a design decision made early (plaintext storage) required a non-trivial migration later. Beginning with bcrypt from the first iteration would have been less costly. This lesson — that security controls are cheaper to implement upfront than to retrofit — is a practical confirmation of the SDL's core argument.

**Scope management in security engineering.** Not every control is appropriate for every deployment context. Learning to distinguish between "not implemented" and "deliberately deferred as out of scope with a documented rationale" is an important professional skill. The explicit treatment of IP-rate limiting, the `Secure` cookie flag, and CSRF tokens as out-of-scope (rather than simply missing) reflects the kind of reasoned security decision-making expected in professional practice.

**Testing from an attacker's perspective.** The attacker-testing phase required a different mental model than functional user testing. Rather than asking "does this feature work?", the question becomes "how would an adversary attempt to subvert this feature?" This adversarial thinking — enumerating inputs, bypassing the UI, exploiting state transitions — is a skill that developed significantly over the course of this project.

---

## Appendix A — CWE Resolution Table

| CWE ID | Name | Status |
|--------|------|--------|
| CWE-16 | Configuration | Resolved |
| CWE-89 | SQL Injection | Resolved |
| CWE-203 | Observable Discrepancy (Username Enumeration) | Resolved |
| CWE-256 | Plaintext Storage of Password | Resolved |
| CWE-287 | Improper Authentication | Resolved |
| CWE-288 | Auth Bypass via Alternate Path | Resolved |
| CWE-306 | Missing Auth for Critical Function | Resolved |
| CWE-307 | Excessive Authentication Attempts | Resolved |
| CWE-321 | Hard-coded Cryptographic Key | Resolved |
| CWE-352 | Cross-Site Request Forgery | Partial (SameSite=Lax; tokens out of scope) |
| CWE-384 | Session Fixation | Resolved |
| CWE-400 | Uncontrolled Resource Consumption | Resolved |
| CWE-521 | Weak Password Requirements | Resolved |
| CWE-522 | Insufficiently Protected Credentials | Resolved |
| CWE-565 | Cookie Without Validation | Resolved |
| CWE-613 | Insufficient Session Expiration | Out of scope |
| CWE-614 | Sensitive Cookie Without Secure Flag | Out of scope (local dev / no HTTPS) |
| CWE-640 | Weak Password Recovery Mechanism | Partial (state machine + attempt limit) |
| CWE-770 | Resource Allocation Without Throttling | Resolved |
| CWE-916 | Insufficient Hash Work Factor | Resolved |
| CWE-1004 | Cookie Without HttpOnly | Resolved |

---

## Appendix B — Threat Summary Table

| # | Threat | CWE(s) | Mitigation | Status |
|---|--------|--------|------------|--------|
| 1 | Username Enumeration | CWE-203 | Generic messages in login and reset flow | Resolved |
| 2 | Password Guessing / Brute Force | CWE-307 | Progressive lockout (5/15/60/300 min) | Resolved |
| 3 | Stored Credentials in Plaintext | CWE-522, CWE-916 | bcrypt (work factor 12) for passwords + security answers | Resolved |
| 4 | Password Recovery Abuse | CWE-640, CWE-288 | reset_step state machine; 3-attempt security question limit | Partial |
| 5 | Credential Stuffing | CWE-307 | Strong password policy; per-account lockout | Partial (IP limiting out of scope) |
| 6 | SQL Injection | CWE-89 | SQLAlchemy ORM parameterized queries | Resolved |
| 7 | Oversized Input | CWE-20 | HTML maxlength + server-side length checks | Resolved |
| 8 | CSRF (Login/General) | CWE-352 | SESSION_COOKIE_SAMESITE=Lax | Partial (tokens out of scope) |
| 9 | Session Cookie Forgery | CWE-565, CWE-321 | 43-char random SECRET_KEY; no hardcoded fallback | Resolved |
| 10 | Session Hijacking | CWE-384 | HttpOnly=True; session.clear() on login | Partial (Secure flag out of scope) |
| 11 | Insecure Configuration | CWE-16 | FLASK_ENV-gated debug; .env gitignored | Resolved |
| 12 | Feedback Spam | CWE-400, CWE-770 | @login_required; 5/day limit; 2000-char cap; HTML escape | Resolved |
| 13 | CSRF (Feedback) | CWE-352 | SESSION_COOKIE_SAMESITE=Lax | Partial (tokens out of scope) |

---

*End of Report*
