from sqlalchemy import Column, Integer, String, SmallInteger, VARCHAR, TIMESTAMP
from database import Base
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

    def __init__(self, title, description, points, flag, hint, penalty, entity_id, category_id, id=None, active=0, type=0, bonus=0, bonus_dec=0, bonus_fix=0, created_ts=None):
        self.title = title
        self.description = description
        self.entity_id = entity_id
        self.category_id = category_id
        self.points = points
        self.flag = flag
        self.hint = hint
        self.penalty = penalty
        self.active = active
        self.type = type
        self.bonus = bonus
        self.bonus_dec = bonus_dec
        self.bonus_fix = bonus_fix
        self.created_ts = created_ts
        self.id = id

    def __repr__(self):
        return {c.name: str(getattr(self, c.name)) for c in self.__table__.columns}

class Session(Base):
    __tablename__= 'sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cookie = Column(String)
    data = Column(String)
    team_id = Column(Integer)
    created_ts = Column(TIMESTAMP)
    last_access_ts = Column(TIMESTAMP)
    last_page_access = Column(String)

    def __init__(self, id, cookie, data, team_id, created_ts, last_accessed_ts, last_page_access):
        self.id = id
        self.cookie = cookie
        self.data = data
        self.team_id = team_id
        self.created_ts = created_ts
        self.last_access_ts = last_accessed_ts
        self.last_page_access = last_page_access

    def __repr__(self):
        return {c.name: str(getattr(self, c.name)) for c in self.__table__.columns}