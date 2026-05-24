from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import auth_headers_for

client = TestClient(app)


def test_class_and_lab_routes_registered():
    paths = {(r.path, tuple(sorted(r.methods))) for r in app.routes}
    assert ('/api/admin/classes', ('GET',)) in paths or ('/api/admin/classes', ('GET', 'HEAD'))
    assert any(p == '/api/admin/labs' for p, _ in paths)


def test_student_cannot_manage_classes_and_labs():
    h = auth_headers_for('student1')
    assert client.post('/api/admin/classes', json={'name': 'X'}, headers=h).status_code == 403
    assert client.post('/api/admin/labs', json={'class_id': 1, 'name': 'L', 'default_pool_id': 1}, headers=h).status_code == 403


def test_admin_create_class_and_enrollment_and_lab_validation():
    h = auth_headers_for('admin')
    r = client.post('/api/admin/classes', json={'name': 'BIO101', 'term': '2026S'}, headers=h)
    assert r.status_code == 200
    class_id = r.json()['data']['id']

    r = client.post(f'/api/admin/classes/{class_id}/enrollments', json={'user_id': 2, 'role': 'student'}, headers=h)
    assert r.status_code == 200
    r2 = client.post(f'/api/admin/classes/{class_id}/enrollments', json={'user_id': 2, 'role': 'student'}, headers=h)
    assert r2.status_code == 200
    assert r2.json()['data']['id'] == r.json()['data']['id']

    bad = client.post('/api/admin/labs', json={'class_id': class_id, 'name': 'Lab', 'default_pool_id': 99999}, headers=h)
    assert bad.status_code == 422
