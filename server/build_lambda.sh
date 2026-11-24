#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -x "../venv/bin/python" ]; then
  PYTHON="../venv/bin/python"
else
  PYTHON="python3"
fi

rm -rf package deployment.zip
mkdir -p package

# 1. Install Linux x86_64 Python 3.14 wheels matching AWS Lambda AL2023 (glibc 2.34).
#    Preserves .dist-info directories (required at runtime by email-validator).
"$PYTHON" -m pip install \
  --requirement requirements.txt \
  --target package \
  --platform manylinux_2_34_x86_64 \
  --platform manylinux_2_28_x86_64 \
  --platform manylinux_2_24_x86_64 \
  --platform manylinux_2_17_x86_64 \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.14 \
  --only-binary=:all: \
  --upgrade

# 2. Copy application code only (never copies .env, tests/, alembic/, or __pycache__)
cp main.py config.py database.py db_models.py dependencies.py models.py package/
cp -r routers services package/
find package -type d -name "__pycache__" -exec rm -rf {} +

# 3. Zip package/ using Python stdlib (no OS zip binary required) and check Lambda limits
"$PYTHON" - <<'PY'
import pathlib
import zipfile

pkg = pathlib.Path("package")
out = pathlib.Path("deployment.zip")
unzipped = 0

with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(pkg.rglob("*")):
        if path.is_file():
            unzipped += path.stat().st_size
            zf.write(path, path.relative_to(pkg))

unzipped_mb = unzipped / 1024 / 1024
zipped_mb = out.stat().st_size / 1024 / 1024
print(f"Built server/{out.name}: zipped={zipped_mb:.1f} MB, unzipped={unzipped_mb:.1f} MB (Lambda limit: 250 MB)")
assert unzipped_mb < 250, f"Package exceeds Lambda 250 MB unzipped limit ({unzipped_mb:.1f} MB)"
PY

# 4. Clean up temporary staging dir so local pytest does not collect vendored package tests
rm -rf package
