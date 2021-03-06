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
from . import image
import os
from core.tree import FileNode
import core.config as config
import glob


class Imagestream(image.Image):

    def getFiles(node):
        files = []
        if node.get('system.imagestream') == '':
            return files

        image_dir = config.get('paths.datadir') + node.get('system.imagestream')

        try:
            newest_image = max(glob.iglob(image_dir + '*.jpg'), key=os.path.getctime)
        except:
            print 'No images in %s' % (image_dir)
            return files

        files += [FileNode(newest_image, 'image', 'image/jpeg', node)]
        return files
