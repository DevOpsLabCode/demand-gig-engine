# Coverage Policy

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


The CI quality gate requires **90.00% statement and branch coverage** for the backend's production business-logic modules:

- `backend/gigs/facebook.py`
- `backend/gigs/models.py`
- `backend/gigs/payments.py`
- `backend/gigs/serializers.py`
- `backend/gigs/services.py`
- `backend/integrations/vibesmeet/`

The coverage denominator intentionally excludes generated migrations, Django/DRF framework wiring, admin registration, URL routing, management-command adapters, and HTTP transport views. Those files are thin integration/bootstrap layers and are validated separately by Django system checks, migration checks, static checks, and functional test runs.

CI runs line and branch coverage and fails when the measured total is below 90%:

```bash
python -m pytest backend -v \
  --cov \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-fail-under=90
```

A passing build therefore means the measured production business-logic coverage met or exceeded the 90% quality gate. Excluded files are listed explicitly in `.coveragerc`; broad wildcard exclusions of application packages are not permitted.
