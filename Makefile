.DEFAULT_GOAL := help
.PHONY: help install dev fetch check_updates silver gold benchmark benchmark_quick models all app test test_unit test_integration lint format type clean docker_build docker_up dq validate_releases

PY  := .venv/bin/python
PIP := .venv/bin/pip
PYTHONPATH := src

help:
	@echo "Komandat e përpunimit (inxhinieri e të dhënave):"
	@echo ""
	@echo "  install           krijo venv nëse mungon dhe instalo varësitë"
	@echo "  dev               instalo edhe veglat e zhvillimit (ruff, mypy, pytest, pre-commit)"
	@echo ""
	@echo "  fetch             shkarko bronze OCDS"
	@echo "  check_updates     kontrollo për rekorde të reja të tenderëve në burim"
	@echo "  silver            bronze -> silver"
	@echo "  gold              silver -> tender_features + 3 përmbledhje gold"
	@echo "  benchmark         23 konfigurime të pambikëqyrura + 12 të mbikëqyrura"
	@echo "  benchmark_quick   provë e shpejtë e motorit të benchmark-ut (sekonda)"
	@echo "  models            tender_features + champions -> tender_summary + modele/SHAP"
	@echo "  all               ekzekuto DAG-un e plotë (anashkalon fazat e freskëta)"
	@echo "  app               nis panelin Streamlit"
	@echo ""
	@echo "  validate_releases verifiko hash-et e publikimeve dhe zinxhirin e prejardhjes"
	@echo "  dq                ekzekuto të gjitha suitat e pritshmërive DQ"
	@echo "  test              pytest (njësi + kontrata + integrim + faqet UI)"
	@echo "  test_unit         vetëm njësi + kontrata (i shpejtë)"
	@echo "  test_integration  testet e integrimit"
	@echo "  lint              ruff check + kontroll formati"
	@echo "  format            ruff format (në vend)"
	@echo "  type              mypy mbi src/thesis"
	@echo ""
	@echo "  docker_build      ndërto imazhin Docker të prodhimit"
	@echo "  docker_up         docker compose up për panelin"
	@echo ""
	@echo "  clean             hiq skedarët e përkohshëm; ruaj të dhënat dhe modelet"

install:
	@test -d .venv || python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e .

dev: install
	$(PIP) install -e '.[dev,notebooks]'
	.venv/bin/pre-commit install

fetch:
	$(PY) -m thesis pipeline bronze

check_updates:
	$(PY) -m thesis pipeline check-updates

silver:
	$(PY) -m thesis pipeline silver

gold:
	$(PY) -m thesis pipeline gold

benchmark:
	$(PY) -m thesis pipeline benchmark

benchmark_quick:
	$(PY) -m thesis pipeline benchmark --quick

models:
	$(PY) -m thesis pipeline ml

all:
	$(PY) -m thesis pipeline run
	@echo ""
	@echo "Përpunimi përfundoi. Ekzekuto 'make app' për panelin."

dq:
	$(PY) -m thesis dq run

validate_releases:
	$(PY) -m thesis pipeline validate-releases

app:
	$(PY) -m thesis ui

test:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m pytest tests -v --color=yes

test_unit:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m pytest tests/unit tests/contracts -v --color=yes

test_integration:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m pytest tests/integration -v --color=yes

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

type:
	$(PY) -m mypy src/thesis

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis htmlcov
	rm -f .coverage .coverage.* coverage.xml
	find src streamlit_app tests airflow_dags scripts notebooks -type d \( -name __pycache__ -o -name .ipynb_checkpoints \) -prune -exec rm -rf {} +
	@echo "U hoqën skedarët e përkohshëm. Të dhënat, modelet dhe mjedisi .venv u ruajtën."

docker_build:
	docker build -t kosovo-procurement-thesis:dev .

docker_up:
	docker compose up app
