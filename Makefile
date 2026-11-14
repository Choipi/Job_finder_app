.PHONY: install backend-install frontend-install backend frontend test build

install: backend-install frontend-install

backend-install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

frontend-install:
	cd frontend && npm install

backend:
	cd backend && .venv/bin/python run.py

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest

build:
	cd frontend && npm run build
