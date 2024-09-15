from .db import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Text, ForeignKey


class MatchStatsFaceMatches(Base):
    __tablename__ = 'Matches.stats.face_matches'

    id = Column(Integer, primary_key=True)
    match_stats_id = Column("Matches.stats", Integer, ForeignKey('Matches.stats.id')) # noqa
    league = Column(Text)
    date = Column(Text)
    home = Column(Text)
    away = Column(Text)
    home_FT = Column(Text)
    away_FT = Column(Text)

    match_stats = relationship("MatchStats", back_populates="face_matches")
