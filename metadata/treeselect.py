"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <arne.seifert@tum.de>

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
from mediatumtal import tal
from core.transition import httpstatus
import core.tree as tree
from utils.utils import esc
from core.metatype import Metatype


class m_treeselect(Metatype):

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        return tal.getTAL("metadata/treeselect.html",{"lock": lock,
                                                      "value": value,
                                                      "width": width,
                                                      "name": field.getName(),
                                                      "field": field,
                                                      "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/treeselect.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormatedValue_(self, field, node, language=None, html=1, template_from_caller=None, mask=None):
        value = node.get(field.getName())
        if html:
            value = esc(value)
        return (field.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        try:
            return value.replace("; ", ";")
        except:
            return value

    def getName(self):
        return "fieldtype_treeselect"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    # method for popup methods of type treeselect
    def getPopup(self, req):
        req.writeTAL("metadata/treeselect.html", {"basedir": tree.getRoot('collections'),
                                                  "name": req.params.get("name", ''), "value": req.params.get("value")}, macro="popup")
        return httpstatus.HTTP_OK

    # method for additional keys of type treeselect
    def getLabels(self):
        return m_treeselect.labels

    labels = {"de":
              [
                  ("treeselect_popup_title", "Knotenauswahl"),
                  ("fieldtype_treeselect", "Knotenauswahlfeld"),
                  ("fieldtype_text_desc", "Feld zur Knotenauswahl"),
                  ("treeselect_titlepopupbutton", "Knotenauswahl \xc3\xb6ffnen"),
                  ("treeselect_done", "\xC3\x9Cbernehmen"),
              ],
              "en":
              [
                  ("treeselect_popup_title", "Node selection"),
                  ("fieldtype_treeselect", "node selection field"),
                  ("fieldtype_text_desc", "field for node selection"),
                  ("treeselect_titlepopupbutton", "open node selection"),
                  ("treeselect_done", "Done"),
              ]
              }
