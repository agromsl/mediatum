# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from sqlalchemy.ext import compiler
from sqlalchemy.sql import table
from sqlalchemy.sql.ddl import DDLElement


class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable

class DropView(DDLElement):
    def __init__(self, name):
        self.name = name

@compiler.compiles(CreateView)
def visiit_create_view(element, compiler, **kw):
    return "CREATE VIEW %s AS %s" % (element.name, compiler.sql_compiler.process(element.selectable))


@compiler.compiles(DropView)
def visit_drop_view(element, compiler, **kw):
    return "DROP VIEW %s" % (element.name)


def view(name, metadata, selectable):
    t = table(name)

    for c in selectable.c:
        c._make_proxy(t)

    CreateView(name, selectable).execute_at('after-create', metadata)
    DropView(name).execute_at('before-drop', metadata)
    return t