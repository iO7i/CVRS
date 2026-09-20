setup:
	python -m pip install -e ".[dev,adoption]"
check test:
	python tools/dev.py check
lint:
	python tools/dev.py lint
docs:
	python tools/dev.py docs
demo:
	python tools/dev.py demo
package:
	python tools/dev.py public-preview
