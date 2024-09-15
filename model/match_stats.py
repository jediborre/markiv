from .db import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Text, ForeignKey


class MatchStats(Base):
    __tablename__ = 'Matches.stats'

    id = Column(Integer, primary_key=True)
    Matches = Column(Integer, ForeignKey('Matches.id'))
    fecha = Column(Text)

    match = relationship("Match", back_populates="stats")
    home_matches = relationship("MatchStatsHomeMatches", uselist=True) # noqa
    away_matches = relationship("MatchStatsAwayMatches", uselist=True) # noqa
    face_matches = relationship("MatchStatsFaceMatches", uselist=True) # noqa