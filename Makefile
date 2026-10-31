PY := .venv/bin/python

.PHONY: setup render compare gallery approve clean

setup:            ## create virtualenv and install dependencies
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt

render:           ## render all designs (or: make render IDS="hug love")
	$(PY) tools/render.py $(IDS)
	$(PY) tools/gallery.py

compare: render   ## photo vs. recreation sheets (only for designs with reference photos)
	$(PY) tools/compare.py $(IDS)
	$(PY) tools/gallery.py

gallery:          ## build/index.html to browse build/ (open build/index.html)
	$(PY) tools/gallery.py

approve:          ## copy approved files to designs/<id>/ : make approve IDS=hug
	@test -n "$(IDS)" || (echo "usage: make approve IDS=\"hug love\""; exit 1)
	@for id in $(IDS); do \
		mkdir -p designs/$$id && \
		cp build/$$id-front.svg build/$$id-front.png build/$$id-back.svg build/$$id-back.png build/$$id-preview.jpg designs/$$id/ && \
		echo "approved: designs/$$id"; \
	done

clean:
	rm -rf build
