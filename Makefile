PYTHON ?= python

.PHONY: ci-backend ci-frontend ci-build ci-integration

ci-backend:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r platform/backend/requirements.txt -r platform/backend/requirements-dev.txt
	MUP_DATABASE_URL=sqlite:///./platform/tests/test.db PYTHONPATH=platform/backend ruff check platform/backend/app platform/tests
	MUP_DATABASE_URL=sqlite:///./platform/tests/test.db PYTHONPATH=platform/backend pytest -q platform/tests/unit

ci-frontend:
	corepack enable
	cd platform/frontend && pnpm install --no-frozen-lockfile
	cd platform/frontend && pnpm lint
	cd platform/frontend && pnpm test
	cd platform/frontend && pnpm build

ci-build:
	docker build -t manga-update-platform-ci:latest platform

ci-integration:
	MUP_DATABASE_URL=sqlite:///./platform/tests/test.db PYTHONPATH=platform/backend pytest -q platform/tests/integration
