.PHONY: all lint test demo-repl demo-rpc run clean

all: lint test demo-repl demo-rpc

lint:
	python -m flake8 --max-line-length=79 src tests

test:
	python -m coverage run --branch -m pytest tests/test_mbt.py -v
	python -m coverage report -m

demo-repl:
	python -m src.demo_repl

demo-rpc:
	python -m src.demo_client

run:
	python -m src.demo_client

clean:
	python -c "import shutil, os; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', 'htmlcov')]; [os.remove(f) for f in ('.coverage', 'journal.log') if os.path.exists(f)]"
