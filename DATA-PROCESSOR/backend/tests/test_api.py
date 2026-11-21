# test the FastAPI endpoints with TestClient (no real server needed)
import pytest
from fastapi.testclient import TestClient

from data_agent import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main.config, 'UPLOAD_DIR', tmp_path)
    sent = []

    async def fake_send(event):  # stands in for sending the event to Inngest
        sent.append(event)
        return ['event-123']

    monkeypatch.setattr(main.inngest_client, 'send', fake_send)
    c = TestClient(main.app)
    c.sent = sent
    return c


def test_health(client):
    assert client.get('/api/health').json()['ok'] is True


def test_upload_without_data_file_rejected(client):
    res = client.post('/api/jobs', files=[('files', ('guide.pdf', b'%PDF', 'application/pdf'))])
    assert res.status_code == 400 and 'data file' in res.json()['detail']


def test_upload_unknown_file_type_rejected(client):
    res = client.post('/api/jobs', files=[('files', ('virus.exe', b'x', 'application/octet-stream'))])
    assert res.status_code == 400


def test_valid_upload_sends_event(client, tmp_path):
    files = [
        ('files', ('guide.pdf', b'%PDF', 'application/pdf')),
        ('files', ('../../data.xlsx', b'xlsx', 'application/octet-stream')),  # "naughty" file name
    ]
    res = client.post('/api/jobs', files=files)
    assert res.status_code == 200 and res.json()['event_id'] == 'event-123'

    data = client.sent[0].data
    assert data['data_path'].startswith(str(tmp_path))  # stays inside the upload folder
    assert data['data_path'].endswith('data.xlsx')
