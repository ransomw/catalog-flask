from pdb import set_trace as st

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import Text

import sqlalchemy.sql.functions as func

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.orm import validates

from sqlalchemy import create_engine

# despite underscore, this is a documented instance
from flask import _app_ctx_stack
from flask import current_app

from capp import app

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False, unique=True)
    password = Column(String(500), nullable=True)


class Category(Base):
    __tablename__ = 'category'
    id = Column(
        Integer, primary_key=True)
    # must be unique due to url scheme
    name = Column(
        String(80), nullable=False, unique=True)
    items = relationship("Item", cascade="delete")

    def __str__(self):
        return self.name

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
        }


class Item(Base):
    __tablename__ = 'item'
    id = Column(
        Integer, primary_key=True)
    # must be unique due to url scheme for edit/delete
    title = Column(String(80), unique=True)
    description = Column(Text())
    category_id = Column(
        Integer, ForeignKey('category.id'), nullable=False)
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    last_update = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now())

    @validates('description')
    def validate_description(self, key, description):
        if description == '':
            raise ValueError(
                "may not have empty description")
        return description

    @property
    def serialize(self):
        return {
            'cat_id': self.category_id,
            'description': self.description,
            'id': self.id,
            'title': self.title,
        }


def _connect_db():
    """ return a new sqlalchemy session """
    engine = create_engine(
        'sqlite:///' + current_app.config['DATABASE'])
    Base.metadata.create_all(engine)
    # todo: db disconnect or transaction to be roll back?
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    return DBSession()


def get_db():
    top = _app_ctx_stack.top
    if not hasattr(top, 'db_session'):
        top.db_session = _connect_db()
    return top.db_session


@app.teardown_appcontext
def close_database(exception):
    get_db().close()
