REPO_PYTHON ?= .venv/bin/python

.PHONY: test-focused test-failed test-failed-first test-stepwise test-full

# Explicit selection is required; empty TESTS must not expand to the full suite.
test-focused:
	@test -n "$(TESTS)" || (echo 'Set TESTS to affected files or node IDs'; exit 2)
	$(REPO_PYTHON) -m pytest -p no:rerunfailures --no-cov $(TESTS)

# Zero cached failures selects no tests; it is not new-code verification.
test-failed:
	$(REPO_PYTHON) -m pytest -p no:rerunfailures --no-cov --last-failed --last-failed-no-failures=none

# Failed-first is a full suite with the existing coverage gate retained.
test-failed-first:
	$(REPO_PYTHON) -m pytest -p no:rerunfailures --failed-first

test-stepwise:
	$(REPO_PYTHON) -m pytest -p no:rerunfailures --no-cov --stepwise

test-full:
	$(REPO_PYTHON) -m pytest -p no:rerunfailures
