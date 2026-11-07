PORT ?= 8000

.PHONY: run gallery

run:
	@echo "Gallery: http://localhost:$(PORT)/gallery/"
	python3 -m http.server $(PORT)

gallery:
	python3 src/gallery.py
