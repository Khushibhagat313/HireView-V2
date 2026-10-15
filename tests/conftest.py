import pytest


@pytest.fixture
def make_company():
    """Create throwaway companies for a test and delete them afterwards (cascades to everything they own),
    so test runs never leave rows behind or write into the shared Test Co data."""
    from src.db.store import create_company, delete_company

    created = []

    def make(name: str = "Pytest Co"):
        company = create_company(name)
        created.append(company.id)
        return company

    yield make
    for company_id in created:
        delete_company(company_id)
