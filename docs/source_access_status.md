# Sources requiring permission or an alternative authorized feed

As of 2026-11-06, the GitHub Actions robot checked the robots policy before collecting.

- **PEPPY**, https://www.peppy.jp/seminar : not crawled; robots.txt check did not permit access from GitHub Actions. `config.py` enabled=false.
- **EDUWARD Press/EDUONE**, https://eduone.jp/lecture/ : not crawled; robots.txt check did not permit access from GitHub Actions. `config.py` enabled=false.
- Their collection code stays in the repository so it can be activated only after the site's policies and an authorized feed/API or permission are confirmed. Do not bypass a refusal.
- Official specialist-society sources JAVNU, JSVD, JVCS, and JSVC are enabled for evaluation. Actual access and extraction outcomes must be checked in `data/run_status.json`. An enabled site does NOT guarantee successful collection.
- No Claude API key is required for these sources.
