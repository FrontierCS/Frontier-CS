# Project Rules for Frontier-CS

## Backend Selection

**NEVER change the backend due to missing credentials or CI configuration issues.**

- Research track: always uses SkyPilot (cloud VMs)
- Algorithmic track: always uses Docker (local)

If CI fails due to credentials/permissions, fix the credentials - do NOT change the code to use a different backend. The backend choice is intentional for each track's evaluation requirements.
