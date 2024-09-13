import logging
from sqlalchemy.orm import relationship
from sqlalchemy.exc import OperationalError
from sqlalchemy import Column, Integer, Text
from .db import Base, retry_on_timeout


class Match(Base):
    __tablename__ = 'Matches'

    id = Column(Integer, primary_key=True)
    league = Column(Text)
    pais = Column(Text)
    time = Column(Text)
    home = Column(Text)
    away = Column(Text)
    home_pos = Column(Text)
    away_pos = Column(Text)
    url = Column(Text)

    stats = relationship("MatchStats", uselist=False, back_populates="match")

    @classmethod
    @retry_on_timeout(max_retries=3, delay=5)
    def get_all(cls, db=None):
        if db:
            try:
                # return [db.query(cls).first()]
                return db.query(cls).all()
            except OperationalError as err:
                logging.error(f"Error adding match: {err}")
                db.rollback()
                raise
