﻿"""
 mediatum - a multimedia content repository

 Copyright (C) 2013 Arne Seifert <arne.seifert@tum.de>
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
from workflow import WorkflowStep
from utils.utils import checkXMLString
import utils.mail as mail

class MailError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class WorkflowStep_CheckContent(WorkflowStep):
    def runAction(self, node, op=""):
        attrs = ""
        for k,v in node.items():
            attrs += v
            
        if not checkXMLString(attrs):
            try:
                mail.sendmail(self.get('from'), self.get('to'), self.get('subject'), self.get('text'))
            except:
                pass

        self.forward(node, True)

    
    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("from", "metafield")
        field.set("label", t(lang, "admin_wfstep_checkcontent_sender"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("email", "metafield")
        field.set("label", t(lang, "admin_wfstep_checkcontent_recipient"))
        field.set("type", "text")
        ret.append(field)
        
        field = tree.Node("subject", "metafield")
        field.set("label", t(lang, "admin_wfstep_checkcontent_subject"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("text", "metafield")
        field.set("label", t(lang, "admin_wfstep_checkcontent_text"))
        field.set("type", "memo")
        ret.append(field)
        
    def getLabels(self):
        return { "de":
            [
                ("admin_wfstep_checkcontent_sender", "E-Mail Absender"),
                ("admin_wfstep_checkcontent_recipient", "Empfänger"),
                ("admin_wfstep_checkcontent_subject", "Betreff"),
                ("admin_wfstep_checkcontent_text", "Text"),
                
            ],
           "en":
            [
                ("admin_wfstep_checkcontent_sender", "Email Sender"),
                ("admin_wfstep_checkcontent_recipient", "Recipient"),
                ("admin_wfstep_checkcontent_subject", "Subject"),
                ("admin_wfstep_checkcontent_text", "Text"),
            ]
            }      