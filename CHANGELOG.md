## [2.1.0](https://github.com/f6ra07nk14/uv-default-project/compare/v2.0.1...v2.1.0) (2026-01-23)


### 👷 Build

* optimize Dockerfile by using bind mounts for uv sync dependencies ([c1a5c33](https://github.com/f6ra07nk14/uv-default-project/commit/c1a5c3374a9a788f00e0a3e693ab285007efb749))


### 🦊 CI/CD

* simplify CI workflow by removing Docker image pull and using local commands for code quality checks and testing ([00b3158](https://github.com/f6ra07nk14/uv-default-project/commit/00b31588266d03dd184c9c773ff844db7dba2b1c))
* update CI workflow to include tests directory for linting and type checking ([0d13559](https://github.com/f6ra07nk14/uv-default-project/commit/0d1355922b9310bf551e8aca051b383eb2f0b687))


### 📔 Docs

* update README with new delete-branch job documentation ([75f7ba2](https://github.com/f6ra07nk14/uv-default-project/commit/75f7ba235287e6de79cb7e5dc6a47d809a1500a3))


### 💎 Features

* add CI job to delete PR branch after merge ([18dd07b](https://github.com/f6ra07nk14/uv-default-project/commit/18dd07b275ff8d6e53488d170b3287374b09ad7b))
* add cleanup of untagged Docker images in cleanup-images job ([85c8784](https://github.com/f6ra07nk14/uv-default-project/commit/85c8784a4d49dc48b32b5f2ac9a64845055bba4e))


### 🔧 Fixes

* check HTTP response code when deleting branch ([632766d](https://github.com/f6ra07nk14/uv-default-project/commit/632766d0d5e9d7755f1682b8af8c10287fe9dfe6))
* correct mypy command and shell operators in CI workflow ([48efe47](https://github.com/f6ra07nk14/uv-default-project/commit/48efe476554ac4430077c10b4675017869678f0f))
* correct regex in prepareCmd to match version line in pyproject.toml ([4eadff1](https://github.com/f6ra07nk14/uv-default-project/commit/4eadff11098ad45cb3cb7f97a8f42367713e4972))
* improve event context validation for workflow conditions ([977d71c](https://github.com/f6ra07nk14/uv-default-project/commit/977d71c21f87dfe4b0c950fb89b7abcea9e92230))
* set PYTHONPATH for pytest to find source modules ([c3144f7](https://github.com/f6ra07nk14/uv-default-project/commit/c3144f7bf438ad0d42f84e3770fe6bf6da2484aa))
* trigger cleanup-images only after successful PR merge ([8298115](https://github.com/f6ra07nk14/uv-default-project/commit/8298115b3fdc46a9cc1fa68631e0209d38741df9))
* update Python version in pyproject.toml to 3.9 ([053eeca](https://github.com/f6ra07nk14/uv-default-project/commit/053eeca60d9624a098f055b4965324476d1933b8))


### 🔨 Refactor

* use absolute path for PYTHONPATH assignment ([6f96df4](https://github.com/f6ra07nk14/uv-default-project/commit/6f96df463529a4a2eaf6ade7b1e4c6bcc0302246))

## [2.0.1](https://github.com/f6ra07nk14/uv-default-project/compare/v2.0.0...v2.0.1) (2026-01-23)


### 👷 Build

* add ruff and mypy to dependency groups and configure linting settings ([d4a4465](https://github.com/f6ra07nk14/uv-default-project/commit/d4a4465fcc72e24a67b185e96c60f54d75bc134a))
* update Dockerfile to install development dependencies with uv sync ([92e1d60](https://github.com/f6ra07nk14/uv-default-project/commit/92e1d60e7ad87679fd6e47c05933ed4d1085db21))


### 🦊 CI/CD

* enhance CI workflow with code quality checks and uv.lock detection ([f28658b](https://github.com/f6ra07nk14/uv-default-project/commit/f28658ba3865cb57eb09085e175c927b0ffa99ca))


### 📔 Docs

* enhance README with detailed project structure and CI/CD pipeline information ([ebbe64f](https://github.com/f6ra07nk14/uv-default-project/commit/ebbe64f3c21995ca8a351dd107d0e3df4d1b0a70))
* update README to include usage instructions and code quality checks ([30eac0e](https://github.com/f6ra07nk14/uv-default-project/commit/30eac0ed02d7d1744131490a57817755bf9d2c6b))

## [2.0.0](https://github.com/f6ra07nk14/uv-default-project/compare/v1.1.0...v2.0.0) (2026-01-23)


### ⚠ BREAKING CHANGES

* The greet function now accepts an optional formal parameter.
This changes the function signature from greet(name) to greet(name, formal=False).
Existing code that uses the function will still work due to the default parameter,
but the API has been extended.

### 👷 Build

* rename optional-dependencies to dependency-groups in pyproject.toml ([e5f1ae5](https://github.com/f6ra07nk14/uv-default-project/commit/e5f1ae5b4d630e97e975bb3a7907165ff53ebe7f))
* update Dockerfile to include uv.lock and modify installation command ([a52417d](https://github.com/f6ra07nk14/uv-default-project/commit/a52417dcb757652e0f7df88a0c6ff80a1a30881b))


### 📦 Other

* update .gitignore to include .idea directory and add uv.lock file ([f328257](https://github.com/f6ra07nk14/uv-default-project/commit/f328257890c7df3bca3d691a1581900185f839ad))


### 🦊 CI/CD

* update release configuration to include .tar.gz and .whl assets ([5deae5f](https://github.com/f6ra07nk14/uv-default-project/commit/5deae5f2527a647aa7af09645aaf5597bb707358))


### 💎 Features

* add formal parameter to greet function ([94cf09e](https://github.com/f6ra07nk14/uv-default-project/commit/94cf09e1b96f5109623a670a30b5d8142ffb9e9f))

## [1.1.0](https://github.com/f6ra07nk14/uv-default-project/compare/v1.0.3...v1.1.0) (2026-01-23)


### 💎 Features

* add multiplication function and improve docstring formatting ([b4bd412](https://github.com/f6ra07nk14/uv-default-project/commit/b4bd41235919c893550169a86680fdd6c540d1b8))

## [1.0.3](https://github.com/f6ra07nk14/uv-default-project/compare/v1.0.2...v1.0.3) (2026-01-23)


### 🔧 Fixes

* remove PyPI publish step and incorrect version extraction in release workflow ([#12](https://github.com/f6ra07nk14/uv-default-project/issues/12)) ([f915e06](https://github.com/f6ra07nk14/uv-default-project/commit/f915e06e7e22aa008deda99880d5c98cae45a257))

## [1.0.2](https://github.com/f6ra07nk14/uv-default-project/compare/v1.0.1...v1.0.2) (2026-01-23)


### 🔧 Fixes

* change assets from false to empty array in semantic-release config ([aa72fec](https://github.com/f6ra07nk14/uv-default-project/commit/aa72feca2265029d542d2a3268b21ebac420af87)), closes [#9](https://github.com/f6ra07nk14/uv-default-project/issues/9)

## [1.0.1](https://github.com/f6ra07nk14/uv-default-project/compare/v1.0.0...v1.0.1) (2026-01-23)


### 🔧 Fixes

* add issues:write permission to release job for semantic-release ([486a39f](https://github.com/f6ra07nk14/uv-default-project/commit/486a39f97c323178fab6ee44d9982bebda025818)), closes [#4](https://github.com/f6ra07nk14/uv-default-project/issues/4)

## 1.0.0 (2026-01-23)


### 📔 Docs

* update README with comprehensive CI/CD documentation ([73b5eba](https://github.com/f6ra07nk14/uv-default-project/commit/73b5ebaa5089f61825615db0ea94bb609c40b20a))


### 💎 Features

* implement branch-specific Docker tagging and GitHub Packages distribution ([5bc157d](https://github.com/f6ra07nk14/uv-default-project/commit/5bc157dfd621362f3a5e5ebaab50b6713c06f833))
* implement comprehensive CI/CD workflow with semantic versioning ([64b0429](https://github.com/f6ra07nk14/uv-default-project/commit/64b0429e41f1761e41e6e8e3f1ab8b7aafe267c9))


### 🔧 Fixes

* improve release detection and package publishing ([1c7ada0](https://github.com/f6ra07nk14/uv-default-project/commit/1c7ada0d7a2baba224b042b2f90e0fe1e2a9478b))
* Sanitize branch names for Docker tags and add cleanup job ([d1e9c68](https://github.com/f6ra07nk14/uv-default-project/commit/d1e9c684542da949b820e32447d62be3d00fa85b))
* Use centralized branch name in metadata action tags ([53955fb](https://github.com/f6ra07nk14/uv-default-project/commit/53955fbebccca245db5dbfb0a540d8c60d1a2f69))


### 🔨 Refactor

* simplify package distribution step ([077e9da](https://github.com/f6ra07nk14/uv-default-project/commit/077e9da058c8886f020ae45142d7e4435a4b3e91))


### ✨ Style

* remove trailing spaces from CI workflow ([88855f1](https://github.com/f6ra07nk14/uv-default-project/commit/88855f14fe249e1893608646ad5ddd6f7b7487e3))

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Initial project setup with uv package manager
- Docker support with CI/CD integration
- Automated testing with pytest
