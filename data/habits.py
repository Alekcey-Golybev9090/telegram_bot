import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase


class Habit(SqlAlchemyBase):
    __tablename__ = 'habits'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    chat_id = sqlalchemy.Column(sqlalchemy.Integer)
    start_datetime = sqlalchemy.Column(sqlalchemy.DateTime)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    address = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    delta_time = sqlalchemy.Column(sqlalchemy.TIME, nullable=True, default=datetime.timedelta(seconds=0))
