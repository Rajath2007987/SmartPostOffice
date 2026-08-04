from app import app
import json

sample = {
    "tracking": "DUPTEST123",
    "parcelStatus": "In Transit",
    "city": "TestCity",
    "phone": "9999999999",
    "email": "test@example.com",
    "sender_name": "Tester",
    "weight": "1kg",
    "price": 50.0
}

with app.test_client() as c:
    # login
    resp = c.post('/admin_login', json={"username": "admin", "password": "admin123"})
    print('login ->', resp.status_code, resp.get_json())

    # first insert
    resp = c.post('/admin', json=sample)
    print('first insert ->', resp.status_code, resp.get_json())

    # second insert with changed status to simulate duplicate
    sample['parcelStatus'] = 'Delivered'
    resp = c.post('/admin', json=sample)
    print('second insert (should update) ->', resp.status_code, resp.get_json())

    # fetch parcel
    resp = c.get('/getparcel/DUPTEST123')
    print('getparcel ->', resp.status_code, resp.get_json())
