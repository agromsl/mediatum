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
import lib.lza.lza as l
import core.acl as acl
import core.users as users

from schema.schema import getMetaType
from core.translation import lang, t
from utils.utils import dec_entry_log
from core.transition import httpstatus


@dec_entry_log
def getContent(req, ids):
    user = users.getUserFromRequest(req)
    if "lza" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")
    
    v = {}
    v['error'] = ""

    nodes = []
    for id in ids:
        node = tree.getNode(id)

        access = acl.AccessData(req)
        if not access.hasWriteAccess(node):
            req.setStatus(httpstatus.HTTP_FORBIDDEN)
            return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        nodes.append(node)
        if "createlza" in req.params:           
            # remove old file if existing
            for f in node.getFiles():
                if f.getType()=="lza":
                    node.removeFile(f)
            # create new file     
            for f in node.getFiles():
                if f.getType() in ("original", "document"):
                    try:
                        archive = l.LZA(f.retrieveFile())
                        schema = node.getSchema()

                        # test for lza export mask
                        if (getMetaType(schema).getMask("lza")):
                            m = getMetaType(schema).getMask("lza")
                            meta = l.LZAMetadata(m.getViewHTML([node], 8))
                        else:
                            # generate error message
                            meta = l.LZAMetadata("""
        <?xpacket begin="\xef\xbb\xbf" id="mediatum_metadata"?>
                <lza:data> 
                    <lza:error>-definition missing-</lza:error>
                </lza:data><?xpacket end="w"?>
                                """)
                        archive.writeMediatumData(meta)
                        node.addFile(tree.

                        FileNode(archive.buildLZAName(),"lza", f.getMimeType()))
                    
                    except l.FiletypeNotSupported:
                        v['error'] = "edit_lza_wrongfiletype"
                    

        elif "removelza" in req.params:
            for f in node.getFiles():
                if f.getType()=="lza":
                    node.removeFile(f)

    v['id'] = req.params.get("id","0")
    v['tab'] = req.params.get("tab", "")
    v['ids'] = ids
    v['nodes'] = nodes
    v['t'] = t
    v['language'] = lang(req)

    meta = {}
    for id in ids:
        node = tree.getNode(id)
        for f in node.getFiles():
            if f.getType()=="lza":
                try:
                    archive = l.LZA(f.retrieveFile(), f.getMimeType())
                    meta[id] = archive.getMediatumData()
                except IOError:
                    v['error'] = "edit_lza_ioerror"

    v['meta'] = meta
    return req.getTAL("web/edit/modules/lza.html", v, macro="edit_lza")
