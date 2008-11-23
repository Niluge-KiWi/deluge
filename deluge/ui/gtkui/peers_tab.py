#
# peers_tab.py
#
# Copyright (C) 2008 Andrew Resch <andrewresch@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
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


import gtk, gtk.glade
import os.path
import cPickle
import pkg_resources
import gobject
from itertools import izip

from deluge.ui.client import aclient as client
from deluge.configmanager import ConfigManager
import deluge.component as component
import deluge.common
import deluge.ui.gtkui.common as common
from deluge.ui.gtkui.listview import cell_data_speed as cell_data_speed
from deluge.ui.gtkui.torrentdetails import Tab
from deluge.log import LOG as log

def cell_data_progress(column, cell, model, row, data):
    value = model.get_value(row, data)
    cell.set_property("value", value * 100)
    cell.set_property("text", "%.2f%%" % (value * 100))

class ColumnState:
    def __init__(self, name, position, width, sort, sort_order):
        self.name = name
        self.position = position
        self.width = width
        self.sort = sort
        self.sort_order = sort_order

class PeersTab(Tab):
    def __init__(self):
        Tab.__init__(self)
        glade = component.get("MainWindow").get_glade()

        self._name = "Peers"
        self._child_widget = glade.get_widget("peers_tab")
        self._tab_label = glade.get_widget("peers_tab_label")
        self.peer_menu = glade.get_widget("menu_peer_tab")
        glade.signal_autoconnect({
            "on_menuitem_add_peer_activate": self._on_menuitem_add_peer_activate,
            })

        self.listview = glade.get_widget("peers_listview")
        self.listview.connect("button-press-event", self._on_button_press_event)
        # country pixbuf, ip, client, downspeed, upspeed, country code, int_ip, seed/peer icon, progress
        self.liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, str, int, int, str, gobject.TYPE_UINT, gtk.gdk.Pixbuf, float)
        self.cached_flag_pixbufs = {}

        self.seed_pixbuf = gtk.gdk.pixbuf_new_from_file(deluge.common.get_pixmap("seeding16.png"))
        self.peer_pixbuf = gtk.gdk.pixbuf_new_from_file(deluge.common.get_pixmap("downloading16.png"))

        # key is ip address, item is row iter
        self.peers = {}

        # Country column
        column = gtk.TreeViewColumn()
        render = gtk.CellRendererPixbuf()
        column.pack_start(render, False)
        column.add_attribute(render, "pixbuf", 0)
        column.set_sort_column_id(5)
        column.set_clickable(True)
        column.set_resizable(True)
        column.set_expand(False)
        column.set_min_width(10)
        column.set_reorderable(True)
        self.listview.append_column(column)

        # Address column
        column = gtk.TreeViewColumn(_("Address"))
        render = gtk.CellRendererPixbuf()
        column.pack_start(render, False)
        column.add_attribute(render, "pixbuf", 7)
        render = gtk.CellRendererText()
        column.pack_start(render, False)
        column.add_attribute(render, "text", 1)
        column.set_sort_column_id(6)
        column.set_clickable(True)
        column.set_resizable(True)
        column.set_expand(False)
        column.set_min_width(10)
        column.set_reorderable(True)
        self.listview.append_column(column)

        # Client column
        column = gtk.TreeViewColumn(_("Client"))
        render = gtk.CellRendererText()
        column.pack_start(render, False)
        column.add_attribute(render, "text", 2)
        column.set_sort_column_id(2)
        column.set_clickable(True)
        column.set_resizable(True)
        column.set_expand(False)
        column.set_min_width(10)
        column.set_reorderable(True)
        self.listview.append_column(column)

        # Progress column
        column = gtk.TreeViewColumn(_("Progress"))
        render = gtk.CellRendererProgress()
        column.pack_start(render, True)
        column.set_cell_data_func(render, cell_data_progress, 8)
        column.set_sort_column_id(8)
        column.set_clickable(True)
        column.set_resizable(True)
        column.set_expand(False)
        column.set_min_width(10)
        column.set_reorderable(True)
        self.listview.append_column(column)

        # Down Speed column
        column = gtk.TreeViewColumn(_("Down Speed"))
        render = gtk.CellRendererText()
        column.pack_start(render, False)
        column.set_cell_data_func(render, cell_data_speed, 3)
        column.set_sort_column_id(3)
        column.set_clickable(True)
        column.set_resizable(True)
        column.set_expand(False)
        column.set_min_width(10)
        column.set_reorderable(True)
        self.listview.append_column(column)

        # Up Speed column
        column = gtk.TreeViewColumn(_("Up Speed"))
        render = gtk.CellRendererText()
        column.pack_start(render, False)
        column.set_cell_data_func(render, cell_data_speed, 4)
        column.set_sort_column_id(4)
        column.set_clickable(True)
        column.set_resizable(True)
        column.set_expand(False)
        column.set_min_width(10)
        column.set_reorderable(True)
        self.listview.append_column(column)

        self.listview.set_model(self.liststore)

        self.load_state()

        self.torrent_id = None

    def save_state(self):
        filename = "peers_tab.state"
        state = []
        for index, column in enumerate(self.listview.get_columns()):
            state.append(ColumnState(column.get_title(), index, column.get_width(),
                column.get_sort_indicator(), int(column.get_sort_order())))

        # Get the config location for saving the state file
        config_location = ConfigManager("gtkui.conf")["config_location"]

        try:
            log.debug("Saving FilesTab state file: %s", filename)
            state_file = open(os.path.join(config_location, filename), "wb")
            cPickle.dump(state, state_file)
            state_file.close()
        except IOError, e:
            log.warning("Unable to save state file: %s", e)

    def load_state(self):
        filename = "peers_tab.state"
        # Get the config location for loading the state file
        config_location = ConfigManager("gtkui.conf")["config_location"]
        state = None

        try:
            log.debug("Loading PeersTab state file: %s", filename)
            state_file = open(os.path.join(config_location, filename), "rb")
            state = cPickle.load(state_file)
            state_file.close()
        except (EOFError, IOError), e:
            log.warning("Unable to load state file: %s", e)

        if state == None:
            return

        if len(state) != len(self.listview.get_columns()):
            log.warning("peers_tab.state is not compatible! rejecting..")
            return

        for column_state in state:
            # Find matching columns in the listview
            for (index, column) in enumerate(self.listview.get_columns()):
                if column_state.name == column.get_title():
                    # We have a match, so set options that were saved in state
                    if column_state.width > 0:
                        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                        column.set_fixed_width(column_state.width)
                        column.set_sort_indicator(column_state.sort)
                        column.set_sort_order(column_state.sort_order)
                    if column_state.position != index:
                        # Column is in wrong position
                        if column_state.position == 0:
                            self.listview.move_column_after(column, None)
                        else:
                            self.listview.move_column_after(column, self.listview.get_columns()[column_state.position - 1])

    def update(self):
        # Get the first selected torrent
        torrent_id = component.get("TorrentView").get_selected_torrents()

        # Only use the first torrent in the list or return if None selected
        if len(torrent_id) != 0:
            torrent_id = torrent_id[0]
        else:
            # No torrent is selected in the torrentview
            self.liststore.clear()
            return

        if torrent_id != self.torrent_id:
            # We only want to do this if the torrent_id has changed
            self.liststore.clear()
            self.peers = {}
            self.torrent_id = torrent_id

        client.get_torrent_status(self._on_get_torrent_status, torrent_id, ["peers"])

    def get_flag_pixbuf(self, country):
        if country == "  ":
            return None

        if not self.cached_flag_pixbufs.has_key(country):
            # We haven't created a pixbuf for this country yet
            try:
                self.cached_flag_pixbufs[country] = gtk.gdk.pixbuf_new_from_file(
                    pkg_resources.resource_filename(
                        "deluge",
                         os.path.join("data", "pixmaps", "flags", country.lower() + ".png")))
            except Exception, e:
                log.debug("Unable to load flag: %s", e)
                return None

        return self.cached_flag_pixbufs[country]

    def _on_get_torrent_status(self, status):
        new_ips = set()
        for peer in status["peers"]:
            new_ips.add(peer["ip"])
            if self.peers.has_key(peer["ip"]):
                # We already have this peer in our list, so lets just update it
                row = self.peers[peer["ip"]]
                if not self.liststore.iter_is_valid(row):
                    # This iter is invalid, delete it and continue to next iteration
                    del self.peers[peer["ip"]]
                    continue
                values = self.liststore.get(row, 3, 4, 5, 7, 8)
                if peer["down_speed"] != values[0]:
                    self.liststore.set_value(row, 3, peer["down_speed"])
                if peer["up_speed"] != values[1]:
                    self.liststore.set_value(row, 4, peer["up_speed"])
                if peer["country"] != values[2]:
                    self.liststore.set_value(row, 5, peer["country"])
                    self.liststore.set_value(row, 0, self.get_flag_pixbuf(peer["country"]))
                if peer["seed"]:
                    icon = self.seed_pixbuf
                else:
                    icon = self.peer_pixbuf

                if icon != values[3]:
                    self.liststore.set_value(row, 7, icon)

                if peer["progress"] != values[4]:
                    self.liststore.set_value(row, 8, peer["progress"])
            else:
                # Peer is not in list so we need to add it

                # Create an int IP address for sorting purposes
                ip_int = sum([int(byte) << shift
                    for byte, shift in izip(peer["ip"].split(":")[0].split("."), (24, 16, 8, 0))])

                if peer["seed"]:
                    icon = self.seed_pixbuf
                else:
                    icon = self.peer_pixbuf

                row = self.liststore.append([
                    self.get_flag_pixbuf(peer["country"]),
                    peer["ip"],
                    peer["client"],
                    peer["down_speed"],
                    peer["up_speed"],
                    peer["country"],
                    ip_int,
                    icon,
                    peer["progress"]])

                self.peers[peer["ip"]] = row

        # Now we need to remove any ips that were not in status["peers"] list
        for ip in set(self.peers.keys()).difference(new_ips):
            self.liststore.remove(self.peers[ip])
            del self.peers[ip]

    def clear(self):
        self.liststore.clear()

    def _on_button_press_event(self, widget, event):
        """This is a callback for showing the right-click context menu."""
        log.debug("on_button_press_event")
        # We only care about right-clicks
        if self.torrent_id and event.button == 3:
            self.peer_menu.popup(None, None, None, event.button, event.time)
            return True

    def _on_menuitem_add_peer_activate(self, menuitem):
        """This is a callback for manually adding a peer"""
        log.debug("on_menuitem_add_peer")
        common.add_peer_dialog()
        return True
