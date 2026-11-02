#!/usr/bin/env python3
"""Create an allowlisted deployment archive without personal DBs or secrets."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent
FILES='''server.py database.py online.py migrate_sqlite.py dictionary_enrichment.py
soumatome_import.py soumatome_parts_import.py source_coverage.py
requirements.txt render.yaml .env.example .gitignore
package_deploy.py'''.split()

def package(destination=None):
    destination=Path(destination or ROOT/'artifacts/kotoba-render.zip')
    destination.parent.mkdir(parents=True,exist_ok=True)
    paths=[ROOT/name for name in FILES]
    paths+=sorted(p for p in (ROOT/'web').glob('*') if p.is_file())
    paths+=sorted(p for p in (ROOT/'data').iterdir() if p.is_file() and p.suffix in {'.json','.csv','.tsv','.txt','.md'})
    paths+=sorted((ROOT/'docs').glob('*.md'))
    paths+=sorted((ROOT/'tests').glob('*.py'))
    paths+=sorted((ROOT/'scripts').glob('*.py'))
    if any(not p.is_file() for p in paths):raise ValueError('Missing packaged source file')
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in paths:archive.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(destination) as archive:
        for name in archive.namelist():
            if name.endswith(('.sqlite3','.db','.dump','.backup')) or name.startswith(('backups/','source_books/','.venv/')) or name=='.env':
                raise ValueError('Unsafe package entry')
    return destination

if __name__=='__main__':print(package())
