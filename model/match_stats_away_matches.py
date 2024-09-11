from .db import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Text, ForeignKey


class MatchStatsAwayMatches(Base):
    __tablename__ = 'Matches.stats.away_matches'

    id = Column(Integer, primary_key=True)
    match_stats_id = Column("Matches.stats", Integer, ForeignKey('Matches.stats.id')) # noqa
    a_league = Column(Text)
    a_match_date = Column(Text)
    a_home_name = Column(Text)
    a_away_name = Column(Text)
    a_result = Column(Text)
    a_h_HT = Column(Text)
    a_a_HT = Column(Text)
    a_h_FT = Column(Text)
    a_a_FT = Column(Text)

    match_stats = relationship("MatchStats", back_populates="away_matches")
