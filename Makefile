PYTHON ?= python3

.PHONY: help check validate smoke

help: ## Show available targets
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

check: ## Repo consistency plus static validation of every template
	$(PYTHON) scripts/check_repo.py --strict
	$(PYTHON) scripts/validate_all.py --strict

validate: ## Static validation only (same as the CI validate job)
	$(PYTHON) scripts/validate_all.py --strict

smoke: ## Generate and build every template for real (needs cargo-generate)
	$(PYTHON) scripts/validate_all.py --strict --smoke
