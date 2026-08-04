from app import app
import json

with app.test_client() as c:
    # Login first
    resp = c.post('/admin_login', json={"username": "admin", "password": "admin123"})
    print('Login:', resp.status_code)

    # Test 1: Missing tracking
    resp = c.post('/admin', json={"parcelStatus": "In Transit", "city": "NYC", "phone": "1234567890"})
    print('Missing tracking:', resp.status_code, resp.get_json())

    # Test 2: Missing parcelStatus
    resp = c.post('/admin', json={"tracking": "T123", "city": "NYC", "phone": "1234567890"})
    print('Missing parcelStatus:', resp.status_code, resp.get_json())

    # Test 3: Missing city
    resp = c.post('/admin', json={"tracking": "T123", "parcelStatus": "In Transit", "phone": "1234567890"})
    print('Missing city:', resp.status_code, resp.get_json())

    # Test 4: Missing phone
    resp = c.post('/admin', json={"tracking": "T123", "parcelStatus": "In Transit", "city": "NYC"})
    print('Missing phone:', resp.status_code, resp.get_json())

    # Test 5: Empty string (should fail)
    resp = c.post('/admin', json={"tracking": "", "parcelStatus": "In Transit", "city": "NYC", "phone": "1234567890"})
    print('Empty tracking:', resp.status_code, resp.get_json())

    # Test 6: All valid
    resp = c.post('/admin', json={"tracking": "VALID123", "parcelStatus": "In Transit", "city": "NYC", "phone": "1234567890"})
    print('All valid:', resp.status_code, resp.get_json())
