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
import hashlib
import core.tree as tree
import core.usergroups as usergroups
import core.config as config
import core.translation as translation
from core.users import useroption


class User(tree.Node):

    def getGroups(self):
        groups = []
        for p in self.getParents():
            if p.type == "usergroup":
                groups += [p.getName()]
        return groups

    def getLastName(self):
        return self.get("lastname")

    def setLastName(self, value):
        self.set("lastname", value)

    def getFirstName(self):
        return self.get("firstname")

    def setFirstName(self, value):
        self.set("firstname", value)

    def getTelephone(self):
        return self.get("telephone")

    def setTelephone(self, value):
        self.set("telephone", value)

    def getComment(self):
        return self.get("comment")

    def setComment(self, value):
        self.set("comment", value)

    def getEmail(self):
        return self.get("email")

    def setEmail(self, m):
        return self.set("email", m)

    def getPassword(self):
        return self.get("password")

    def setPassword(self, p):
        self.set("password", hashlib.md5(p).hexdigest())

    def inGroup(self, id):
        for group in self.getGroups():
            if group == id:
                return True
        return False

    def getOption(self):
        return self.get("opts")

    def setOption(self, o):
        return self.set("opts", o)

    def getOptionList(self):
        retList = {}
        myoptions = self.getOption()
        for option in useroption:
            if option.value in myoptions and option.value != "":
                retList[option.getName()] = True
            else:
                retList[option.getName()] = False
        return retList

    def isGuest(self):
        return self.getName() == config.get("user.guestuser")

    def isAdmin(self):
        return self.inGroup(config.get("user.admingroup", "Administration"))

    def isEditor(self):
        for group in self.getGroups():
            if "e" in str(usergroups.getGroup(group).getOption()):
                return True
        return False

    def isWorkflowEditor(self):
        for group in self.getGroups():
            if "w" in str(usergroups.getGroup(group).getOption()):
                return True
        return False

    def stdPassword(self):
        return self.get("password") == hashlib.md5(config.get("user.passwd")).hexdigest()

    def resetPassword(self, newPwd):
        self.set("password", hashlib.md5(newPwd).hexdigest())

    def translate(self, key):
        return translation.translate(key=key, user=self)

    def isSystemType(self):
        return 1

    def setUserType(self, value):
        self.usertype = value

    def getUserType(self):
        for p in self.getParents():
            if p.type == "usergroup":
                continue
            return p.getName()

        # try:
        #    print "else", self.usertype
        #    return self.usertype
        # except AttributeError:
        #    print " ->", self.getName()
        #    for p in self.getParents():
        #
        #        print "   p:", p.getName(), p.id, p.type
        #        if p.type=="usergroup":
        #            continue
        #        return p.getName()

    def setOrganisation(self, value):
        self.set("organisation", value)

    def getOrganisation(self):
        return self.get("organisation")

    def allowAdd(self):
        return 1

    def canChangePWD(self):
        if self.isAdmin():
            return 0
        if self.getUserType() == "users":
            return "c" in self.getOption()
        else:
            from core.users import authenticators
            return authenticators[self.getUserType()].canChangePWD()

    def getShoppingBag(self, name=""):
        ret = []
        for c in self.getChildren():
            if c.getContentType() == "shoppingbag":
                if str(c.id) == str(name) or c.getName() == name:
                    return [c]
                else:
                    ret.append(c)
        return ret

    def addShoppingBag(self, name, items=[]):
        sb = tree.Node(name, type="shoppingbag")
        sb.setItems(items)
        self.addChild(sb)

    def isDynamicUser(self):
        """user objects that are not persisted in the database are labeled 'dynamic'"""
        return False

    def getUserID(self):
        """
        for compatibility with dynamic users that are not persisted as nodes:
        those will return a unique identifier for their directory entry
        nodes should return the node id
        """
        return self.id


class ExternalUser:

    def getUserType(self):
        return self.usertype

    def getUser(self):
        raise "not implemented"

    def authenticate_login(self, username, password):
        raise "notImplemented"

    def getName(self):
        return ""

    def allowAdd(self):
        return 0

    def canChangePWD(self):
        raise "not implemented"

    def getAdminOperation(self, req, params={}):
        raise "not implemented"

    def isDynamicUser(self):
        """user objects that are not persisted in the database are labeled 'dynamic'"""
        return False
