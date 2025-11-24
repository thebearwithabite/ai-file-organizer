# Security Policy

## 🛡️ Security Priorities

The AI File Organizer handles potentially sensitive user data. Security is a top priority, particularly around:

1. **PII Protection** - No personally identifiable information in code or commits
2. **Credential Safety** - No API keys, tokens, or passwords in repository
3. **Data Privacy** - Local processing by default, secure cloud integration
4. **Rollback Safety** - Complete undo capability for all file operations

## 🔒 Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.x     | ✅ Yes            |
| 2.x     | ❌ No             |
| 1.x     | ❌ No             |

## 🚨 Reporting a Vulnerability

### For Critical Security Issues

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead:

1. **Email the maintainer directly** at the contact information in the repository
2. **Provide details:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

### For Non-Critical Security Improvements

You can create a public issue using the "Security Issue" template if:
- It's a general security improvement suggestion
- No active exploitation is possible
- It doesn't expose existing vulnerabilities

## ⚠️ Common Security Concerns

### PII (Personally Identifiable Information)

**What qualifies as PII:**
- Real names (use "Client Name", "User" instead)
- Email addresses (use user@example.com)
- Phone numbers
- Physical addresses
- Social Security Numbers
- API keys or credentials
- Actual client or project names

**Protection measures:**
- Use `scrub_personal_info.py` before all commits
- Review all changes with `git diff`
- Never commit actual user data or screenshots with PII
- Use placeholder names in code and documentation

### Credentials and API Keys

**Proper storage:**
- Environment variables (`.env` files in `.gitignore`)
- System keychain (macOS)
- Configuration files in `.gitignore`
- Never in code or commits

**Example - WRONG:**
```python
api_key = "sk-1234567890abcdef"  # ❌ NEVER DO THIS
```

**Example - CORRECT:**
```python
api_key = os.getenv('GEMINI_API_KEY')  # ✅ Use environment variables
```

### File Operation Safety

**Rollback System:**
- All file operations logged in `easy_rollback_system.py`
- Users can undo any operation with `--undo` command
- Complete operation history maintained
- No permanent data loss from AI decisions

### Database Security

**ChromaDB/SQLite:**
- Database files in `.gitignore`
- No sensitive data in version control
- Local storage by default
- Encryption for cloud backups (if implemented)

## 🔍 Security Scanning

### Automated Scans

We use:
- **CodeQL** - Static code analysis for security vulnerabilities
- **Dependabot** - Automatic dependency vulnerability alerts
- **Dependency Review** - PR-based dependency security checks

### Manual Reviews

Before each release:
- Manual code review for security issues
- PII scrubbing verification
- Credential exposure check
- Third-party dependency audit

## 📋 Security Checklist for Contributors

Before submitting a PR:

- [ ] No PII in code, comments, or commits
- [ ] No hardcoded credentials or API keys
- [ ] `scrub_personal_info.py` run and verified
- [ ] No actual user data in test files
- [ ] Environment variables used for secrets
- [ ] `.gitignore` updated for new config files
- [ ] Database files excluded from commits
- [ ] Screenshots reviewed for sensitive data

## 🔐 Dependency Security

### Python Dependencies

- Keep dependencies up to date via Dependabot
- Review security advisories regularly
- Pin versions in `requirements*.txt`
- Audit new dependencies before adding

### Frontend Dependencies

- `npm audit` run regularly for frontend_v2
- Dependencies reviewed before updates
- Known vulnerabilities addressed promptly

## 🛠️ Security Tools

### Available Tools

**PII Scrubbing:**
```bash
python scrub_personal_info.py
```

**Credential Check:**
```bash
git log --all --full-history --source -- "*secret*" "*password*"
```

**Dependency Audit:**
```bash
pip-audit  # If installed
npm audit  # For frontend
```

## 📊 Security Incident Response

### If a Vulnerability is Discovered

1. **Assess Severity:**
   - Critical: Immediate action required
   - High: Fix within 24-48 hours
   - Medium: Fix in next release
   - Low: Address when convenient

2. **Containment:**
   - Identify affected versions
   - Determine if exploitation has occurred
   - Create patch immediately

3. **Notification:**
   - Notify affected users (if any)
   - Create security advisory
   - Update documentation

4. **Resolution:**
   - Deploy fix
   - Verify fix effectiveness
   - Update security policy if needed

5. **Post-Mortem:**
   - Document what happened
   - Improve processes to prevent recurrence
   - Update security checks

## 🎓 Security Best Practices

### For Users

- Keep your installation up to date
- Use environment variables for API keys
- Regularly backup your database
- Review rollback logs periodically
- Report suspicious behavior

### For Developers

- Review code for security implications
- Test with non-sensitive data only
- Use secure coding practices
- Keep dependencies updated
- Document security decisions

## 📝 Security Updates

Security fixes will be:
- Released as patch versions (e.g., 3.1.1)
- Announced in release notes
- Tagged with `[SECURITY]` in commits
- Documented in this file

## 📞 Contact

For security concerns:
- **Email:** [Use repository maintainer contact]
- **GitHub:** @thebearwithabite (for non-critical issues)
- **Response Time:** Within 48 hours for critical issues

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)

---

**Last Updated:** November 2024
**Version:** 3.1
