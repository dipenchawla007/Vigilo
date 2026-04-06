.PHONY: test run ui docker-build docker-up lint

test:
	PYTHONPATH=src pytest tests/ -v

run:
	PYTHONPATH=src python3 -m sentinel.graph --product-name metformin --product-type drug

ui:
	PYTHONPATH=src streamlit run ui/app.py

docker-build:
	docker compose build

docker-up:
	docker compose up sentinel-ui

sandbox-build:
	docker build -t sentinel-sandbox ./sandbox

lint:
	python -m py_compile src/sentinel/graph.py
	python -m py_compile src/sentinel/clients/llm.py
	python -m py_compile src/sentinel/clients/openfda.py
	python -m py_compile src/sentinel/export_pdf.py
	python -m py_compile src/sentinel/nodes/execute.py
