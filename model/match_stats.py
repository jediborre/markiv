from .db import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Text, ForeignKey


class MatchStats(Base):
    __tablename__ = 'Matches.stats'

    id = Column(Integer, primary_key=True)
    Matches = Column(Integer, ForeignKey('Matches.id'))
    fecha = Column(Text)
    eventos_html = Column(Text)
    home_scored = Column(Text)
    home_scoredGame = Column(Text)
    home_conceded = Column(Text)
    home_concededGame = Column(Text)
    away_scored = Column(Text)
    away_conceded = Column(Text)
    away_scoredGame = Column(Text)
    away_concededGame = Column(Text)
    # home_HT = Column(Text)
    # away_HT = Column(Text)
    # home_shoot_on_target_HT = Column(Text)
    # away_shoot_on_target_HT = Column(Text)
    # home_shoot_off_target_HT = Column(Text)
    # away_shoot_off_target_HT = Column(Text)
    # home_attacks_HT = Column(Text)
    # away_attacks_HT = Column(Text)
    # home_shoot_on_target_FT = Column(Text)
    # away_shoot_on_target_FT = Column(Text)
    # home_shoot_off_target_FT = Column(Text)
    # away_shoot_off_target_FT = Column(Text)
    # home_attacks_FT = Column(Text)
    # away_attacks_FT = Column(Text)
    # home_corners_HT = Column(Text)
    # away_corners_HT = Column(Text)

    match = relationship("Match", back_populates="stats")
    eventos = relationship("MatchStatsEventos", uselist=True, back_populates="stats") # noqa
    home_matches = relationship("MatchStatsHomeMatches", uselist=True) # noqa
    away_matches = relationship("MatchStatsAwayMatches", uselist=True) # noqa