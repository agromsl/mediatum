# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import os.path
from pytest import fixture, yield_fixture
import migration.acl_migration
from migration.test.factories import AccessFactory
from migration.test.factories import ImportNodeFactory
from core.database.postgres.permission import AccessRule, AccessRuleset
from core.test.factories import DirectoryFactory, NodeFactory
from ipaddr import IPv4Network
from core.database.postgres.connector import read_and_prepare_sql


@fixture(scope="session", autouse=True)
def import_database():
    """Drop/create schema and load models"""
    from core import db
    db.session.execute("DROP SCHEMA IF EXISTS mediatum_import CASCADE")
    db.session.execute("CREATE SCHEMA mediatum_import")
    sql_dir = os.path.join(os.path.dirname(__file__), "..")
    db.session.execute(read_and_prepare_sql("acl_migration.sql", sql_dir=sql_dir))
    db.session.commit()
    from migration.import_datamodel import ImportBase
    ImportBase.metadata.bind = db.engine
    ImportBase.metadata.create_all()
    return db


@yield_fixture(autouse="True", scope="function")
def session():
    """Yields default session which is closed after the test.
    Inner actions are wrapped in a transaction that always rolls back.
    """
    from core import db
    s = db.session
    transaction = s.connection().begin()
    yield s
    transaction.rollback()
    s.close()


@fixture
def import_node_with_simple_access(session):
    node = NodeFactory(id=100)
    import_node = ImportNodeFactory(
        id=100,
        readaccess="{ group test_readers }",
        writeaccess="{ group test_writers }",
        dataaccess="{ group test_datausers }")
    return import_node


@fixture
def import_node_with_complex_access(session):
    node = NodeFactory(id=100)
    import_node = ImportNodeFactory(id=100,
                                    readaccess="{ NOT ( group test_readers OR group test_readers2 ) }")
    return import_node


@fixture
def import_node_with_ruleset(session):
    node = NodeFactory(id=100)
    session.flush()
    acl1 = AccessFactory(rule="NOT ( group test_readers OR group test_readers2 )", name="not_rule")
    import_node = ImportNodeFactory(id=100, readaccess="not_rule,{ user darfdas }")
    return import_node


@fixture
def users_and_groups_for_ruleset(session):
    from core import User, UserGroup
    users = [User(login_name="darfdas")]
    session.add_all(users)

    groups = [UserGroup(name="test_readers"), UserGroup(name="test_readers2")]
    session.add_all(groups)
    return users, groups


@fixture
def two_access_rules():
    rule1 = AccessRule(group_ids=[11, 12], invert_group=True)
    rule2 = AccessRule(group_ids=[13], subnets=[IPv4Network("127.0.0.1/32")])
    return rule1, rule2


@fixture
def two_access_rulesets():
    ruleset1 = AccessRuleset(name="Ruleset1")
    ruleset2 = AccessRuleset(name="Ruleset2")
    return ruleset1, ruleset2


@fixture
def some_numbered_nodes():
    return [DirectoryFactory(id=j) for j in range(1, 4)]