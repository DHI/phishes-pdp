# PHISHES PDP — Repository Design

Version: 1.0
Date: 2026-02-25
Status: Proposed baseline

## 1. Purpose

This document defines the repository-level design for PHISHES PDP.

It describes:

- Top-level scope and boundaries
- Repository design principles
- Responsibilities of root-level artifacts
- Relationship between repository-level and module-level documentation

## 2. Scope and Boundaries

### In scope

- Overall repository structure and navigation
- Governance and contributor-facing policy files
- Cross-module discoverability conventions
- Documentation layering across root and module documents

### Out of scope

- Internal architecture of `data-download-tool`
- Internal architecture of `plant-growth-module`
- Detailed module workflows, APIs, and runtime behavior

## 3. Design Principles

1. **Separation of concerns**
   - Each module owns its own source code, dependencies, notebooks, and technical specs.

2. **Stable top-level contract**
   - Root-level files define governance, onboarding, and orientation for contributors and users.

3. **Module autonomy**
   - Modules can evolve independently as long as their published interfaces and docs remain coherent.

4. **Documentation layering**
   - Root docs explain repository composition; module docs explain implementation details.

## 4. Repository Responsibilities

The top-level repository is responsible for:

- Presenting a unified project overview and clear entry points
- Defining contribution, security, citation, and code-of-conduct policies
- Maintaining a consistent high-level structure for modules and shared assets
- Linking users to the correct module-specific setup and technical documentation

## 5. Documentation Contract

Repository-level documents should describe:

- **What exists** in the repository
- **How the parts relate**
- **Where to find detailed documentation**

Module-level documents should describe:

- **How each module works internally**
- Module-specific architecture, workflows, interfaces, and constraints

## 6. Top-Level Artifact Roles

- `README.md`: user-facing project overview and navigation
- `phishes-pdp.md`: agent/context-oriented high-level repository guidance
- `REPOSITORY_DESIGN.md`: repository design baseline and scope boundaries
- Policy files (`SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`): governance and compliance context
- Module folders (`data-download-tool/`, `plant-growth-module/`): implementation ownership and module documentation

## 7. Acceptance Criteria

This repository design is considered effective when:

- Users can identify module entry points from root docs
- Contributors can find governance policies without module-level deep dives
- Repository-level docs avoid duplicating module internals
- Module documentation remains the authoritative source for implementation details
