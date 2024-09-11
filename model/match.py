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
    minuto = Column(Text)
    home_FT = Column(Text)
    away_FT = Column(Text)
    home = Column(Text)
    away = Column(Text)
    home_pos = Column(Text)
    away_pos = Column(Text)
    home_Amarillas = Column(Text)
    away_Amarillas = Column(Text)
    home_Rojas = Column(Text)
    away_Rojas = Column(Text)
    # home_corner_HT = Column(Text)
    # away_corner_HT = Column(Text)
    # home_corner_FT = Column(Text)
    # away_corner_FT = Column(Text)
    # home_dangerous_FT = Column(Text)
    # away_dangerous_FT = Column(Text)
    # home_dangerouse_HT = Column(Text)
    # away_dangerouse_HT = Column(Text)
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
