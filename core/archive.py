"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2009 Matthias Kramm <kramm@in.tum.de>

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

import core
import sys
import thread
import time
import logging
import core.config as config
import core.tree as tree
from core.tree import db
from core import archivemanager
from utils.utils import splitpath, intersection, union
from utils.date import parse_date, now, format_date



def archive_log(message, type="info"):
    if type=="info":
        logging.getLogger("archive").info(message)
    else:
        logging.getLogger("archive").error(message)
        
class Archive:

    def __init__(self):
        self.lock = thread.allocate_lock()
    
    def acquire(self):
        self.lock.acquire()

        
    def release(self):
        self.lock.release()
    
    def getLockState(self):
        return self.lock

    def actionArchive(self, nodes):
        None

    def getArchivedFile(self, node):
        None
        
    def deleteFromArchive(self, filename):
        None
        
    def writelog(self, message="", type="info"):
        archive_log(message, type)
        
    def info(self):
        return "no description of archive manager found"
        
    def stat(self, attribute=""):
        stat = {}
        stat['name'] = str(self)
        stat['used'] = db.getNodeIdByAttribute("archive_type", str(self))       
        stat['state1'] = len(intersection([stat['used'], db.getNodeIdByAttribute("archive_state", "1")]))
        stat['state2'] = len(intersection([stat['used'], db.getNodeIdByAttribute("archive_state", "3")]))
        stat['state3'] = len(intersection([stat['used'], db.getNodeIdByAttribute("archive_state", "3")]))
        stat['used'] = len(stat['used'])
        
        if attribute=="":
            return stat
        elif attribute in stat.keys():
            return stat[attribute]
            

        
class ArchiveManager:

    def __init__(self):
        self.manager = []

        if config.get("archive.activate", "").lower()=="true":
            print "Initializing archive manager:",
            for paths in config.get("archive.class").split(";"):
                path, manager = splitpath(paths)
                if path and path not in sys.path:
                    sys.path += [path]
                m = __import__(manager).__dict__[manager]()
                print m,",",
                self.manager.append(m)
            print len(self.manager), "manager loaded"

        if len(self.manager)>0:
            None
            # start archiving thread
            thread_id = thread.start_new_thread(self.archive_thread, ())
            archive_log("started archiving thread, thread_id="+str(thread_id))
    
    def getManager(self, name=""):
        if name=="":
            return self.manager
        for manager in self.manager:
            if str(manager)==name:
                return manager
        return None
            
    def archive_thread(self):
        global db
        if not time:
            return
        while 1:
            time.sleep(int(config.get("archive.interval",10)))
            archive_nodes_3 = db.getNodeIdByAttribute("archive_state", "3")
            archive_nodes_2 = []

            date_now = format_date(now(), "yyymmddhhmmss")

            for manager in self.manager:
                # search for nodes to archive after access over period (state 2)
                for n in db.getNodeIdByAttribute("archive_state", "2"):
                    node = tree.getNode(n)
                    if node.get("archive_date"):
                        date_archive = format_date(parse_date(node.get("archive_date"),"%Y-%m-%dT%H:%M:%S"), "yyymmddhhmmss")
                        if date_now >= date_archive:
                            archive_nodes_2.append(long(node.id))
                
                # union to get all nodes with state 3 and 2 with over period
                archive_nodes = union((archive_nodes_3, archive_nodes_2))
                nodes = intersection((db.getNodeIdByAttribute("archive_type",str(manager)), archive_nodes))
                
                # run action defined in manager
                manager.actionArchive(nodes)


def initialize():
    global init
    archive_manager = []
    if config.get("archive.activate", "").lower()=="true":
        print "Initializing archive manager:",
        for paths in config.get("archive.class").split(";"):
            path, manager = splitpath(paths)
            if path and path not in sys.path:
                sys.path += [path]
            m = __import__(manager).__dict__[manager]()
            print m,",",
            archive_manager.append(m)
        print len(archive_manager), "manager loaded"
    if len(archive_manager)>0:
        None
        # start archiving thread
        thread_id = thread.start_new_thread(archive_thread, ())
        log.info("started archiving thread, thread_id="+str(thread_id))
        
        return archive_manager