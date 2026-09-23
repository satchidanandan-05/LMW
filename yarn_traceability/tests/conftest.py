import pytest

from database.database import init_database, make_engine


@pytest.fixture
def engine():
    eng = make_engine("sqlite:///:memory:")
    init_database(eng, sample_data=True, bcrypt_rounds=4)
    yield eng
    eng.dispose()
