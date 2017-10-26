import pytest
import requests
import os
import json

MATRIX_USERNAME = os.environ.get("MATRIX_USERNAME")
MATRIX_PASSWORD = os.environ.get("MATRIX_PASSWORD")

from room_stats.utils import get_all_rooms_to_file, MatrixClient

@pytest.fixture(scope="module")
def client():
    client = MatrixClient(
        "https://matrix.org/_matrix/client/r0",
        MATRIX_USERNAME, MATRIX_PASSWORD
    )
    client.login()
    return client


@pytest.mark.slow
def test_login(client):
    assert client.token is not None

# @pytest.mark.slow
# def test_public_rooms(client):
#     rooms = client.get_public_rooms(limit=20)
#     assert len(rooms) == 20

@pytest.mark.slow
def test_export_rooms_to_file(client, tmpdir):
    f = tmpdir.join("matrix-rooms.json")
    get_all_rooms_to_file(f, limit=20)
    content = f.read()
    assert len(content) > 0
    rooms = json.loads(content)
    assert len(rooms) == 20
    room = rooms[0]
    assert 'room_id' in room
