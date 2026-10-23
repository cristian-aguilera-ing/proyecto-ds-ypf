PY := .venv/bin/python

.PHONY: venv data train test api up down notebooks

venv:
	python3 -m venv .venv && $(PY) -m pip install -r requirements.txt && $(PY) -m pip install -e .

data:
	$(PY) -m ypf_ds.data.clean

train:
	$(PY) -m ypf_ds.models.train --trials 25

test:
	$(PY) -m pytest -q

api:
	.venv/bin/uvicorn api.app:app --reload

notebooks:
	for nb in notebooks/0*.ipynb; do .venv/bin/jupyter nbconvert --to notebook --execute --inplace $$nb; done

up:
	docker compose up --build -d

down:
	docker compose down
