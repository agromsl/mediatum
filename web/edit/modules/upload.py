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
import core.athana as athana
import os
import core.users as users
import core.tree as tree
import re
import utils.date
from utils.log import logException
import core.config as config
import zipfile, PIL.Image
import random 
import logging
from core.datatypes import loadAllDatatypes
from web.edit.edit_common import showdir, getUploadDir
import utils.date as date
from utils.utils import join_paths, OperationException, EncryptionException, formatException
from utils.fileutils import importFile

from core.tree import Node
from core.acl import AccessData
from schema.schema import loadTypesFromDB

from core.translation import translate, lang, t


def elemInList(list, name):
    for item in list:
        if item.getName()==name:
            return True
    return False

def getContent(req, ids):
    error = req.params.get("error")
    if "file" in req.params or "datatype" in req.params: # create node with/without file
        try:
            upload_new(req)
        except OperationException, e:
            error = e.value


    user = users.getUserFromRequest(req)
    uploaddir = tree.getNode(ids[0])

    schemes = AccessData(req).filter(loadTypesFromDB())
    _schemes = []
    for scheme in schemes:
        if scheme.isActive():
            _schemes.append(scheme)
    schemes = _schemes

    # find out which schema allows which datatype, and hence,
    # which overall data types we should display
    dtypes = []
    datatypes = loadAllDatatypes()
    for scheme in schemes:
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes:
                for t in datatypes:
                    if t.getName()==dtype and not elemInList(dtypes, t.getName()):
                        dtypes.append(t)
                 
    dtypes.sort(lambda x, y: cmp(translate(x.getLongName(), request=req).lower(), translate(y.getLongName(), request=req).lower()))

    objtype = ""
    if len(dtypes)==1:
        objtype = dtypes[0]
    else:
        for t in datatypes:
            if t.getName()==req.params.get("objtype",""):
                objtype = t
                break

    # filter schemes for special datatypes
    if req.params.get("objtype","")!="":
        _schemes = []
        for scheme in schemes:
            if req.params.get("objtype","") in scheme.getDatatypes():
                _schemes.append(scheme)
        schemes = _schemes
        schemes.sort(lambda x, y: cmp(translate(x.getLongName(), request=req).lower(),translate(y.getLongName(), request=req).lower()))

    return req.getTAL("web/edit/modules/upload.html",{"id":req.params.get("id"),"datatypes":dtypes, "schemes":schemes, "objtype":objtype, "error":error},macro="upload_form") + showdir(req, uploaddir)


# differs from os.path.split in that it handles windows as well as unix filenames
FNAMESPLIT=re.compile(r'(([^/\\]*[/\\])*)([^/\\]*)')
def mybasename(filename):
    g = FNAMESPLIT.match(filename)
    if g:
        return g.group(3)
    else:
        return filename

def importFileIntoNode(user,realname,tempname,datatype, workflow=0):
    logging.getLogger('usertracing').info(user.name + " upload "+realname+" ("+tempname+")")

    if realname.lower().endswith(".zip"):
        z = zipfile.ZipFile(tempname)
        for f in z.namelist():
            name = mybasename(f)
            if name.startswith("._"):
                # ignore Mac OS X junk
                continue
            rnd = str(random.random())[2:]
            ext = os.path.splitext(name)[1]
            newfilename = join_paths(config.get("paths.tempdir"), rnd+ext)
            fi = open(newfilename, "wb")
            fi.write(z.read(f))
            fi.close()
            importFileIntoNode(user, name, newfilename, datatype)
            os.unlink(newfilename)
        return
    if realname!="":
        n = tree.Node(name=mybasename(realname), type=datatype)
        print n
        file = importFile(realname,tempname)
        n.addFile(file)
    else:
        # no filename given
        n = tree.Node(name="", type=datatype)

    # service flags
    n.set("creator", user.getName())
    n.set("creationtime", date.format_date())
    if hasattr(n,"event_files_changed"):
        try:
            n.event_files_changed()
            uploaddir = getUploadDir(user)
            uploaddir.addChild(n)

        except OperationException, e:
            for file in n.getFiles():
                if os.path.exists(file.retrieveFile()):
                    os.remove(file.retrieveFile())
            raise OperationException(e.value)

def upload_new(req):
    user = users.getUserFromRequest(req)
    datatype = req.params.get("datatype", "image")
    uploaddir = getUploadDir(user)

    workflow = "" #int(req.params["workflow"])
    
    if "file" in req.params.keys():
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                importFileIntoNode(user, file.filename, file.tempname, datatype, workflow)
                req.request["Location"] = req.makeLink("content", {"id":uploaddir.id})
            except OperationException, e:
                raise OperationException(e.value)
            #except:
            #    raise OperationException("error:unkonwn")
            return athana.HTTP_MOVED_TEMPORARILY;

    # upload without file
    importFileIntoNode(user, "", "", datatype, workflow)
    req.request["Location"] = req.makeLink("content", {"id":uploaddir.id})
    return athana.HTTP_MOVED_TEMPORARILY;