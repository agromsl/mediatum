"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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

import core.users as users
import core.tree as tree

from utils.log import logException
from web.edit.edit_common import showdir, getImportDir
from schema.bibtex import importBibTeX, MissingMapping


def getInformation():
    return {"version":"1.0", "system":1}
    
def getContent(req, ids):   
    if req.params.get("upload")=="uploadfile":
        # try to import file
        return import_new(req)
    return req.getTAL("web/edit/modules/imports.html",{"error":req.params.get("error")},macro="upload_form") + showdir(req, tree.getNode(ids[0]))

def import_new(req):
    user = users.getUserFromRequest(req)
    importdir= getImportDir(user)
    del req.params["upload"]
    
    if "file" in req.params.keys():
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                importBibTeX(file.tempname, importdir)
                req.request["Location"] = req.makeLink("content", {"id":importdir.id})
            except MissingMapping,e:
                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":str(e)})
            except:
                logException("error during upload")
                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"PostprocessingError"})
                req.params["error"] = "file_processingerror"
            return getContent(req, [importdir.id])
    
    # error while import, no file given
    req.params["error"] = "no_file_transferred"
    return getContent(req, [importdir.id])
