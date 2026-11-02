"""Read-only field-by-field SQLite/Neon verification. Never print connection details."""
import datetime as dt
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import load_environment
from migrate_sqlite import FIELDS
import server


def verify(source):
    if not os.environ.get('DATABASE_URL'):
        raise ValueError('DATABASE_URL is required for PostgreSQL verification')
    source = Path(source).resolve()
    result = {}
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as local:
        local.row_factory = sqlite3.Row
        with server.connect() as remote:
            for table, fields in FIELDS.items():
                def canonical(rows):
                    values = []
                    for row in rows:
                        row = dict(row)
                        if table == 'progress':
                            original = dict(row)
                            row = {'phase': 'choice', 'streak': 0, 'mastered': 0,
                                   'last_mode': None, **row}
                            if 'phase' not in original and row['stage'] >= 3 and row['successes'] >= 3:
                                row['phase'] = 'write'
                        for key in ('due', 'created'):
                            if row.get(key):
                                value = dt.datetime.fromisoformat(row[key])
                                if value.tzinfo is None:
                                    raise ValueError('Timestamp missing timezone: ' + table)
                                row[key] = value.astimezone(dt.timezone.utc).isoformat()
                        values.append(json.dumps({f: row.get(f) for f in fields},
                                                 ensure_ascii=False, sort_keys=True))
                    return sorted(values)
                before = canonical(local.execute('SELECT * FROM ' + table))
                after = canonical(remote.execute('SELECT * FROM ' + table))
                if before != after:
                    raise ValueError('Data mismatch: ' + table)
                result[table] = {'sqlite': len(before), 'neon': len(after),
                                 'all_fields_equal': True,
                                 'sha256': hashlib.sha256('\n'.join(before).encode()).hexdigest()}
    return result


if __name__ == '__main__':
    load_environment()
    try:
        print(json.dumps(verify(ROOT / 'progress.sqlite3'), indent=2))
    except Exception as error:
        print('Verification failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
