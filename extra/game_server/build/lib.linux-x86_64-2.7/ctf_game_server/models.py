from sqlalchemy import Column, Integer, String, SmallInteger, VARCHAR, TIMESTAMP
from ctf_game_server.database import Base
import json

class Level(Base):
    __tablename__ = 'levels'
    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(SmallInteger)
    type = Column(VARCHAR(4))
    title = Column(String)
    description = Column(String)
    entity_id = Column(Integer)
    category_id = Column(Integer)
    points = Column(Integer)
    bonus = Column(Integer)
    bonus_dec = Column(Integer)
    bonus_fix = Column(Integer)
    flag = Column(String)
    hint = Column(String)
    penalty = Column(Integer)
    created_ts = Column(TIMESTAMP)

    def __init__(self, title, description, points, flag, hint, penalty, entity_id, category_id, id=None, active=None, type=None, bonus=None, bonus_dec=None, bonus_fix=None, created_ts=None):
        self.title = title
        self.description = description
        self.entity_id = entity_id
        self.category_id = category_id
        self.points = points
        self.flag = flag
        self.hint = hint
        self.penalty = penalty

    def __repr__(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}