# Repo-root convenience: forward into package Makefiles
.DEFAULT_GOAL := help

.PHONY: help dataset-factory vision-engine channel3-ping

help:
	@echo "Design to Reality monorepo"
	@echo ""
	@echo "Packages:"
	@echo "  make -C dataset_factory help"
	@echo "  make -C vision_engine help"
	@echo ""
	@echo "Or from repo root:"
	@echo "  make dataset-factory help"
	@echo "  make vision-engine help"
	@echo "  make channel3-ping              # test Channel3 API"
	@echo ""
	@$(MAKE) -C dataset_factory help
	@echo ""
	@$(MAKE) -C vision_engine help

# Usage: make dataset-factory <target...>   e.g. make dataset-factory label LIMIT=3
dataset-factory:
	@$(MAKE) -C dataset_factory $(filter-out $@,$(MAKECMDGOALS))

# Usage: make vision-engine <target...>   e.g. make vision-engine run-fake
vision-engine:
	@$(MAKE) -C vision_engine $(filter-out $@,$(MAKECMDGOALS))

channel3-ping:
	@$(MAKE) -C vision_engine channel3-ping QUERY="$(QUERY)"

# Absorb extra goals used as arguments to the package targets above.
%:
	@:
