"""Run the original study-engine suite against isolated PostgreSQL schemas."""
import os
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_app import KotobaTests
from tests.test_online import OnlineTests

class PostgresStudyTests(KotobaTests):
    def setUp(self):
        self.fixture=OnlineTests('runTest');self.fixture.setUp()
        super().setUp()
    def tearDown(self):
        super().tearDown();self.fixture.tearDown()

if __name__=='__main__':
    if not os.environ.get('TEST_DATABASE_URL'):raise SystemExit('Set TEST_DATABASE_URL to a disposable test database')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PostgresStudyTests))
    raise SystemExit(not result.wasSuccessful())
