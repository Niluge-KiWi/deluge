#
# toolbar.py
#
# Copyright (C) 2007 Andrew Resch ('andar') <andrewresch@gmail.com>
# 
# Deluge is free software.
# 
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 2 of the License, or (at your option)
# any later version.
# 
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA    02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.

import pygtk
pygtk.require('2.0')
import gtk, gtk.glade
import gobject

import deluge.ui.component as component
from deluge.log import LOG as log
from deluge.common import TORRENT_STATE
import deluge.ui.client as client

class ToolBar(component.Component):
    STATE_FINISHED = TORRENT_STATE.index("Finished")
    STATE_SEEDING = TORRENT_STATE.index("Seeding")
    STATE_PAUSED = TORRENT_STATE.index("Paused")
    def __init__(self):
        component.Component.__init__(self, "ToolBar")
        log.debug("ToolBar Init..")
        self.window = component.get("MainWindow")
        self.toolbar = self.window.main_glade.get_widget("toolbar")
        ### Connect Signals ###
        self.window.main_glade.signal_autoconnect({
            "on_toolbutton_add_clicked": self.on_toolbutton_add_clicked,
            "on_toolbutton_remove_clicked": self.on_toolbutton_remove_clicked,
            "on_toolbutton_clear_clicked": self.on_toolbutton_clear_clicked,
            "on_toolbutton_pause_clicked": self.on_toolbutton_pause_clicked,
            "on_toolbutton_resume_clicked": self.on_toolbutton_resume_clicked,
            "on_toolbutton_preferences_clicked": \
                self.on_toolbutton_preferences_clicked,
            "on_toolbutton_connectionmanager_clicked": \
                self.on_toolbutton_connectionmanager_clicked
        })
        self.change_sensitivity = [
            "toolbutton_add",
            "toolbutton_remove",
            "toolbutton_clear",
            "toolbutton_pause",
            "toolbutton_resume"
        ]

    def start(self):
        for widget in self.change_sensitivity:
            self.window.main_glade.get_widget(widget).set_sensitive(True)
        gobject.idle_add(self.update_buttons)
    
    def stop(self):
        for widget in self.change_sensitivity:
            self.window.main_glade.get_widget(widget).set_sensitive(False)
        
    def visible(self, visible):
        if visible:
            self.toolbar.show()
        else:
            self.toolbar.hide()
            
    def add_toolbutton(self, callback, label=None, image=None, stock=None,
                                                         tooltip=None):
        """Adds a toolbutton to the toolbar"""
        # Create the button
        toolbutton = gtk.ToolButton(stock)
        if label is not None:
            toolbutton.set_label(label)
        if image is not None:
            toolbutton.set_icon_widget(image)
        # Set the tooltip
        if tooltip is not None:
            tip = gtk.Tooltips()
            tip.set_tip(toolbutton, tooltip)
        
        # Connect the 'clicked' event callback
        toolbutton.connect("clicked", callback)
        
        # Append the button to the toolbar
        self.toolbar.insert(toolbutton, -1)
        
        # Show the new toolbutton
        toolbutton.show()
        
        return toolbutton
    
    def add_separator(self, position=None):
        """Adds a separator toolitem"""
        sep = gtk.SeparatorToolItem()
        if position is not None:
            self.toolbar.insert(sep, position)
        else:
            # Append the separator
            self.toolbar.insert(sep, -1)

        sep.show()
        
        return sep
    
    def remove(self, widget):
        """Removes a widget from the toolbar"""
        self.toolbar.remove(widget)
            
    ### Callbacks ###
    def on_toolbutton_add_clicked(self, data):
        log.debug("on_toolbutton_add_clicked")
        # Use the menubar's callback
        component.get("MenuBar").on_menuitem_addtorrent_activate(data)

    def on_toolbutton_remove_clicked(self, data):
        log.debug("on_toolbutton_remove_clicked")
        # Use the menubar's callbacks
        component.get("MenuBar").on_menuitem_remove_activate(data)

    def on_toolbutton_clear_clicked(self, data):
        log.debug("on_toolbutton_clear_clicked")
        # Use the menubar's callbacks
        component.get("MenuBar").on_menuitem_clear_activate(data)
        
    def on_toolbutton_pause_clicked(self, data):
        log.debug("on_toolbutton_pause_clicked")
        # Use the menubar's callbacks
        component.get("MenuBar").on_menuitem_pause_activate(data)
     
    def on_toolbutton_resume_clicked(self, data):
        log.debug("on_toolbutton_resume_clicked")
        # Use the menubar's calbacks
        component.get("MenuBar").on_menuitem_resume_activate(data)

    def on_toolbutton_preferences_clicked(self, data):
        log.debug("on_toolbutton_preferences_clicked")
        # Use the menubar's callbacks
        component.get("MenuBar").on_menuitem_preferences_activate(data)

    def on_toolbutton_connectionmanager_clicked(self, data):
        log.debug("on_toolbutton_connectionmanager_clicked")
        # Use the menubar's callbacks
        component.get("MenuBar").on_menuitem_connectionmanager_activate(data)

    def update_buttons(self):
        log.debug("update_buttons")
        # If all the selected torrents are paused, then disable the 'Pause' 
        # button.
        # The same goes for the 'Resume' button.
        pause = False
        resume = False

        # Disable the 'Clear Seeders' button if there's no finished torrent
        finished = False

        selecteds = component.get('TorrentView').get_selected_torrents()
        if not selecteds : selecteds  = []

        for torrent in  selecteds :
            status = client.get_torrent_status(torrent, ['state'])['state']
            if status == self.STATE_PAUSED:
                resume = True
            elif status in [self.STATE_FINISHED, self.STATE_SEEDING]:
                finished = True
                pause = True
            else:
                pause = True
            if pause and resume and finished:    break

        # Enable the 'Remove Torrent' button only if there's some selected 
        # torrent.
        remove = (len(selecteds ) > 0)

        if not finished:
            torrents = client.get_session_state()
            for torrent in torrents:
                if torrent in selecteds: continue
                status = client.get_torrent_status(torrent, ['state'])['state']
                if status in [self.STATE_FINISHED, self.STATE_SEEDING]:
                    finished = True
                    break

        for name, sensitive in (("toolbutton_pause", pause),
                                ("toolbutton_resume", resume),
                                ("toolbutton_remove", remove),
                                ("toolbutton_clear", finished)):
            self.window.main_glade.get_widget(name).set_sensitive(sensitive)

        return False

