"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import core.tree as tree
import os
import logging
import core.acl as acl
import core.users as users

import json

from utils.utils import getMimeType, splitpath, dec_entry_log
from utils.fileutils import importFile

from core.translation import lang
from core.translation import t as translation_t
from core.transition import httpstatus

logger = logging.getLogger('usertracing')
logger_e = logging.getLogger('editor')


# to do: limit number of logos

@dec_entry_log
def getContent(req, ids):
    user = users.getUserFromRequest(req)
    node = tree.getNode(ids[0])
    access = acl.AccessData(req)

    if "logo" in users.getHideMenusForUser(user) or not access.hasWriteAccess(node):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    # delete logo file
    if "action" in req.params and req.params.get('action') == "delete":
        file = req.params.get('file').split("/")[-1]
        for f in node.getFiles():
            if f.retrieveFile().endswith(file):
                node.removeFile(f)
                req.write('ok')
                return None
        req.write('not found')
        return None

    # add logo file
    if "addfile" in req.params.keys():
        file = req.params.get("updatefile")
        if file:
            mimetype = "application/x-download"
            type = "file"
            mimetype, type = getMimeType(file.filename.lower())

            if mimetype not in ("image/jpeg", "image/gif", "image/png"):
                # wrong file type (jpeg, jpg, gif, png)
                req.setStatus(httpstatus.HTTP_INTERNAL_SERVER_ERROR)
                return req.getTAL("web/edit/modules/logo.html", {}, macro="filetype_error")
            else:
                file = importFile(file.filename, file.tempname)
                node.addFile(file)

    # save logo
    if "logo_save" in req.params.keys():
        # save url
        if req.params.get("logo_link", "") == "":
            node.removeAttribute("url")
        else:
            node.set('url', req.params.get("logo_link"))

        # save filename
        if req.params.get('logo') == "/img/empty.gif":
            # remove logo from current node
            node.set("system.logo", "")
            msg = "%s cleared logo for node %r (%r, %r)" % (user.getName(), node.id, node.name, node.type)
            logger.info(msg)
            logger_e.info(msg)
        else:
            node.set("system.logo", req.params.get("logo").split("/")[-1])
            msg = "%s set logo for node %r (%r, %r) to %r" % (user.getName(), node.id, node.name, node.type, node.get("system.logo"))
            logger.info(msg)
            logger_e.info(msg)

    logofiles = []
    for f in node.getFiles():
        if f.getType() == "image":
            logofiles.append(splitpath(f.retrieveFile()))
    
    v = {
        "id": req.params.get("id", "0"),
        "tab": req.params.get("tab", ""),
        "node": node,
        "logofiles": logofiles,
        "logo": node.getLogoPath(),
        "language": lang(req),
        "t": translation_t
    }
         
    return req.getTAL("web/edit/modules/logo.html", v, macro="edit_logo")
