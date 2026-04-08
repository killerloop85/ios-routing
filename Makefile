PYTHON ?= python3
UPDATER := $(PYTHON) scripts/update_routing_lists.py
STREISAND := $(PYTHON) scripts/export_streisand_rules.py
STREISAND_URI := $(PYTHON) scripts/export_streisand_uri.py
HIDDIFY := $(PYTHON) scripts/export_hiddify_rules.py
HAPP := $(PYTHON) scripts/export_happ_routing.py
SMOKE := $(PYTHON) scripts/smoke_check.py
REGRESSION := $(PYTHON) scripts/check_regression_domains.py
REPORTS_DIR := reports

.PHONY: help smoke regression streisand streisand-uri streisand-qr hiddify hiddify-check happ happ-check offline update write report-json report-md ci

help:
	@printf "Available targets:\n"
	@printf "  make smoke        Run repository smoke checks\n"
	@printf "  make regression   Run the fixed regression domain suite\n"
	@printf "  make streisand    Write Streisand JSON and URI exports to disk\n"
	@printf "  make streisand-uri Write Streisand import URI exports to disk\n"
	@printf "  make streisand-qr Write compact Streisand split QR artifacts to disk\n"
	@printf "  make hiddify      Write Hiddify JSON exports to disk\n"
	@printf "  make hiddify-check Check Hiddify export sync without writing\n"
	@printf "  make happ         Write Happ routing exports to disk\n"
	@printf "  make happ-check   Check Happ export sync without writing\n"
	@printf "  make offline      Run offline updater preview\n"
	@printf "  make update       Fetch sources and print diff preview\n"
	@printf "  make write        Write regenerated lists to disk\n"
	@printf "  make report-json  Print JSON report to stdout\n"
	@printf "  make report-md    Write Markdown report to reports/routing-update.md\n"
	@printf "  make ci           Run the same local checks used by CI\n"

smoke:
	$(SMOKE)

regression:
	$(REGRESSION)

streisand:
	$(STREISAND) --write
	$(STREISAND_URI) --write

streisand-uri:
	$(STREISAND_URI) --write

streisand-qr:
	$(STREISAND) --write
	$(STREISAND_URI) --write

hiddify:
	$(HIDDIFY) --write

hiddify-check:
	$(HIDDIFY) --offline

happ:
	$(HAPP) --write

happ-check:
	$(HAPP) --offline

offline:
	$(UPDATER) --offline

update:
	$(UPDATER)

write:
	$(UPDATER) --write

report-json:
	$(UPDATER) --report-json -

report-md:
	mkdir -p $(REPORTS_DIR)
	$(UPDATER) --report-md $(REPORTS_DIR)/routing-update.md

ci: smoke
