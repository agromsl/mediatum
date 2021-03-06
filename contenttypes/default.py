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
import sys
import logging
import time

from mediatumtal import tal
import core.acl as acl
import core.tree as tree
import core.config as config
from core.translation import lang
from core.styles import getContentStyles
import core.users as users
from schema.schema import getMetadataType, VIEW_DATA_ONLY, VIEW_HIDE_EMPTY
from utils.utils import Menu, highlight, format_filesize
from export.exportutils import runTALSnippet, default_context
from web.services.cache import date2string as cache_date2string

languages = [l.strip() for l in config.get("i18n.languages").split(",") if l.strip()]

# for TAL templates from mask cache
context = default_context.copy()
context['host'] = "http://" + config.get("host.name")

DEFAULT_MASKCACHE = 'deep'  # 'deep' | 'shallow' | None
# remark 2013-09-18 wn: only deep cache compatible with multilingual text/memo/htmlmemo fields


def init_maskcache():
    global maskcache, maskcache_shallow, maskcache_accesscount, maskcache_msg
# for deep mask caching
maskcache = {}
maskcache_accesscount = {}
maskcache_msg = '| cache initialized %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')

# for shallow mask caching
maskcache_shallow = {}


def get_maskcache_report():
    s = maskcache_msg + "| %d lookup keys in cache, total access count: %d\r\n|\r\n"
    total_access_count = 0
    for k, v in sorted(maskcache_accesscount.items()):
        s += "| %s : %s\r\n" % (k.ljust(60, '.'), str(v).rjust(8, '.'))
        total_access_count += v
    return s % (len(maskcache_accesscount), total_access_count)


def flush_maskcache(req=None):
    global maskcache, maskcache_accesscount, maskcache_shallow, maskcache_msg
    logging.getLogger("everything").info("going to flush maskcache, content is: \r\n" + get_maskcache_report())
    maskcache = {}
    maskcache_accesscount = {}
    maskcache_shallow = {}
    if req:
        user = users.getUserFromRequest(req)
        logging.getLogger("everything").info("flush of masks cache triggered by user %s with request on '%s'" % (user.name, req.path))

        sys.stdout.flush()
    maskcache_msg = '| cache last flushed %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')


def make_lookup_key(node, language=languages[0], labels=True):
    global languages
    flaglabels = 'nolabels'
    if labels:
        flaglabels = 'uselabels'

    if language in languages:
        return "%s_%s_%s" % (str(node.type), str(language), flaglabels)
    else:
        return "%s_%s_%s" % (str(node.type), languages[0], flaglabels)


def get_maskcache_entry(lookup_key):
    try:
        res = maskcache[lookup_key]
        maskcache_accesscount[lookup_key] += 1
    except:
        res = None
    return res


class Default(tree.Node):

    def getTypeAlias(self):
        return "default"

    def getOriginalTypeName(self):
        return "original"

    def getCategoryName(self):
        return "undefined"

    def getDetailsCondition(self):
        '''checks if 'details' should be displayed
           or not

           :return: boolean
        '''
        if self.get('system.prev_id') != '' and len(self.getChildren()) > 0 in [(c.get('system.next_id') != '') for c in self.getChildren()]:
            return True
        else:
            return (self.get('system.prev_id') == '') or (len(self.getChildren()) > 0) in [(c.get('system.prev_id') != '') for c in self.getChildren()]

    def getFurtherDetailsCondition(self, req):
        '''checks if 'further details'
           should be displayed or not

           :return: boolean
        '''
        try:
            if len(tree.getNode(req.params.get('pid', self.id)).getChildren()) == 1:
                return False
            if len(self.getParents()) > 0:
                return True
            else:
                return (self.get('system.prev_id') == '') or (len(self.getChildren()) > 0) in [(c.get('system.prev_id') != '') for c in self.getChildren()]
        except tree.NoSuchNodeError:
            return False

    def getParentInformation(self, req):
        '''sets diffrent used Information
           to a dict object

           :param req: request object
           :return: dict parentInformation
        '''
        parentInformation = {}
        pid = req.params.get('pid', self.id)
        parentInformation['parent_node_id'] = pid

        if len(self.getChildren()) > 0 and self.isContainer() != 1:
            parentInformation['children_list'] = [child for child in self.getChildren() if not child.get('system.next_id') != '']
        else:
            parentInformation['children_list'] = []

        if len([sib.id for sib in filter(lambda itm: str(itm.id) == pid, self.getParents())]) != 0:
            parentInformation['parent_condition'] = True
            parentInformation['siblings_list'] = [c for c in tree.getNode(pid).getChildren() if c.id != self.id]
        else:
            parentInformation['parent_condition'] = False
            if len(self.getParents()) > 0:
                parentInformation['siblings_list'] = self.getParents()[0].getChildren()
            else:
                parentInformation['siblings_list'] = []

        parentInformation['display_siblings'] = pid != self.id
        parentInformation['parent_is_container'] = [id for id in self.getParents() if self.isContainer() != 1]
        parentInformation['details_condition'] = self.getDetailsCondition()
        parentInformation['further_details'] = self.getFurtherDetailsCondition(req)

        return parentInformation

    def show_node_big(self, req, template="", macro=""):
        mask = self.getFullView(lang(req))
        access = acl.AccessData(req)

        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()
        # hide empty elements}, macro)
        node = self

        return req.getTAL(template,
                          {'node': self,
                           'metadata': mask.getViewHTML([self], VIEW_HIDE_EMPTY),
                           'format_size': format_filesize,
                           'access': access,
                           'parentInformation': self.getParentInformation(req)
                          })

    def show_node_image(self, language=None):
        return tal.getTAL(
            "contenttypes/default.html", {'children': self.getChildren().sort_by_orderpos(),
                                          'node': self},
                                          macro="show_node_image")

    def show_node_text(self, words=None, language=None, separator="", labels=0, cachetype=DEFAULT_MASKCACHE):
        if cachetype not in ['shallow', 'deep']:
            return self.show_node_text_orignal(words=words, language=language, separator=separator, labels=labels)
        elif cachetype == 'deep':
            return self.show_node_text_deep(words=words, language=language, separator=separator, labels=labels)
        else:
            return self.show_node_text_shallow(words=words, language=language, separator=separator, labels=labels)

    """ format preview node text """
    # original

    def show_node_text_orignal(self, words=None, language=None, separator="", labels=0):
        if separator == "":
            separator = "<br/>"
        metatext = list()
        mask = self.getMask("nodesmall")
        for m in self.getMasks("shortview", language=language):
            mask = m

        if mask:
            fields = mask.getMaskFields()
            for field in mask.getViewHTML([self], VIEW_DATA_ONLY, language=language, mask=mask):
                if len(field) >= 2:
                    value = field[1]
                else:
                    value = ""

                if words is not None:
                    value = highlight(value, words, '<font class="hilite">', "</font>")

                if value:
                    if labels:
                        for f in fields:
                            if f.getField().getName() == field[0]:
                                metatext.append("<b>%s:</b> %s" % (f.getLabel(), value))
                                break
                    else:
                        if field[0].startswith("author"):
                            value = '<span class="author">%s</span>' % value
                        if field[0].startswith("subject"):
                            value = '<b>%s</b>' % value
                        metatext.append(value)
        else:
            metatext.append('&lt;smallview mask not defined&gt;')

        return separator.join(metatext)

    # deep caching
    def show_node_text_deep(self, words=None, language=None, separator="", labels=0):

        def render_mask_template(node, mfs, words=None, separator="", skip_empty_fields=True):
            """
               mfs: [mask] + list_of_maskfields
            """
            res = []
            exception_count = {}
            mask = mfs[0]
            for node_attribute, fd in mfs[1:]:
                metafield_type = fd['metafield_type']
                field_type = fd['field_type']
                if metafield_type in ['date', 'url', 'hlist']:
                    exception_count[metafield_type] = exception_count.setdefault(metafield_type, 0) + 1
                    value = node.get(node_attribute)
                    try:
                        value = fd['metadatatype'].getFormatedValue(fd['element'], node, language=language, mask=mask)[1]
                    except:
                        value = fd['metadatatype'].getFormatedValue(fd['element'], node, language=language)[1]
                elif metafield_type in ['field']:
                    if field_type in ['hgroup', 'vgroup']:
                        _sep = ''
                        if field_type == 'hgroup':
                            fd['unit'] = ''  # unit will be taken from definition of the hgroup
                            use_label = False
                        else:
                            use_label = True
                        value = getMetadataType(field_type).getViewHTML(
                                                                         fd['field'],  # field
                                                                         [node],  # nodes
                                                                         0,  # flags
                                                                         language=language,
                                                                         mask=mask, use_label=use_label)
                else:
                    value = node.get(node_attribute)
                    metadatatype = fd['metadatatype']

                    if hasattr(metadatatype, "language_snipper"):
                        metafield = fd['element']
                        if (metafield.get("type") == "text" and metafield.get("valuelist") == "multilingual") \
                            or \
                           (metafield.get("type") in ['memo', 'htmlmemo'] and metafield.get("multilang") == '1'):
                            value = metadatatype.language_snipper(value, language)

                    if value.find('&lt;') >= 0:
                        # replace variables
                        for var in re.findall(r'&lt;(.+?)&gt;', value):
                            if var == "att:id":
                                value = value.replace("&lt;" + var + "&gt;", node.id)
                            elif var.startswith("att:"):
                                val = node.get(var[4:])
                                if val == "":
                                    val = "____"

                                value = value.replace("&lt;" + var + "&gt;", val)
                        value = value.replace("&lt;", "<").replace("&gt;", ">")

                    if value.find('<') >= 0:
                        # replace variables
                        for var in re.findall(r'\<(.+?)\>', value):
                            if var == "att:id":
                                value = value.replace("<" + var + ">", node.id)
                            elif var.startswith("att:"):
                                val = node.get(var[4:])
                                if val == "":
                                    val = "____"

                                value = value.replace("&lt;" + var + "&gt;", val)
                        value = value.replace("&lt;", "<").replace("&gt;", ">")

                    if value.find('tal:') >= 0:
                        context['node'] = node
                        value = runTALSnippet(value, context)

                    # don't escape before running TAL
                    if (not value) and fd['default']:
                        default = fd['default']
                        if fd['default_has_tal']:
                            context['node'] = node
                            value = runTALSnippet(default, context)
                        else:
                            value = default

                if skip_empty_fields and not value:
                    continue

                if fd["unit"]:
                    value = value + " " + fd["unit"]
                if fd["format"]:
                    value = fd["format"].replace("<value>", value)
                if words:
                    value = highlight(value, words, '<font class="hilite">', "</font>")
                res.append(fd["template"] % value)
            if exception_count and len(exception_count.keys()) > 1:
                pass
            return separator.join(res)

        if not separator:
            separator = "<br/>"

        lookup_key = make_lookup_key(self, language, labels)

        # if the lookup_key is already in the cache dict: render the cached mask_template
        # else: build the mask_template

        if lookup_key in maskcache:
            mfs = maskcache[lookup_key]
            res = render_mask_template(self, mfs, words=words, separator=separator)
            maskcache_accesscount[lookup_key] += 1
        else:
            mask = self.getMask("nodesmall")
            for m in self.getMasks("shortview", language=language):
                mask = m

            if mask:
                mfs = [mask]  # mask fields
                values = []
                fields = mask.getMaskFields(first_level_only=True)
                ordered_fields = sorted([(f.orderpos, f) for f in fields])
                for orderpos, field in ordered_fields:
                    fd = {}  # field descriptor
                    fd['field'] = field
                    element = field.getField()
                    element_type = element.get('type')
                    field_type = field.get('type')

                    t = getMetadataType(element.get("type"))

                    fd['format'] = field.getFormat()
                    fd['unit'] = field.getUnit()
                    label = field.getLabel()
                    fd['label'] = label
                    default = field.getDefault()
                    fd['default'] = default
                    fd['default_has_tal'] = (default.find('tal:') >= 0)

                    fd['metadatatype'] = t
                    fd['metafield_type'] = element_type
                    fd['element'] = element
                    fd['field_type'] = field_type

                    def getNodeAttributeName(field):
                        metafields = [x for x in field.getChildren() if x.type == 'metafield']
                        if len(metafields) != 1:
                            # this can only happen in case of vgroup or hgroup
                            logging.getLogger("error").error("maskfield %s zero or multiple metafield child(s)" % field.id)
                            return field.name
                        return metafields[0].name

                    node_attribute = getNodeAttributeName(field)
                    fd['node_attribute'] = node_attribute

                    def build_field_template(field_descriptor):
                        if labels:
                            template = "<b>" + field_descriptor['label'] + ":</b> %s"
                        else:
                            if field_descriptor['node_attribute'].startswith("author"):
                                template = '<span class="author">%s</span>'
                            elif field_descriptor['node_attribute'].startswith("subject"):
                                template = '<b>%s</b>'
                            else:
                                template = "%s"
                        return template

                    template = build_field_template(fd)

                    fd['template'] = template
                    long_field_descriptor = [node_attribute, fd]
                    mfs = mfs + [long_field_descriptor]

                maskcache[lookup_key] = mfs
                maskcache_accesscount[lookup_key] = 0
                res = render_mask_template(self, mfs, words=words, separator=separator)

            else:
                res = '&lt;smallview mask not defined&gt;'

            if element_type == 'date':
                comp = res.split(separator)
                pre = comp[0].split('(')[-1].strip(')')

                print comp, pre
        return res

    # shallow caching
    def show_node_text_shallow(self, words=None, language=None, separator="", labels=0):
        global maskcache_shallow

        def render_mask_template(node, mfs, words=None, separator=""):
            mask, fields, labels_data = mfs
            metatext = list()

            for field in mask.getViewHTML([node], VIEW_DATA_ONLY, language=language, mask=mask):
                if len(field) >= 2:
                    value = field[1]
                else:
                    value = ""

                if words is not None:
                    value = highlight(value, words, '<font class="hilite">', "</font>")

                if value:
                    if labels:
                        for f, f_name, f_label in labels_data:
                            if f_name == field[0]:
                                metatext.append("<b>%s:</b> %s" % (f_label, value))
                                break
                    else:

                        if field[0].startswith("author"):
                            value = '<span class="author">%s</span>' % value
                        if field[0].startswith("subject"):
                            value = '<b>%s</b>' % value
                        metatext.append(value)

            return separator.join(metatext)

        if not separator:
            separator = "<br/>"

        lookup_key = make_lookup_key(self, language, labels)

        if lookup_key in maskcache_shallow:
            mfs = maskcache_shallow[lookup_key]
            return render_mask_template(self, mfs, words=words, separator=separator)
        else:
            # this list will be cached
            to_be_cached = []

            metatext = list()
            mask = self.getMask("nodesmall")
            for m in self.getMasks("shortview", language=language):
                mask = m

            if mask:
                fields = mask.getMaskFields()

                def getNodeAttributeName(field):
                    metafields = [x for x in field.getChildren() if x.type == 'metafield']
                    if len(metafields) != 1:
                        logging.getLogger("error").error("maskfield %s zero or multiple metafield child(s)" % field.id)
                    return metafields[0].name

                if labels:
                    labels_data = [(f, f.getField().getName(), f.getLabel()) for f in fields]
                else:
                    pass
                    labels_data = []

                for field in mask.getViewHTML([self], VIEW_DATA_ONLY, language=language, mask=mask):
                    if len(field) >= 2:
                        value = field[1]
                    else:
                        value = ""

                    if words is not None:
                        value = highlight(value, words, '<font class="hilite">', "</font>")

                    if value:
                        if labels:
                            for f, f_name, f_label in labels_data:
                                if f_name == field[0]:
                                    metatext.append("<b>%s:</b> %s" % (f_label, value))
                                    break
                        else:

                            if field[0].startswith("author"):
                                value = '<span class="author">%s</span>' % value
                            if field[0].startswith("subject"):
                                value = '<b>%s</b>' % value
                            metatext.append(value)

                to_be_cached = [mask, fields, labels_data]
                maskcache_shallow[lookup_key] = to_be_cached

            else:
                metatext.append('&lt;smallview mask not defined&gt;')
            return separator.join(metatext)

    def isContainer(self):
        return 0

    def getTreeIcon(self):
        return ""

    def isSystemType(self):
        return 0

    def get_name(self):
        return self.name

    def getTechnAttributes(self):
        return {}

    def has_object(self):
        return True

    def getFullView(self, language):
        masks = self.getMasks(type="fullview", language=language)
        if len(masks) > 1:
            for m in masks:
                if m.getLanguage() == language:
                    return m
            for m in masks:
                if m.getLanguage() in ["", "no"]:
                    return m
        elif len(masks) == 0:
            return tree.Node("", type="mask")
        else:
            return masks[0]

    def getSysFiles(self):
        return []

    def buildLZAVersion(self):
        print "no lza builder implemented"

    def getEditMenuTabs(self):
        menu = list()
        try:
            submenu = Menu("menuglobals", "..")
            menu.append(submenu)
        except TypeError:
            pass
        return ";".join([m.getString() for m in menu])

    def getDefaultEditTab(self):
        return "view"

    def childcount(self):
        return 0

    def getLabel(self):
        return self.getName()
