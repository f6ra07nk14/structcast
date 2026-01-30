# uv-default-project

An practical starter template for Python projects using [uv](https://github.com/astral-sh/uv), with optional Docker support and a CI/CD pipeline.

- [uv-default-project](#uv-default-project)
  - [Features](#features)
  - [Project Structure](#project-structure)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Usage](#usage)
    - [Running Tests](#running-tests)
    - [Adding Tests](#adding-tests)
    - [Code Quality Checks](#code-quality-checks)
  - [CI/CD Pipeline](#cicd-pipeline)
    - [Workflow Triggers](#workflow-triggers)
    - [Pipeline Stages](#pipeline-stages)
      - [1. Build Docker Image](#1-build-docker-image)
      - [2. Test](#2-test)
      - [3. Cleanup Images (Pull Requests Only)](#3-cleanup-images-pull-requests-only)
      - [4. Delete Branch (Pull Requests Only)](#4-delete-branch-pull-requests-only)
      - [5. Release Job (Main Branch Push Only)](#5-release-job-main-branch-push-only)
    - [Semantic Versioning Rules](#semantic-versioning-rules)
    - [Release Configuration](#release-configuration)
    - [Workflow Permissions](#workflow-permissions)
  - [Docker Image](#docker-image)
    - [Image Naming Convention](#image-naming-convention)
    - [Available Tags](#available-tags)
    - [Pulling Images](#pulling-images)
    - [Image Lifecycle](#image-lifecycle)
  - [Development](#development)
    - [Commit Message Convention](#commit-message-convention)
      - [Format](#format)
      - [Commit Types and Version Impact](#commit-types-and-version-impact)
      - [Examples](#examples)
      - [Multi-line Commits](#multi-line-commits)
  - [License](#license)

## Features

- **uv package manager**: fast, modern dependency and environment management
- **Docker support**: container builds that mirror CI behavior
- **CI/CD pipeline**: automated GitHub Actions workflow with:
  - Docker image change detection
  - Automatic Docker image building and publishing to GitHub Container Registry
  - Docker image verification
  - Automated testing with pytest in Docker containers

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── ci.yml           # CI/CD pipeline configuration
├── src/
│   └── uv_default_project/
│       ├── __init__.py      # Main module with example functions
│       └── __main__.py      # Entry point for the application
├── tests/
│   └── test_basic.py        # Example tests
├── Dockerfile               # Docker container configuration
├── pyproject.toml          # Project metadata and dependencies
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) - Install from <https://github.com/astral-sh/uv>
- Docker (optional, for containerization)

### Installation

First, install all dependencies including development tools:

```bash
uv sync --group dev
```

This command will:

- Create a virtual environment (if not exists)
- Install all project dependencies
- Install development tools (pytest, ruff, mypy)

### Usage

Once installed, you can run the example module:

```bash
uv run python -m uv_default_project
```

### Running Tests

Run tests locally:

```bash
uv run pytest tests/ -v
```

Or run tests in Docker:

```bash
docker build -t uv-default-project .
docker run --rm uv-default-project pytest tests/ -v
```

### Adding Tests

Create test files in the `tests/` directory following the pattern `test_*.py`:

```python
def test_your_feature():
    assert your_function() == expected_result
```

### Code Quality Checks

This project uses **ruff** for linting and **mypy** for static type checking.

**Run linting checks:**

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues where possible
uv run ruff check --fix .

# Format code
uv run ruff format .
```

**Run type checking:**

```bash
# Check types in source code
uv run mypy src/

# Check with verbose output
uv run mypy src/ --verbose
```

**Run all quality checks at once:**

```bash
# Comprehensive check
uv run ruff check . && uv run mypy src/ && uv run pytest tests/
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) implements a multi-stage pipeline that builds a Docker image, runs tests inside it, and (on `main`) can publish an automated release.

If you are new to CI/CD, you can treat this as:

1. Build an image (only when needed)
2. Run tests in that image
3. Optionally release from `main` based on commit messages

### Workflow Triggers

- **Push to main or dev branches** - Runs Build, Test, and Release (main only) jobs
- **Pull requests to main or dev** - Runs Build, Test, and Cleanup jobs
- **Version tags** (`v*`) - Triggers on tag pushes

### Pipeline Stages

#### 1. Build Docker Image

Intelligently builds and pushes Docker images to GitHub Container Registry:

- **Change Detection**: Checks if `Dockerfile` or `.dockerignore` changed since last commit/PR base
- **Smart Build**: Only rebuilds if Docker files changed OR branch-latest image doesn't exist
- **Tagging Strategy**:
  - `[branch]-[short-sha]` - Specific commit (e.g., `dev-abc1234`)
  - `[branch]-latest` - Latest build for the branch (e.g., `dev-latest`, `main-latest`)
- **Skips on**: Commits with `[skip ci]` message to avoid duplication

#### 2. Test

Runs code quality checks and pytest tests inside the Docker container:

- **Image Source**: Pulls the exact image built/verified in the build stage
- **Code Quality Checks**:
  - **Format Check**: Runs `ruff format --check` to ensure code formatting compliance
  - **Linting**: Runs `ruff check` to detect code style and potential issues
  - **Type Checking**: Runs `mypy` to verify static type annotations
- **Test Execution**: Runs `pytest tests/ -v --tb=short` in the container
- **Volume Mount**: Mounts `src/` and `tests/` directories for the latest code
- **Failure Handling**: Pipeline stops if any quality check or test fails

#### 3. Cleanup Images (Pull Requests Only)

Automatically cleans up Docker images for feature branches after successful PR merge:

- **Triggers**: Only on merged pull requests
- **Protected Branches**: Skips cleanup for `main` and `dev` branches
- **Feature Branches**: Deletes all images tagged with the branch name pattern
- **Cleanup Scope**: 
  - Removes both `-latest` and `-[sha]` tagged images for the branch
  - Removes all untagged Docker images

#### 4. Delete Branch (Pull Requests Only)

Automatically deletes the PR branch after successful merge:

- **Triggers**: Only on merged pull requests
- **Protected Branches**: Skips deletion for `main` and `dev` branches
- **Feature Branches**: Deletes the git branch using GitHub API
- **Permissions**: Requires `contents: write` permission

#### 5. Release Job (Main Branch Push Only)

Runs automatically after merge to main branch:

**Semantic Release Process**:

1. **Calculate Version**: Analyzes conventional commits to determine next version
   - `breaking:` or `BREAKING CHANGE:` → Major version bump (X.0.0)
   - `feat:` → Minor version bump (0.Y.0)
   - `fix:`, `perf:`, `revert:`, `build:` → Patch version bump (0.0.Z)
   - `docs:`, `style:`, `refactor:`, `test:`, `chore:`, `ci:` → No release

2. **Update Version Files**:
   - Updates version in `pyproject.toml` using sed
   - Generates/updates `CHANGELOG.md` with categorized release notes
   - Uses conventional commits preset with emoji sections

3. **Build Package**:
   - Runs `uv build` to create distribution packages
   - Generates both wheel (`.whl`) and source distribution (`.tar.gz`)
   - Validates that dist directory contains built packages

4. **Commit and Tag**:
   - Creates commit: `chore(release): X.Y.Z [skip ci]`
   - Includes full release notes in commit message
   - Creates and pushes git tag: `vX.Y.Z`
   - `[skip ci]` prevents triggering another CI run

5. **GitHub Release**:
   - Creates GitHub Release with the version tag
   - Attaches built distribution files (wheel and source tarball)
   - Includes categorized changelog for this version:
     - 💥 Breaking Changes
     - 💎 Features
     - 🔧 Fixes
     - 🚀 Performance
     - 🔨 Refactor
     - 🔙 Reverts
     - 👷 Build
     - 📦 Other (chore)
     - 🦊 CI/CD
     - 📔 Docs
     - ✨ Style
     - 🚨 Tests

6. **Back-merge to Dev**:
   - Automatically merges main back to dev branch
   - Prevents branch divergence
   - Uses `[skip ci]` to avoid triggering another pipeline
   - Only runs if release was actually created

### Semantic Versioning Rules

The project uses semantic versioning (SemVer) with conventional commits:

**Version Format**: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

- **MAJOR** (X.0.0): Breaking changes that require user action
  - Triggered by: `breaking:` type or `BREAKING CHANGE:` footer
  - Example: `breaking: remove deprecated endpoints`

- **MINOR** (0.Y.0): New features that are backward compatible
  - Triggered by: `feat:` type
  - Example: `feat: add export functionality`

- **PATCH** (0.0.Z): Bug fixes and minor improvements
  - Triggered by: `fix:`, `perf:`, `build:`, `revert:` types
  - Example: `fix: correct validation logic`

- **No Release**: Documentation, styling, tests, refactoring
  - Types: `docs:`, `style:`, `refactor:`, `test:`, `chore:`, `ci:`
  - These commits appear in changelog but don't trigger releases

### Release Configuration

The project uses semantic-release with these plugins (configured in [.releaserc.json](.releaserc.json)):

1. **@semantic-release/commit-analyzer**: Analyzes commits using conventional commits preset
2. **@semantic-release/release-notes-generator**: Generates categorized changelog with emojis
3. **@semantic-release/changelog**: Maintains CHANGELOG.md file
4. **@semantic-release/exec**: Updates pyproject.toml version and builds packages with uv
5. **@semantic-release/git**: Commits version changes and changelog
6. **@semantic-release/github**: Creates GitHub releases with distribution files attached

### Workflow Permissions

The workflow requires specific permissions for different jobs:

**Build Job**:

- `contents: read` - Checkout repository
- `packages: write` - Push Docker images to GitHub Container Registry

**Test Job**:

- `contents: read` - Checkout repository
- `packages: read` - Pull Docker images from GitHub Container Registry

**Cleanup Job** (PRs only):

- `packages: write` - Delete Docker images for feature branches

**Delete Branch Job** (PRs only):

- `contents: write` - Delete merged PR branches

**Release Job** (main branch only):

- `contents: write` - Create commits, tags, and releases
- `packages: write` - Publish packages to GitHub Packages
- `pull-requests: write` - Semantic release PR integration
- `issues: write` - Semantic release issue integration

## Docker Image

The Docker image is automatically published to GitHub Container Registry with branch-specific tagging:

### Image Naming Convention

```
ghcr.io/[OWNER]/[REPOSITORY]:[BRANCH]-latest
ghcr.io/[OWNER]/[REPOSITORY]:[BRANCH]-[SHORT_SHA]
```

Replace `[OWNER]` and `[REPOSITORY]` with your GitHub organization/user and repository name.

### Available Tags

- **Branch Latest**: `[branch]-latest` - Most recent build from a branch
  - `main-latest` - Latest production build
  - `dev-latest` - Latest development build
  - `feature-xyz-latest` - Latest build from feature branch

- **Commit Specific**: `[branch]-[short-sha]` - Specific commit (7-char SHA)
  - `main-abc1234` - Specific commit on main
  - `dev-def5678` - Specific commit on dev

### Pulling Images

```bash
# Latest from main branch
docker pull ghcr.io/[OWNER]/[REPOSITORY]:main-latest

# Latest from dev branch
docker pull ghcr.io/[OWNER]/[REPOSITORY]:dev-latest

# Specific commit on main branch
docker pull ghcr.io/[OWNER]/[REPOSITORY]:main-abc1234

# Specific commit on dev branch
docker pull ghcr.io/[OWNER]/[REPOSITORY]:dev-def5678
```

### Image Lifecycle

- **Main/Dev Branches**: Images persist indefinitely
- **Feature Branches**: Images automatically cleaned up after PR tests complete successfully
- **Build Strategy**: Only rebuilds if Dockerfile changes or image doesn't exist

## Development

### Commit Message Convention

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification for automated versioning and changelog generation.

If you use this template as-is, commit messages on `main` directly influence whether a release is created (and what version bump it gets).

#### Format

```
<type>: <description>

[optional body]

[optional footer]
```

#### Commit Types and Version Impact

| Type                              | Version Bump      | Section in Changelog | Example                             |
| --------------------------------- | ----------------- | -------------------- | ----------------------------------- |
| `breaking:` or `BREAKING CHANGE:` | **Major** (X.0.0) | 💥 Breaking Changes   | `breaking: remove deprecated API`   |
| `feat:`                           | **Minor** (0.Y.0) | 💎 Features           | `feat: add user authentication`     |
| `fix:`                            | **Patch** (0.0.Z) | 🔧 Fixes              | `fix: resolve login redirect issue` |
| `perf:`                           | **Patch** (0.0.Z) | 🚀 Performance        | `perf: optimize database queries`   |
| `build:`                          | **Patch** (0.0.Z) | 👷 Build              | `build: update dependencies`        |
| `revert:`                         | **Patch** (0.0.Z) | 🔙 Reverts            | `revert: undo feature X`            |
| `refactor:`                       | None              | 🔨 Refactor           | `refactor: restructure auth module` |
| `docs:`                           | None              | 📔 Docs               | `docs: update API documentation`    |
| `style:`                          | None              | ✨ Style              | `style: format code with black`     |
| `test:`                           | None              | 🚨 Tests              | `test: add unit tests for auth`     |
| `chore:`                          | None              | 📦 Other              | `chore: update .gitignore`          |
| `ci:`                             | None              | 🦊 CI/CD              | `ci: update workflow`               |

#### Examples

**Feature addition (Minor version bump)**:

```bash
git commit -m "feat: add password reset functionality"
```

**Bug fix (Patch version bump)**:

```bash
git commit -m "fix: resolve memory leak in parser"
```

**Breaking change (Major version bump)**:

```bash
git commit -m "feat!: change API endpoint structure

BREAKING CHANGE: API endpoints now use /v2/ prefix instead of /v1/"
```

**No release (documentation)**:

```bash
git commit -m "docs: update installation instructions"
```

#### Multi-line Commits

For more detailed commits with body and footer:

```bash
git commit -m "feat: add OAuth2 authentication

Implements OAuth2 flow with support for Google and GitHub providers.
Includes token refresh mechanism and session management.

Closes #123"
```

## License

See `LICENSE` for details.
