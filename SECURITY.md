# Security Policy

## Branch Protection Rules

This repository enforces the following security policies to protect the main branch:

### Main Branch Protection

The `main` branch is protected with the following rules:

1. **No Direct Pushes**: Direct pushes to the `main` branch are **not allowed**
2. **Pull Request Required**: All changes must go through a pull request
3. **Required Reviews**: Pull requests require approval from code owners before merging
4. **Required Status Checks**: All CI/CD checks must pass before merging
5. **Up-to-date Branch**: Branches must include the latest commits from the base branch before merging

### Code Owners

Code owners are defined in the `.github/CODEOWNERS` file. These individuals or teams are:
- Automatically requested for review on pull requests
- Required to approve changes before they can be merged
- Responsible for maintaining code quality and security

### For Repository Administrators

To configure these protections in GitHub:

1. Go to **Settings** → **Branches**
2. Add a branch protection rule for `main`
3. Enable the following settings:
   - ✅ Require a pull request before merging
     - ✅ Require approvals (minimum: 1)
     - ✅ Dismiss stale pull request approvals when new commits are pushed
     - ✅ Require review from Code Owners
   - ✅ Require status checks to pass before merging
     - ✅ Require branches to be up to date before merging
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings (even for administrators)
   - ✅ Restrict who can push to matching branches (only allow specific users/teams)

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by:

1. **Do NOT** open a public issue
2. Contact the repository maintainers directly
3. Provide detailed information about the vulnerability
4. Allow reasonable time for the issue to be addressed before public disclosure

## Security Best Practices

Contributors should follow these security best practices:

- Never commit sensitive data (passwords, API keys, tokens)
- Keep dependencies up to date
- Follow secure coding guidelines
- Review code changes carefully before approval
- Enable two-factor authentication on GitHub accounts
