# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import datetime
import logging
import time

import pyaml
from ipaddr import IPv4Network, IPv4Address
import psycopg2.extensions
from psycopg2.extensions import adapt, AsIs
import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy import Column, ForeignKey, event, Integer, DateTime, func as sqlfunc
from sqlalchemy.orm import relationship, backref, Query, Mapper
from sqlalchemy.ext.declarative import declared_attr

from core.transition import request


logg = logging.getLogger(__name__)


C = Column
FK = ForeignKey
rel = relationship
bref = backref

DB_SCHEMA_NAME = "mediatum"

# warn when queries take longer than `SLOW_QUERY_SECONDS`
SLOW_QUERY_SECONDS = 0.2


def dynamic_rel(*args, **kwargs):
        return relationship(*args, lazy="dynamic", **kwargs)


class TimeStamp(object):

    """a simple timestamp mixin"""

    @declared_attr
    def created_at(cls):
        return C(DateTime, default=sqla.func.now())


def integer_pk(**kwargs):
    return C(Integer, primary_key=True, **kwargs)


def integer_fk(*args, **kwargs):
    if len(args) == 2:
        return C(args[0], ForeignKey(args[1]), **kwargs)
    elif len(args) == 1:
        return C(ForeignKey(args[0]), **kwargs)
    else:
        raise ValueError("at least one argument must be specified (type)!")


db_metadata = sqla.MetaData(schema=DB_SCHEMA_NAME)
func = getattr(sqla.func, DB_SCHEMA_NAME)
DeclarativeBase = declarative_base(metadata=db_metadata)

# some pretty printing for SQLAlchemy objects ;)


def to_dict(self):
    return dict((str(col.name), getattr(self, col.name))
                for col in self.__table__.columns)


def to_yaml(self):
    return pyaml.dump(self.to_dict())


DeclarativeBase.to_dict = to_dict
DeclarativeBase.to_yaml = to_yaml


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement,
                          parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    conn.info.setdefault('current_query', []).append(statement)


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement,
                         parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    # total in seconds
    if total > SLOW_QUERY_SECONDS:
        if hasattr(conn.connection.connection, "history"):
            statement = conn.connection.connection.history.last_statement
        else:
            statement = conn.info['current_query'].pop(-1)
        logg.warn("slow query %.1fms:\n%s", total * 1000, statement)


# IP types handling

def adapt_ipv4network(ipnet):
    val = adapt(str(ipnet)).getquoted()
    return AsIs(val + "::cidr")

def adapt_ipv4address(ipnet):
    val = adapt(str(ipnet)).getquoted()
    return AsIs(val + "::inet")

psycopg2.extensions.register_adapter(IPv4Network, adapt_ipv4network)
psycopg2.extensions.register_adapter(IPv4Address, adapt_ipv4address)
psycopg2.extensions.register_type(psycopg2.extensions.new_array_type((651,), "CIDR[]", psycopg2.STRING))


# Date types handling

class InfDateAdapter(object):

    """Map datetime.date.min/max values to infinity in Postgres
    Taken from: http://initd.org/psycopg/docs/usage.html"""

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def getquoted(self):
        if self.wrapped == datetime.date.max:
            return b"'infinity'::date"
        elif self.wrapped == datetime.date.min:
            return b"'-infinity'::date"
        else:
            return psycopg2.extensions.DateFromPy(self.wrapped).getquoted()

psycopg2.extensions.register_adapter(datetime.date, InfDateAdapter)


class MtQuery(Query):

    def _find_nodeclass(self):
        from core import Node
        """Returns the query's underlying model classes."""
        return [
            d['entity']
            for d in self.column_descriptions
            if issubclass(d['entity'], Node)
        ]

    def filter_read_access(self, user=None, ip=None, req=None):
        
        if user is None and ip is None:
            if req is None:
                req = request
                
            from core.users import user_from_session
            user = user_from_session(req.session)
            ip = IPv4Address(req.remote_addr)
            
        # admin sees everything ;)
        if user.is_admin:
            return self
        
        nodeclass = self._find_nodeclass()
        if not nodeclass:
            return self
        else:
            nodeclass = nodeclass[0]
            
        read_access = func.has_read_access_to_node(nodeclass.id, user.group_ids, ip, sqlfunc.current_date())
        return self.filter(read_access)