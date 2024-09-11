from .db import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Text, ForeignKey


class MatchStatsHomeMatches(Base):
    __tablename__ = 'Matches.stats.home_matches'

    id = Column(Integer, primary_key=True)
    match_stats_id = Column("Matches.stats", Integer, ForeignKey('Matches.stats.id')) # noqa
    h_league = Column(Text)
    h_match_date = Column(Text)
    h_home_name = Column(Text)
    h_away_name = Column(Text)
    h_result = Column(Text)
    h_score_h_HT = Column(Text)
    h_score_a_HT = Column(Text)
    h_score_h_FT = Column(Text)
    h_score_a_FT = Column(Text)

    match_stats = relationship("MatchStats", back_populates="home_matches")
