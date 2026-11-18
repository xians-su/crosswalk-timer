#!/bin/bash
# Run every test:  bash tests/run.sh      (see README, "測試", for what each one needs)
set -e; cd "$(dirname "$0")/.."
node tests/logic.test.mjs
bash tests/check.test.sh
python3 tests/page.test.py
