# Branch Protection Configuration Guide

This document provides step-by-step instructions for repository administrators to configure branch protection rules for the PHISHES repository.

## Prerequisites

- Repository administrator access
- Access to repository Settings

## Configuration Steps

### 1. Navigate to Branch Protection Settings

1. Go to the repository on GitHub: https://github.com/DHI/PHISHES
2. Click on **Settings** (top menu)
3. In the left sidebar, click **Branches**
4. Under "Branch protection rules", click **Add rule** (or edit existing rule for `main`)

### 2. Configure Branch Name Pattern

- In the "Branch name pattern" field, enter: `main`

### 3. Enable Required Settings

Check the following boxes and configure as described:

#### Require a pull request before merging
- ☑️ **Require a pull request before merging**
  - ☑️ **Require approvals**: Set minimum to `1` (or higher as needed)
  - ☑️ **Dismiss stale pull request approvals when new commits are pushed**
  - ☑️ **Require review from Code Owners** (this enforces the CODEOWNERS file)
  - ☑️ **Require approval of the most recent reviewable push**

#### Require status checks to pass before merging
- ☑️ **Require status checks to pass before merging**
  - ☑️ **Require branches to be up to date before merging**
  - Search and add the following status checks:
    - `PR Validation`
    - `Code Quality Checks`
    - `Security Scanning`

#### Additional protections
- ☑️ **Require conversation resolution before merging**
- ☑️ **Require signed commits** (optional but recommended)
- ☑️ **Require linear history** (optional, prevents merge commits)

#### Rules applied to administrators
- ☑️ **Do not allow bypassing the above settings**
  - This ensures that even administrators must follow the rules
  - Can be unchecked if you need admin override capability

#### Restrict pushes
- ☑️ **Restrict who can push to matching branches**
  - Leave empty or add specific teams/users who can merge (after PR approval)
  - Typically you can leave this empty to allow anyone with write access to merge approved PRs

### 4. Save Changes

Click **Create** or **Save changes** at the bottom of the page.

## Verification

After configuration, verify the protection is working:

1. Try to push directly to `main` (should fail):
   ```bash
   git push origin main
   # Should receive: "remote: error: GH006: Protected branch update failed"
   ```

2. Create a pull request:
   - Branch protection should require reviews from code owners
   - All status checks must pass
   - Conversations must be resolved

## Additional Security Recommendations

### 1. Enable Two-Factor Authentication
Require 2FA for all organization members:
- Go to Organization Settings → Authentication security
- Enable "Require two-factor authentication"

### 2. Configure CODEOWNERS
Edit `.github/CODEOWNERS` file to specify:
- Teams or individuals responsible for reviews
- Different owners for different paths if needed

### 3. Set Up Required Status Checks
Ensure the GitHub Actions workflow runs on all PRs:
- The `.github/workflows/branch-protection.yml` workflow will run automatically
- Add additional CI/CD workflows as needed

### 4. Enable Dependabot
Configure automated dependency updates:
- Go to Settings → Security & analysis
- Enable "Dependabot alerts"
- Enable "Dependabot security updates"

### 5. Enable Code Scanning
Set up automated code scanning:
- Go to Settings → Security & analysis
- Enable "Code scanning"
- Configure CodeQL or other scanning tools

## Troubleshooting

### "Status check has not run on this commit"
- Ensure the workflow file is in the default branch
- Check that workflow has proper permissions
- Verify workflow is triggered on `pull_request` events

### "Review required from code owners"
- Check that CODEOWNERS file is in `.github/CODEOWNERS`
- Verify team/user names are correct (e.g., `@DHI/phishes-maintainers`)
- Ensure code owners have been properly assigned in GitHub

### "Branch is not up to date"
- Pull latest changes from main: `git pull origin main`
- Rebase or merge main into your branch
- Push updated branch

## Contact

For questions or issues with branch protection configuration, contact:
- Repository administrators
- GitHub organization owners
