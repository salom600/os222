# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x   | ✅ |
| 0.x     | ❌ |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security issues.

Email **salomos@salom600.github.io** with:

- Description of the issue
- Reproduction steps
- Impact assessment

You can expect:

- Acknowledgement within **48 hours**
- Status update within **7 days**
- Patch within **30 days** for critical issues

## Security features

SalomOS ships with these security defaults:

- ✅ Secure Boot signed
- ✅ AppArmor profiles enabled
- ✅ firewalld active
- ✅ SSH server disabled by default
- ✅ No root password in live mode
- ✅ Hardened kernel sysctl
- ✅ Automatic security updates via `unattended-upgrades`
- ✅ Reproducible ISO builds (in progress)
- ✅ Signed packages from Debian repos

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#7-security-model) for details.
