source_paths = terraform_plan_approval
container = docker run -i --rm -u $$(id -u):$$(id -g) -v "$$(pwd)":"$$(pwd)" -w "$$(pwd)" $(3) $(1) $(2)
compose = docker-compose -f test/docker-compose.yml $(1)
compose_run = UID_STRING=$$(id -u):$$(id -g) $(call compose, run --rm $(3) $(1) $(2))

user_cache_dir := $(HOME)/.cache

format:
	$(call container, dockerizedtools/black:19.10b0, .)

check: check-format check-types check-lint

check-types:
	$(call container, dockerizedtools/mypy:0.782, --ignore-missing-imports $(source_paths) test)

check-lint:
	$(call container, dockerizedtools/flake8:3.8.3, $(source_paths) test)

check-format:
	$(call container, dockerizedtools/black:19.10b0, --check .)

dependencies:
	rm -rf vendor
	$(call container, python:3.8.3-alpine3.12, pip install --user -r requirements.txt, \
		-e PYTHONUSERBASE=vendor \
		-v "$(user_cache_dir)":"$(user_cache_dir)" -e XDG_CACHE_HOME="$(user_cache_dir)")

test-setup:
	UID_STRING=$$(id -u):$$(id -g) $(call compose, up -d)

.PHONY: test
test:
	$(call compose_run, tests, python -m unittest -v)

test-cleanup:
	-$(call compose, down -t 0)
