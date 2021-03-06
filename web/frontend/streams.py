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
import re
import os
import glob
import random
import zipfile
import time

import core.config as config
import core.athana as athana
import core.tree as tree
from core.archive import archivemanager
from core.acl import AccessData
from core.tree import getNode
import utils.utils
from utils.utils import get_filesize, join_paths, clean_path, getMimeType
from schema.schema import existMetaField


IMGNAME = re.compile("/?(attachment|doc|images|thumbs|thumb2|file|download|archive)/([^/]*)(/(.*))?$")


def splitpath(path):
    m = IMGNAME.match(path)
    if m is None:
        return path
    try:
        return m.group(2), m.group(4)
    except:
        return m.group(2), None


def send_image(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType() == "image":
            return req.sendFile(f.retrieveFile(), f.getMimeType())
    return 404


def send_image_watermark(req):
    try:
        result = splitpath(req.path)
        n = tree.getNode(result[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType() == "original_wm":
            return req.sendFile(f.retrieveFile(), getMimeType(f.retrieveFile()))
    return 404


def send_rawimage(req):
    access = AccessData(req)
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n, "data") and n.type != "directory":
        return 403
    for f in n.getFiles():
        if f.getType() == "original":
            return req.sendFile(f.retrieveFile(), f.getMimeType())
    return 404


def send_rawfile(req, n=None):
    access = AccessData(req)
    if not n:
        id, filename = splitpath(req.path)
        n = None
        try:
            n = tree.getNode(id)
        except tree.NoSuchNodeError:
            return 404

    if not access.hasAccess(n, "data") and n.getContentType() not in ["directory", "collections", "collection"]:
        return 403
    for f in n.getFiles():
        if f.getType() == "original":
            return req.sendFile(f.retrieveFile(n), f.getMimeType(n))
    return 404


def send_thumbnail(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType() == "thumb":
            if os.path.isfile(f.retrieveFile()):
                return req.sendFile(f.retrieveFile(), f.getMimeType())

    for p in athana.getFileStorePaths("/img/"):
        for test in [
                "default_thumb_%s_%s.*" %
                (n.getContentType(),
                 n.getSchema()),
                "default_thumb_%s.*" %
                (n.getSchema()),
                "default_thumb_%s.*" %
                (n.getContentType())]:
            fps = glob.glob(os.path.join(config.basedir, p[2:], test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)
    return req.sendFile(config.basedir + "/web/img/questionmark.png", "image/png", force=1)


def send_thumbnail2(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType().startswith("presentat"):
            if os.path.isfile(f.retrieveFile()):
                return req.sendFile(f.retrieveFile(), f.getMimeType())
    # fallback
    for f in n.getFiles():
        if f.getType() == "image":
            if os.path.isfile(f.retrieveFile()):
                return req.sendFile(f.retrieveFile(), f.getMimeType())

    # fallback2
    for p in athana.getFileStorePaths("/img/"):
        for test in [
                "default_thumb_%s_%s.*" %
                (n.getContentType(),
                 n.getSchema()),
                "default_thumb_%s.*" %
                (n.getSchema()),
                "default_thumb_%s.*" %
                (n.getContentType())]:
            #fps = glob.glob(os.path.join(config.basedir, theme.getImagePath(), "img", test))
            fps = glob.glob(os.path.join(config.basedir, p[2:], test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)
    return 404


def send_doc(req):
    access = AccessData(req)
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n, "data") and n.type != "directory":
        return 403
    for f in n.getFiles():
        if f.getType() in ["doc", "document"]:
            return req.sendFile(f.retrieveFile(), f.getMimeType())
    return 404


def send_file(req, download=0):
    access = AccessData(req)
    id, filename = splitpath(req.path)
    if id.endswith("_transfer.zip"):
        id = id[:-13]

    try:
        n = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n, "data") and n.type not in ["directory", "collections", "collection"]:
        return 403
    file = None

    if filename is None and n:
        # build zip-file and return it
        zipfilepath, files_written = build_transferzip(n)
        if files_written == 0:
            return 404
        send_result = req.sendFile(zipfilepath, "application/zip")
        if os.sep == '/':  # Unix?
            os.unlink(zipfilepath)  # unlinking files while still reading them only works on Unix/Linux
        return send_result

    # try full filename
    for f in n.getFiles():
        if f.getName() == filename:
            file = f
            break

    # try only extension
    if not file and n.get("archive_type") == "":
        file_ext = os.path.splitext(filename)[1]
        for f in n.getFiles():
            if os.path.splitext(f.getName())[1] == file_ext and f.getType() in ['doc', 'document', 'original', 'mp3']:
                file = f
                break

    if existMetaField(n.getSchema(), 'nodename'):
        display_file_name = '{}.{}'.format(os.path.splitext(os.path.basename(n.name))[0], os.path.splitext(filename)[-1].strip('.'))
    else:
        display_file_name = filename

    # try file from archivemanager
    if not file and n.get("archive_type") != "":
        am = archivemanager.getManager(n.get("archive_type"))
        req.reply_headers["Content-Disposition"] = 'attachment; filename="{}"'.format(display_file_name)
        return req.sendFile(am.getArchivedFileStream(n.get("archive_path")), "application/x-download")

    if not file:
        return 404

    req.reply_headers["Content-Disposition"] = 'attachment; filename="{}"'.format(display_file_name)
    return req.sendFile(file.retrieveFile(), f.getMimeType())


def send_file_as_download(req):
    return send_file(req, download=1)


def send_attachment(req):
    access = AccessData(req)
    id, filename = splitpath(req.path)
    try:
        node = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(node, "data") and n.type != "directory":
        return 403
    # filename is attachment.zip
    for file in node.getFiles():
        if file.getType() == "attachment":
            sendZipFile(req, file.retrieveFile())
            break


def sendBibFile(req, path):
    req.reply_headers['Content-Disposition'] = "attachment; filename=export.bib"
    req.sendFile(path, getMimeType(path))
    if os.sep == '/':  # Unix?
        os.unlink(path)  # unlinking files while still reading them only works on Unix/Linux


def sendZipFile(req, path):
    tempfile = join_paths(config.get("paths.tempdir"), str(random.random())) + ".zip"
    zip = zipfile.ZipFile(tempfile, "w")
    zip.debug = 3

    def r(p):
        if os.path.isdir(join_paths(path, p)):
            for file in os.listdir(join_paths(path, p)):
                r(join_paths(p, file))
        else:
            while len(p) > 0 and p[0] == "/":
                p = p[1:]
            try:
                zip.write(join_paths(path, p), p)
            except:
                pass
    r("/")
    zip.close()
    req.reply_headers['Content-Disposition'] = "attachment; filename=shoppingbag.zip"
    req.sendFile(tempfile, "application/zip")
    if os.sep == '/':  # Unix?
        os.unlink(tempfile)  # unlinking files while still reading them only works on Unix/Linux


#
# send single attachment file to user
#
def send_attfile(req):
    access = AccessData(req)
    f = req.path[9:].split('/')
    try:
        node = getNode(f[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(node, "data") and node.type != "directory":
        return 403
    if len([file for file in node.getFiles() if file._path in ["/".join(f[1:]), "/".join(f[1:-1])]]) == 0:  # check filepath
        return 403

    filename = clean_path("/".join(f[1:]))
    path = join_paths(config.get("paths.datadir"), filename)
    mime, type = getMimeType(filename)
    if(get_filesize(filename) > 16 * 1048576):
        req.reply_headers["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)

    return req.sendFile(path, mime)


def get_archived(req):
    print "send archived"
    id, filename = splitpath(req.path)
    node = tree.getNode(id)
    node.set("archive_state", "1")
    if not archivemanager:
        req.write("-no archive module loaded-")
        return

    archiveclass = ""
    for item in config.get("archive.class").split(";"):
        if item.endswith(node.get("archive_type")):
            archiveclass = item + ".py"
            break

    if archiveclass:  # start process from archive
        os.chdir(config.basedir)
        os.system("python %s %s" % (archiveclass, node.id))

    st = ""
    while True:  # test if process is still running
        attrs = tree.db.getAttributes(id)
        if "archive_state" in attrs.keys():
            st = attrs['archive_state']
        time.sleep(1)
        if st == "2":
            break

    for n in node.getAllChildren():
        tree.remove_from_nodecaches(n)
    req.write('done')


def get_root(req):
    filename = config.basedir + "/web/root" + req.path
    if os.path.isfile(filename):
        return req.sendFile(filename, getMimeType(filename)[0])
    else:
        return 404


def get_all_file_paths(basedir):
    res = []
    for dirpath, dirnames, filenames in os.walk(basedir):
        for fn in filenames:
            res.append(os.path.join(dirpath, fn))
    return res


def build_transferzip(node):
    nid = node.id
    zipfilepath = join_paths(config.get("paths.tempdir"), nid + "_transfer.zip")
    if os.path.exists(zipfilepath):
        zipfilepath = join_paths(config.get("paths.tempdir"), nid + "_" + str(random.random()) + "_transfer.zip")

    zip = zipfile.ZipFile(zipfilepath, "w", zipfile.ZIP_DEFLATED)
    files_written = 0

    for n in node.getAllChildren():
        if n.isActiveVersion():
            for fn in n.getFiles():
                if fn.getType() in ['doc', 'document', 'zip', 'attachment', 'other']:
                    fullpath = fn.retrieveFile()
                    if os.path.isfile(fullpath) and os.path.exists(fullpath):
                        dirname, filename = os.path.split(fullpath)
                        print "adding to zip: ", fullpath, "as", filename
                        zip.write(fullpath, filename)
                        files_written += 1
                    if os.path.isdir(fullpath):
                        for f in get_all_file_paths(fullpath):
                            newpath = f.replace(fullpath, "")
                            print "adding from ", fullpath, "to zip: ", f, "as", newpath
                            zip.write(f, newpath)
                            files_written += 1
    zip.close()

    return zipfilepath, files_written


def build_filelist(node):
    "build file list for generation of xmetadissplus xml"
    files_written = 0
    result_list = []

    for n in node.getAllChildren():
        if n.isActiveVersion():
            for fn in n.getFiles():
                if fn.getType() in ['doc', 'document', 'zip', 'attachment', 'other']:
                    fullpath = fn.retrieveFile()
                    if os.path.isfile(fullpath) and os.path.exists(fullpath):
                        dirname, filename = os.path.split(fullpath)
                        result_list.append([filename, fn.getSize()])
                        files_written += 1
                    if os.path.isdir(fullpath):
                        for f in get_all_file_paths(fullpath):
                            dirname, filename = os.path.split(f)
                            result_list.append([filename, utils.utils.get_filesize(f)])
                            files_written += 1

    return result_list


def get_transfer_url(n):
    "get transfer url for oai format xmetadissplus"
    filecount = len(build_filelist(n))
    if filecount < 2:
        transfer_filename = n.id + ".pdf"
        transferurl = "http://" + config.get("host.name") + "/doc/" + n.id + "/" + transfer_filename
    else:
        transfer_filename = n.id + "_transfer.zip"
        transferurl = "http://" + config.get("host.name") + "/file/" + transfer_filename
    return transferurl
