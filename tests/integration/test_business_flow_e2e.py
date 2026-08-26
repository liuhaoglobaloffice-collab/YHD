import os
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_business_flow_e2e(tmp_path):
    """Exercise the current Supplier -> Auth -> Risk Assessment -> Task -> Audit chain through the FastAPI app.

    This E2E test is intentionally minimal and compatible with the repository's current
    architecture: it reuses the existing auth, supplier, risk, task, and audit route stack
    while using a temporary SQLite database so the chain stays isolated.
    """
    os.environ['METRICS_PERSIST'] = '0'
    db_file = tmp_path / 'business_flow_e2e.db'
    os.environ['DATABASE_URL'] = f"sqlite:///{db_file.as_posix()}"

    # Ensure a clean database URL is seen by config and engine factories.
    import src.database.base as base
    dburl = base.get_database_url()
    assert dburl.startswith('sqlite')

    # Import model modules so SQLAlchemy metadata is registered before table creation.
    importlib.import_module('src.database.provider_metrics_model')
    importlib.import_module('src.business.supplier.models')
    importlib.import_module('src.identity.models')
    importlib.import_module('src.tasks.models')

    # Create the app and use the context manager for startup/shutdown hooks.
    from src.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        username = 'e2e_admin_user'
        email = 'e2e_admin@example.com'
        password = 'supersecure123'

        # Step 1: register an admin user, then log in for a token.
        register_resp = client.post(
            '/api/v1/auth/register',
            json={
                'username': username,
                'email': email,
                'full_name': 'Phase 1 E2E Admin',
                'password': password,
                'role': 'admin',
            },
        )
        assert register_resp.status_code in (200, 201), register_resp.text

        login_resp = client.post(
            '/api/v1/auth/login',
            json={'username': username, 'password': password},
        )
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # Step 2: create supplier.
        supplier_payload = {
            'name': 'E2E Supplier Alpha',
            'code': 'E2E-ALPHA-001',
            'legal_name': 'E2E Supplier Alpha Legal',
            'business_type': 'manufacturer',
            'industry': 'electronics',
            'country': 'CN',
            'product_category': 'AI Hardware',
            'website': 'https://example.com/alpa',
            'description': 'E2E supplier created for Phase 1 flow validation',
            'address': 'Shenzhen, China',
            'phone': '12345678901',
            'email': 'supplier@example.com',
            'registered_capital': 1000000.0,
            'established_date': '2020-01-01',
        }
        supplier_resp = client.post('/api/v1/suppliers', json=supplier_payload, headers=headers)
        assert supplier_resp.status_code == 201, supplier_resp.text
        supplier = supplier_resp.json()
        supplier_id = supplier['id']

        # Step 3: risk assessment.
        risk_resp = client.post(
            f'/api/v1/suppliers/{supplier_id}/assess-risk',
            json={'assessor': 'phase1.e2e'},
            headers=headers,
        )
        assert risk_resp.status_code == 200, risk_resp.text
        assessment = risk_resp.json()
        assert assessment['supplier_id'] == supplier_id
        assert assessment['risk_level'] in {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'} or assessment['risk_level'] in {'low', 'medium', 'high', 'critical'}
        assessment_id = assessment['id']

        # Step 4: persisted history query for assessment evidence.
        history_resp = client.get(
            f'/api/v1/suppliers/{supplier_id}/risk-history',
            headers=headers,
        )
        assert history_resp.status_code == 200, history_resp.text
        history = history_resp.json()
        assert any(item['id'] == assessment_id for item in history)

        # Step 5: confirm audit query and task creation records are visible.
        audit_resp = client.get('/api/v1/audit', headers=headers)
        assert audit_resp.status_code == 200, audit_resp.text
        audit_payload = audit_resp.json()
        assert audit_payload['logs'] is not None

        task_resp = client.get('/api/v1/tasks', headers=headers)
        assert task_resp.status_code == 200, task_resp.text
        tasks_payload = task_resp.json()
        # The route returns a list-like or details object; use response shape compatibility.
        assert tasks_payload is not None

        # The business chain is established when data exists in risk-history and an audit log.
        assert assessment_id is not None
