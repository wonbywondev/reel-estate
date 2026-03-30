import os
import pytest
from db.database import Database
from db.models import Room


@pytest.fixture
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    db.init()
    yield db
    db.close()


def test_insert_and_get_room(db):
    room = Room(
        address="서울특별시 강남구 테헤란로 123",
        floor=3,
        size_pyeong=10.0,
        deposit=3000,
        monthly_rent=50,
        options=["에어컨", "세탁기"],
        year_built=2010,
    )
    room_id = db.insert_room(room)
    fetched = db.get_room(room_id)
    assert fetched.address == room.address
    assert fetched.deposit == 3000
    assert fetched.options == ["에어컨", "세탁기"]
    assert fetched.year_built == 2010


def test_list_rooms(db):
    room = Room(address="서울 강남구 역삼동 1번지", floor=1, size_pyeong=8.0,
                deposit=1000, monthly_rent=40, options=[], year_built=2005)
    db.insert_room(room)
    rooms = db.list_rooms()
    assert len(rooms) == 1
    assert rooms[0].address == "서울 강남구 역삼동 1번지"


def test_update_video_path(db):
    room = Room(address="서울 마포구 합정동 1번지", floor=2, size_pyeong=9.0,
                deposit=500, monthly_rent=60, options=[], year_built=2015)
    room_id = db.insert_room(room)
    db.update_video_path(room_id, "/output/test.mp4")
    fetched = db.get_room(room_id)
    assert fetched.video_path == "/output/test.mp4"
