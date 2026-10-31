PY := .venv/bin/python
# FORCE=1 : render also approved designs (into build/ only) / replace an approved design
FORCE_FLAG_RENDER  := $(if $(filter 1,$(FORCE)),--include-approved)
FORCE_FLAG_APPROVE := $(if $(filter 1,$(FORCE)),--force)

.PHONY: setup render compare gallery approve site clean

setup:            ## create virtualenv and install dependencies
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt

render:           ## render drafts (IDS="dance laugh" to limit; FORCE=1 incl. approved)
	$(PY) tools/render.py $(FORCE_FLAG_RENDER) $(IDS)
	$(PY) tools/gallery.py

compare:          ## photo vs. recreation sheets for designs with reference photos
	$(PY) tools/compare.py $(IDS)
	$(PY) tools/gallery.py

gallery:          ## rebuild build/index.html (drafts + approved)
	$(PY) tools/gallery.py

approve:          ## designs/<id>/ from build: make approve IDS="dance laugh" (FORCE=1 to replace)
	@test -n "$(IDS)" || (echo "usage: make approve IDS=\"dance laugh\""; exit 1)
	$(PY) tools/approve.py $(FORCE_FLAG_APPROVE) $(IDS)
	$(PY) tools/gallery.py

site:             ## build the GitHub Pages site in docs/ from approved designs
	$(PY) tools/site.py

clean:            ## remove build/ (never touches designs/)
	rm -rf build
