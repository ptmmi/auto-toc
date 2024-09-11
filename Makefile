VENV_PATH = .venv

init:
	python -m venv $(VENV_PATH)
	$(VENV_PATH)/bin/pip install -r requirements.txt

clean:
	rm -rf $(VENV_PATH)

run:
	$(VENV_PATH)/bin/python auto-toc.py