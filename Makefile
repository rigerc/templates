PYTHON ?= python3

.PHONY: help check validate harness harness-matrix hooks

help: ## Show available targets
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

check: ## Repo consistency plus static validation (also runs in pre-commit)
	$(PYTHON) scripts/check_repo.py --strict
	$(PYTHON) scripts/validate_all.py --strict

validate: ## Static validation only
	$(PYTHON) scripts/validate_all.py --strict

harness: ## Generate, build, and test every template locally
	$(PYTHON) scripts/harness.py

harness-matrix: ## Also generate each placeholder alternative
	$(PYTHON) scripts/harness.py --matrix

hooks: ## Enable the tracked git hooks (pre-commit runs make check)
	git config core.hooksPath .githooks
	@echo "core.hooksPath = $$(git config core.hooksPath)"
