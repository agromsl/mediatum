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
from utils.utils import formatLongText, u
import core.tree as tree
from core.tree import getNode

from schema.schema import getMetaFieldTypeNames, getMetaFieldTypes, getMetadataType, VIEW_DATA_ONLY, VIEW_SUB_ELEMENT, VIEW_HIDE_EMPTY, VIEW_DATA_EXPORT, dateoption
from core.translation import lang, translate
from core.metatype import Metatype
from lib.iptc.IPTC import get_wanted_iptc_tags, cut_string


class m_field(Metatype):

    def getFormHTML(self, field, nodes, req, sub=False):
        """ create editor field (editarea)"""
        element = field.getField()
        ret = ''
        label = ''
        description = '<div id="div_description"></div>'
        unit = ''

        if not sub:
            label += '<div class="label">' + field.getLabel() + ':'
            if (int(field.getRequired()) > 0):
                label += ' <span class="required">*</span>'
            label += '</div>'
        else:
            if field.getLabel() != "":
                label += field.getLabel() + ': '
                if int(field.getRequired()) > 0:
                    label += '<span class="required">*</span> '

        if field.getDescription() != "":
            description = '<div id="div_description"><a href="#" onclick="openPopup(\'/popup_help?id=' + element.id + \
                '&maskid=' + field.id + '\', \'\', 400, 250)"><img src="/img/tooltip.png" border="0"/></a></div>'

        if not sub:
            if str(element.id) in req.params.get("errorlist", []):
                ret += '<div class="editorerror">'
            else:
                ret += '<div class="editorrow">'

        ret += label + description
        elementtype = element.get("type")

        val = nodes[0].get(element.getName())
        for node in nodes:
            elementname = node.get(element.getName())

            if element.getName() in get_wanted_iptc_tags():
                max_len = int(get_wanted_iptc_tags()[element.getName()].split('|')[-1])
                if not element.getName() in ['iptc_DateCreated', 'TimeCreated']:
                    if max_len:
                        val = cut_string(val, max_len)

            if elementname == "":
                val = ""
        valuelist = {}

        lock = 0
        differentvalues = 0
        containsemptystring = val == ""

        for node in nodes:
            newvalue = node.get(element.getName())
            containsemptystring = containsemptystring or newvalue == ""
            if newvalue not in valuelist:
                differentvalues += 1
                valuelist[newvalue] = 1

        if differentvalues == 2 and containsemptystring:
            for t in valuelist.keys():
                if t != "":
                    val = t
            lock = 1
        elif differentvalues >= 2:
            val = "? "
            lock = 1

        if val == "" and field.getDefault() != "":
            val = field.getDefault()

        t = getMetadataType(elementtype)

        if field.getUnit() != "":
            unit += field.getUnit()

        ret += '<div id="editor_content">' + \
            t.getEditorHTML(element,
                            value=val,
                            width=field.getWidth(),
                            lock=lock,
                            language=lang(req),
                            required=field.getRequired()) + unit + '</div>'
        if not sub:
            ret += '</div>'
        return ret

    """ create view format """

    def getViewHTML(self, field, nodes, flags, language=None, template_from_caller=None, mask=None):
        element = field.getField()
        if not element:
            return []
        fieldtype = element.get("type")
        t = getMetadataType(element.get("type"))
        unit = ''
        if field.getUnit() != "":
            unit = ' ' + field.getUnit()

        if flags & VIEW_DATA_ONLY:
            if fieldtype in ['text']:
                value = u(t.getFormatedValue(element, nodes[0], language, template_from_caller=template_from_caller, mask=mask)[1])
            else:
                value = u(t.getFormatedValue(element, nodes[0], language)[1])
        else:
            if field.getFormat() != "":
                if fieldtype in ['text']:
                    value = t.getFormatedValue(element, nodes[0], language, template_from_caller=template_from_caller, mask=mask)[1]
                else:
                    value = t.getFormatedValue(element, nodes[0], language)[1]
                value = field.getFormat().replace("<value>", value)
            else:
                if fieldtype in ['text']:
                    if template_from_caller and template_from_caller[0]:  # checking template on test nodes: show full length
                        fieldvalue = nodes[0].get(element.name)
                        if fieldvalue.strip():  # field is filled for this node
                            value = str(t.getFormatedValue(element, nodes[0], language, template_from_caller=fieldvalue, mask=mask)[1])
                        else:  # use default
                            value = str(
                                t.getFormatedValue(element, nodes[0], language, template_from_caller=template_from_caller, mask=mask)[1])
                    else:  # cut long values
                        value = str(
                            formatLongText(
                                t.getFormatedValue(
                                    element,
                                    nodes[0],
                                    language,
                                    template_from_caller=template_from_caller,
                                    mask=mask)[1],
                                element))
                elif fieldtype in ['upload']:
                    # passing mask necessary for fieldtype='upload'
                    value = str(formatLongText(t.getFormatedValue(element, nodes[0], language, mask=mask)[1], element))
                else:
                    value = str(formatLongText(t.getFormatedValue(element, nodes[0], language)[1], element))

        if len(value.strip()) > 0:
            value += str(unit)

        label = '&nbsp;'
        if field.getLabel() != "":
            label = field.getLabel() + ': '

        if flags & VIEW_DATA_ONLY:
            # return a valuelist
            return [element.getName(), value, element.getLabel(), element.get("type")]

        elif flags & VIEW_SUB_ELEMENT:
            # element in hgroup
            # only using value omitting label, delimiter like '&nbsp;' may be inserted in hgroup.getViewHTML
            return value

        elif flags & VIEW_HIDE_EMPTY and value.strip() == "":
            # hide empty elements
            return ''
        elif flags & VIEW_DATA_EXPORT:
            if fieldtype in ['text']:
                return str(t.getFormatedValue(element, nodes[0], language, html=0, template_from_caller=template_from_caller, mask=mask)[1])
            else:
                return str(t.getFormatedValue(element, nodes[0], language, html=0)[1])
            # return element.get("type")
        else:
            # standard view
            ret = '<div class="mask_row field-' + element.getName() + '"><div>'
            ret += '<div class="mask_label">' + label + '</div>\n<div class="mask_value">' + value + '&nbsp;</div>\n'
            ret += '</div></div>'
            return ret

    def getMetaHTML(self, parent, index, sub=False, language=None, itemlist=[], ptype="", fieldlist={}):
        """ return formated row for metaeditor """
        if len(itemlist) > 0:
            # parent still not existing
            item = getNode(itemlist[index])
            pitems = len(itemlist)
        else:
            item = parent.getChildren().sort_by_orderpos()[index]
            ptype = parent.get("type")
            pitems = len(parent.getChildren())

        field = item.getField()
        ret = ''
        label = ''
        description = ''

        if field:
            f = getMetadataType(field.get("type"))
            fieldstring = f.getEditorHTML(field, width=item.getWidth(), value=item.getDefault(), language=language) + ' ' + item.getUnit()
        else:  # node for export mask
            attribute = tree.getNode(item.get("attribute"))
            field = item
            fieldstring = getMetadataType("mappingfield").getEditorHTML(
                field, width=item.getWidth(), value=attribute.getName(), language=language) + ' ' + item.getUnit()

        if item.getDescription() != "":
            description = '<div id="div_description"><a href="#" onclick="openPopup(\'/popup_help?id=%s&maskid=%s\', \'\', 400, 250)"> <img src="/img/tooltip.png" border="0"/></a></div>' % (
                field.id, item.id)

        if len(item.getLabel()) > 0 and item.getLabel() != "mapping":
            label = item.getLabel() + ': '
            required = ""
            if item.getRequired():
                required = '<span class="required">*</span>'

            if ptype in("vgroup", "hgroup") or not sub:
                label = '<div class="label">%s %s</div>%s' % (label, required, description)
            else:
                label += required

        else:
            label = '<div class="label">&nbsp;</div>'
        if not sub:
            ret += '<div id="%s" class="row" onmouseover="pick(this)" onmouseout="unpick(this)" onclick="select(this)" style="position:relative;min-height:30px">' % (
                item.id)

        if len(label) > 0:
            ret += '%s<div id="editor_content">%s</div>' % (label, fieldstring)
        else:
            ret += fieldstring

        if not sub:
            # <small style="color:silver">('+(item.get("type"))+')</small>'
            ret += '<div align="right" id="%s_sub" style="display:none; position:absolute; right:1px; top:3px" class="edit_tools">' % (
                item.id)

            if index > 0:
                ret += '<input type="image" src="/img/uparrow.png" name="up_%s" i18n:attributes="title mask_edit_up_title"/>' % (item.id)
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            if index < pitems - 1:
                ret += '<input type="image" src="/img/downarrow.png" name="down_%s" i18n:attributes="title mask_edit_down_title"/>' % (
                    item.id)
            else:
                ret += '&nbsp;&nbsp;&nbsp;'

            if field.getName() in fieldlist.keys():
                if len(fieldlist[field.getName()]) > 1:
                    ret += '&nbsp;<img src="/img/attention.gif" title="%s ' % (translate("mask_edit_multi_label", language))
                    ret += ", ".join([schema.getName() for schema in fieldlist[field.getName()]]) + '"/>'

            ret += ' <input type="image" src="/img/edit.png" name="edit_%s" i18n:attributes="title mask_edit_edit_row"/> <input type="image" src="/img/delete.png" name="delete_%s" i18n:attributes="title mask_edit_delete_row" onClick="return questionDel()"/></div></div>' % (item.id,
                                                                                                                                                                                                                                                                                  item.id)
        return ret

    def getMetaEditor(self, item, req):
        """ editor mask for field definition """
        attr = {}
        fields = []
        pidnode = None

        if "pid" not in req.params.keys():
            for p in item.getParents():
                try:
                    if p.getMasktype() == "export":
                        pidnode = p
                        break
                except:
                    continue

        metadatatype = req.params.get("metadatatype")
        for t in metadatatype.getDatatypes():
            node = tree.Node(type=t)
            attr.update(node.getTechnAttributes())

        if req.params.get("op", "") == "new":
            pidnode = tree.getNode(req.params.get("pid"))
            if hasattr(pidnode, 'getMasktype') and pidnode.getMasktype() in ("vgroup", "hgroup"):
                for field in pidnode.getAllChildren():
                    if field.getType().getName() == "maskitem" and field.id != pidnode.id:
                        fields.append(field)
            else:
                for m in metadatatype.getMasks():
                    if str(m.id) == str(req.params.get("pid")):
                        for field in m.getChildren():
                            fields.append(field)

        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))
        add_values = []
        val = ""
        if item.getField():
            val = item.getField().getValues()

        for t in getMetaFieldTypeNames():
            f = getMetadataType(t)
            add_values.append(f.getMaskEditorHTML(val, metadatatype=metadatatype, language=lang(req)))

        metafields = metadatatype.getMetaFields()
        metafields.sort(lambda x, y: cmp(x.getName().lower(), y.getName().lower()))

        metafieldtypes = getMetaFieldTypes().values()
        metafieldtypes.sort(lambda x, y: cmp(translate(x.getName(), request=req).lower(), translate(y.getName(), request=req).lower()))

        v = {}
        v["op"] = req.params.get("op", "")
        v["pid"] = req.params.get("pid", "")
        v["item"] = item
        v["metafields"] = metafields
        v["fields"] = fields
        v["fieldtypes"] = metafieldtypes
        v["dateoption"] = dateoption
        v["t_attrs"] = attr
        v["icons"] = {"externer Link": "/img/extlink.png", "Email": "/img/email.png"}
        v["add_values"] = add_values
        v["translate"] = translate
        v["language"] = lang(req)

        if pidnode and hasattr(pidnode, 'getMasktype') and pidnode.getMasktype() == "export":
            v["mappings"] = []
            for m in pidnode.getExportMapping():
                v["mappings"].append(tree.getNode(m))
            return req.getTAL("schema/mask/field.html", v, macro="metaeditor_" + pidnode.getMasktype())
        else:
            return req.getTAL("schema/mask/field.html", v, macro="metaeditor")

    def isContainer(self):
        return True

    def getName(self):
        return "maskfieldtype_field"
