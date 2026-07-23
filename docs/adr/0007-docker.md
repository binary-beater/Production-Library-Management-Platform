# 0007 - Containerization via Docker & Multi-Container Docker Compose

## Context
Deployments and local developer environments suffer from "works on my machine" inconsistencies when setting up MySQL, Python environments, and system dependencies.

## Decision
We containerize the application using **Docker** and orchestrate multi-container environments (FastAPI + MySQL 8.0) using **Docker Compose**.

## Highlights
1. Explicit Docker layer caching (`COPY pyproject.toml .` before installing dependencies).
2. Multi-container orchestration with container healthchecks (`mysqladmin ping`).
3. Shared bridge network (`lmp_network`) isolating internal communication.
