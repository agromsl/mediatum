# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

mediaTUM management script.

manage.py <action>

action is one of:

* create: create database schema and structure
* drop: drop database schema with all data
* recreate: run drop and create
* init: load initial database values needed for an empty mediaTUM
* truncate: deletes all data, but keeps the db structure

"""
from __future__ import division, absolute_import, print_function

from functools import partial
import logging
import sys
sys.path.append(".")

from core.init import basic_init
from core.database.postgres import db_metadata
import configargparse
from collections import OrderedDict

basic_init(root_loglevel=logging.WARN)

logg = logging.getLogger("manage.py")
logg.setLevel(logging.INFO)
logging.getLogger("database").setLevel(logging.INFO)

from core.database.init import init_database_values
from core import db


def drop_schema(s):
    s.execute("DROP SCHEMA mediatum CASCADE")
    s.commit()
    logg.info("dropped database structure")


def create_schema(s):
    logg.info("creating DB schema...")

    s.execute("CREATE SCHEMA mediatum")
    s.commit()
    try:
        db.create_all()
        s.commit()
        logg.info("commited database structure")
    except:
        # I tried to use a transaction to enclose everything, but sqlalchemy (?) fails when the schema is created within the transaction
        # solution: just drop the schema it if something fails after schema creation
        s.execute("DROP SCHEMA mediatum CASCADE")
        raise


def recreate(s):
    drop_schema(s)
    create_schema(s)


def reverse_sorted_tables():
    return reversed(db_metadata.sorted_tables)


def truncate_tables(s, table_fullnames=None):

    if not table_fullnames:
        table_fullnames = [t.fullname for t in reverse_sorted_tables()]

    s.execute('TRUNCATE {} RESTART IDENTITY;'.format(
        ','.join(table_fullnames)))

    logg.info("truncated %s", table_fullnames)


def run_maint_command_for_tables(command, s, table_fullnames=None):
    """Runs a maintenance postgres command on tables that must be run outside a transaction.
    Uses all tables if `table_fullnames` is None.
    :param s: session to use
    :param table_fullnames: sequence of schema-qualified table names or None.
    """
    # we can't run inside an (implicit) transaction, so we have to use autocommit mode
    conn = s.connection().execution_options(isolation_level="AUTOCOMMIT")

    if not table_fullnames:
        table_fullnames = [t.fullname for t in reverse_sorted_tables()]

    for fullname in table_fullnames:
        cmd = command + " " + fullname
        logg.info(cmd)
        conn.execute(cmd)

    logg.info("completed %s", command)


vacuum_tables = partial(run_maint_command_for_tables, "VACUUM")
vacuum_analyze_tables = partial(run_maint_command_for_tables, "VACUUM ANALYZE")
reindex_tables = partial(run_maint_command_for_tables, "REINDEX TABLE")


s = db.session

actions = OrderedDict([
    ("create", create_schema),
    ("drop", drop_schema),
    ("recreate", recreate),
    ("init", init_database_values),
    ("truncate", truncate_tables),
    ("vacuum", vacuum_tables),
    ("analyze", vacuum_analyze_tables),
    ("reindex", reindex_tables)
])

if __name__ == "__main__":
    parser = configargparse.ArgumentParser("mediaTUM manage.py")
    parser.add_argument("action", nargs="*", choices=actions.keys())
    args = parser.parse_args()

    print()
    print("running actions: " + ", ".join(args.action))
    print("-" * 80)

    for action in args.action:
        actions[action](s)
        db.session.commit()