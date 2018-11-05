#!/usr/bin/python3
# -*- coding: utf-8 -*-


#                 YAMuPlay - Yet Another Music Player
#                 Copyright (C) 2016-2018 schlizbaeda
#
# YAMuPlay is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License
# or any later version.
#             
# YAMuPlay is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with YAMuPlay. If not, see <http://www.gnu.org/licenses/>.
#
#
# Contributions:
# --------------
# Thanks to meigrafd from the German Raspberry Pi forum for improving 
# my code from classical python programming (imperative programming 
# paradigm) into object-oriented python code. That made it much easier
# to maintain this project.
#   http://roxxs.org/index.php/author/meigrafd/
#   https://forum-raspberrypi.de/user/5394-meigrafd/
# Further thanks to linusg from the German Raspberry Pi forum too.
# He gave lots of useful hints due to python programming on 
# github issue #1 which I'm going to implement in the next time... 
#   https://linusgroh.de/
#   https://github.com/linusg
#
# YAMuPlay uses the following modules:
# ------------------------------------
#
# * python3-dbus             V?                               MIT
# * python-omxplayer-wrapper V0.2.4                           LGPL v3
# * pyudev                   V0.21.0                          LGPL v2.1
# * python-magic             V0.4.13                          MIT
#
# The current GitHub repository of YAMuPlay contains all external
# modules which are necessary for running YAMuPlay. This was decided by
# schlizbaeda for version 0.2.1 and up to avoid any inconsistencies in 
# future due to incompatible updates of these modules by their owners. 
# This already happened twice in past.
# Call the following commands to install the necessary external modules:
# 
#   cd /home/pi/yamuplay
#   sudo apt-get install python3-dbus # not part of YAMuPlay repository
#
#   #git clone https://github.com/willprice/python-omxplayer-wrapper.git
#   cd /home/pi/yamuplay/python-omxplayer-wrapper
#   sudo python3 setup.py install
#
#   #git clone https://github.com/pyudev/pyudev.git
#   cd /home/pi/yamuplay/pyudev
#   sudo python3 setup.py install
#
#   #git clone https://github.com/ahupp/python-magic.git
#   cd /home/pi/yamuplay/python-magic
#   sudo python3 setup.py install
#


import signal # notwendig, um richtig auf Strg+C (in der aufrufenden Konsole) zu reagieren
import sys    # 2017-08-14 schlizbaeda V0.2: notwendig, um die Kommandozeilenparameter zu ermitteln
import magic  # 2017-08-14 schlizbaeda V0.2: notwendig, um die "Magic Number" (Dateityp) einer Datei zu ermitteln
import copy   # 2017-09-20 schlizbaeda V0.2.1: Modul zum ECHTEN Kopieren von veränderlichen Datentypen ("mutable", z.B. Listen)
import os
import time
from omxplayer import OMXPlayer

# tkinter
import tkinter
import tkinter.ttk # wird in dieser Software nur für das Treeview-Steuerelement benötigt
import tkinter.font
import tkinter.messagebox
import tkinter.filedialog
import tkinter.colorchooser

# Module für USB-detect-Ereignisse:
import pyudev

############ HAUPTPTOGRAMM ############ 
class YAMuPlay(object):
    def __init__(self, mediapath = '/media/pi'): # TODO: Unterscheidung wheezy (/media) und jessie (/media/pi)     
        # globale Variablen mit Vorbelegung:
        self.gl_appName = 'YAMuPlay'
        self.gl_appVer = '0.4.0'
        
        # schlizbaeda v0.4.0: Einführung von verschiedenen Verfbosity-Gruppen in Form von Flags:
        self.GL_VERBOSITY_ERROR = 1      # keine Ausgaben (nur Fehler)
        self.GL_VERBOSITY_WARNING = 2    # keine Ausgaben (nur Warnungen)
        self.GL_VERBOSITY_HELP = 4       # Hilfetext beim Programmstart anzeigen
        self.GL_VERBOSITY_NORMAL = 8     # Ausgabe der aktuellen Aktion (z.B. Play-Schaltfläche geklickt)
        self.GL_VERBOSITY_USB = 16        # USB-Ereignisse
        self.GL_VERBOSITY_OMXPLAYER = 32 # Ausgabe der Kommandos an den omxplayer
        self.GL_VERBOSITY_RECEIVE = 64   # Ausgabe der Rückgabewerte vom omxplayer
        self.GL_VERBOSITY_DEBUG = 128    # Debugmeldungen ausgeben
        self.gl_verbosity = self.GL_VERBOSITY_ERROR + self.GL_VERBOSITY_WARNING + self.GL_VERBOSITY_HELP + self.GL_VERBOSITY_NORMAL + self.GL_VERBOSITY_USB + self.GL_VERBOSITY_OMXPLAYER + self.GL_VERBOSITY_RECEIVE #+ self.GL_VERBOSITY_DEBUG
        
        self.GL_PATHSEPARATOR = '/'          # TODO: os.path.sep() liefert das Pfad-Trennzeichen, unter LINUX '/'
        self.gl_MediaDir = mediapath
        self.gl_quit = 0                     # globaler Merker für andere Threads, wenn Ctrl+C oder Alt+F4 (Programm beenden) gedrückt wurde
        self.gl_omxplayer = None             # Über dbus steuerbarer omxplayer
        self.gl_omxplayerListindex = -1      # globale Variable für die Routine omxplaylist initialisieren
        self.gl_omxplayerStopevent = False   # Merker für noch nicht verarbeitete Stoptaste
        self.gl_omxplayerPrevevent = False   # Merker für noch nicht verarbeitete |<<-Taste
        self.gl_omxplayerRewinding = False   # Merker für "Rewind"-Taste gedrückt
        self.gl_omxplayerForwarding = False  # Merker für "Forward"-Taste gedrückt
        self.gl_trvMediadirClickedRow = -1   # Nachbildung des Doppelklicks für Touchbildschirm
        self.gl_trvMediadirClickedTime = 0.0 # Nachbildung des Doppelklicks für Touchbildschirm
        self.gl_lstPlaylistClickedItem = -1  # Nachbildung des Doppelklicks für Touchbildschirm
        self.gl_lstPlaylistClickedTime = 0.0 # Nachbildung des Doppelklicks für Touchbildschirm
        self.gl_trvMediadirChanged = True    # für Titelsuche: True: Die Speichermedien (USB-Laufwerke) haben sich geändert und müssen daher für die Titelsuche neu eingelesen werden!
        self.gl_trvMediadirList = []         # für Titelsuche: Liste initialisieren (leer), die später alle Titel enthält
        self.gl_trvMediadirFoundChg = True   # für Titelsuche: True: Der Suchstring hat sich geändert
        self.gl_trvMediadirFoundList = []    # für Titelsuche: Liste initialisieren (leer), die später alle Suchtreffer enthält
        self.gl_trvMediadirFoundIndex = -1   # für Titelsuche: zuletzt gefundener Listeneintrag
        # die folgenden Variablen können auch über Kommandozeilenparameter gesetzt werden:
        self.gl_alphaDefault = 105           # 2016-11-20 schlizbaeda V0.2: Default für den Alpha-Wert (Transparenz) von Videos (0..255)
        self.gl_fullscreen = False           # 2016-11-20 schlizbaeda V0.2: Vollbildmodus/Fensteransicht
        self.gl_aspectMode = 'letterbox'     # 2016-11-20 schlizbaeda V0.2: "letterbox"/"fill"/"stretch"
        self.gl_keepVideoboxSize = False     # 2017-08-14 schlizbaeda V0.2: Bei einer neuen Videodatei wird die zuvor verwendete Größe beibehalten
        self.gl_VideoboxBackcolor = ''       # 2017-08-14 schlizbaeda V0.2: Hintergrundfarbe des Videofensters (wichtig/nett wegen der Transparenz!)
        self.gl_dx = 0 #48                   # 2016-11-20 schlizbaeda V0.2: X-Versatz zwischen Desktop-Fenster und omxplayer-Video (GPU)
        self.gl_dy = 0 #48                   # 2016-11-20 schlizbaeda V0.2: Y-Versatz zwischen Desktop-Fenster und omxplayer-Video (GPU)
        self.gl_audioOutput = ''             # 2017-11-25 schlizbaeda V0.2.2: Kommandozeilenparameter "-o alsa" für omxplayer
        self.gl_argvFilenames = []           # 2017-08-14 schlizbaeda V0.2: Nur die Dateinamen aus der Kommandozeile, die Optionen "-alpha" etc. wurden bereits herausgefiltert!
		
        # 2017-08-14 schlizbaeda V0.2: Kommandozeilenparameter berücksichtigen:
        argmode = -1 # den ersten Parameter argv[0] als ungültig markieren, da es der Programmname ist!
        for arg in sys.argv:
            if arg == '-alpha':
                argmode = 1 # Kommandozeilenparameter für self.gl_alphaDefault (integer)
            elif arg == '-f':
                argmode = 2 # Kommandozeilenparameter für self.gl_fullscreen (boolean)
            elif arg == '-a':
                argmode = 3 # Kommandozeilenparameter für self.gl_aspectMode (string: "letterbox"/"fill"/"stretch")
            elif arg == '-k':
                argmode = 4 # Kommandozeilenparameter für self.gl_keepVideoboxSize (boolean)
            elif arg == '-c':
                argmode = 5 # Kommandozeilenparameter für self.gl_VideoboxBackcolor (string: "black" etc.)
            elif arg == '-o':
                argmode = 6 # 2017-11-25 schlizbaeda V0.2.2: Kommandozeilenparameter für self.gl_audioOutput (string "hdmi", "local", "both", "alsa[:device]")
            elif arg == '-v':
                argmode = 7 # schlizbaeda v0.4.0: verbosity
            elif arg == '-dx':
                argmode = 16 # Kommandozeilenparameter für self.gl_dx (integer)
            elif arg == '-dy':
                argmode = 17 # Kommandozeilenparameter für self.gl_dy (integer)
            else:
                # Auswertung der Datenparameter
                if argmode == 0:
                    # es handelt sich um einen Dateinamen:
                    self.gl_argvFilenames.append(arg)
                elif argmode == 1: # -alpha
                    try:
                        self.gl_alphaDefault = int(arg)
                    except:
                        pass
                elif argmode == 2: # -f
                    try:
                        self.gl_fullscreen = bool(int(arg))
                    except:
                        pass
                elif argmode == 3: # -a
                    self.gl_aspectMode = arg.lower()
                    if self.gl_aspectMode != 'fill' and self.gl_aspectMode != 'stretch':
                        self.gl_aspectMode = 'letterbox' # wichtig, um einen sauberen Wert zu initialisieren
                elif argmode == 4: # -k
                    try:
                        self.gl_keepVideoboxSize = bool(int(arg))
                    except:
                        pass
                elif argmode == 5: # -c
                    self.gl_VideoboxBackcolor = arg.lower()
                elif argmode == 6: # -o
                    self.gl_audioOutput = arg.lower() # 2017-11-25 schlizbaeda V0.2.2
                elif argmode == 7: # -v (verbosity)
                    try:
                        self.gl_verbosity = int(arg)
                    except:
                        pass
                elif argmode == 16: # -dx
                    try:
                        self.gl_dx = int(arg)
                    except:
                        pass
                elif argmode == 17: # -dy
                    try:
                        self.gl_dy = int(arg)
                    except:
                        pass
                else:
                    # unbekannter Parametertyp: keine Aktion!
                    pass
                argmode = 0 # für den nächsten Parameter wird zunächst auf Default (Dateiname) zurückgestellt
        # Ausgabe des Hilfetextes im Terminalfenster:
        self.printTerminalHelp()
        # Debugausgabe:
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   command line parameters')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'alpha=' + str(self.gl_alphaDefault))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'full=' + str(self.gl_fullscreen))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'aspect=' + self.gl_aspectMode)
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'keep=' + str(self.gl_keepVideoboxSize))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'backCol=' + self.gl_VideoboxBackcolor)
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'audioOut=' + self.gl_audioOutput)
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'dx=' + str(self.gl_dx))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'dy=' + str(self.gl_dy))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'files=' + str(len(self.gl_argvFilenames)))
        for fn in self.gl_argvFilenames:
            self.printVerbose(self.GL_VERBOSITY_DEBUG, '    ' + fn)
		
        # init gui
        self.GUI()

    def printVerbose(self, verbosityFlag, msg, sep = ' ', end = '\n'):
        # schlizbaeda v0.4.0: Ausgabe von Meldungstexten abhängig vom eingestellten Verbosity-Level
        if verbosityFlag & self.gl_verbosity:
            print(msg, sep = sep, end = end)

    def autoplay(self):
        # schlizbaeda v0.4.0: Minimalfunktion, um die parameterbehaftete Funktion in self.GUI über .after aufzurufen
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'Autoplay:')
        self.butPlayPause_Click(None)

    def GUI(self):
        self.YAMuPlayGUI = tkinter.Tk()
        self.YAMuPlayGUI.title(self.gl_appName + ' V' + self.gl_appVer)
        
        # schlizbaeda v0.4.0: Icongrafik aus PNG-Datei erstellen:
        try:
            self.gl_appIcon = tkinter.PhotoImage(file = 'yamuplay.png') # globale Variable für Icongrafik anlegen und *.PNG-Datei einlesen/umwandeln(?)
        except:
            self.gl_appIcon = None
        if not self.gl_appIcon is None:
            self.YAMuPlayGUI.tk.call('wm', 'iconphoto', self.YAMuPlayGUI._w, self.gl_appIcon) # Icongrafik self.gl_appIcon für Hauptfenster verwenden
        
        if self.YAMuPlayGUI.winfo_screenwidth() <= 800:
            w = self.YAMuPlayGUI.winfo_screenwidth() - 8          # gesamte Bildschirmauflösung (Breite)
        else:
            w = int(self.YAMuPlayGUI.winfo_screenwidth() * 3 / 4) # 3/4 * Bildschirmauflösung (Breite)
        h = int(self.YAMuPlayGUI.winfo_screenheight() * 3 / 4)    # 3/4 * Bildschirmauflösung (Höhe)
        l = int((self.YAMuPlayGUI.winfo_screenwidth() - w) / 2)
        t = int((self.YAMuPlayGUI.winfo_screenheight() - h) / 2)
        t = int(t / 3 * 2)                                        # schlizbaeda v0.4.0: "magic" factor for small resolutions of about 800x480 like on the official Raspberry Pi touch display 7" DSI
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   screen size and resulting window geometry')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'screen:   ' + str(self.YAMuPlayGUI.winfo_screenwidth()) + 'x' + str(self.YAMuPlayGUI.winfo_screenheight()))
        #TODO: Einlesen der Fensterkoordinaten aus einer config-Datei...
        geometry = str(w) + 'x' + str(h) + '+' + str(l) + '+' + str(t) # sowas im Format wie '1280x720+0+0'
        self.printVerbose(self.GL_VERBOSITY_DEBUG, 'geometry: ' + geometry)
        self.YAMuPlayGUI.geometry(geometry)
        fontsize = 12
        self.dirFont = tkinter.font.Font(family = 'DejaVuSans', weight = 'bold', size = fontsize)
        self.fileFont = tkinter.font.Font(family = 'DejaVuSans', weight = 'normal', size = fontsize)
        self.monoFont = tkinter.font.Font(family = 'DejaVuSansMono', weight = 'normal', size = fontsize)

        # Menü erstellen:
        self.mnuMainbar = tkinter.Menu(self.YAMuPlayGUI, font = self.fileFont)
        # Menüleiste "Datei"
        self.mnuFile = tkinter.Menu(self.mnuMainbar, font = self.fileFont, tearoff = 0)
        self.mnuFile.add_command(label = 'Mediadatei öffnen', command = self.mnuFileOpen_Click)
        self.mnuFile.add_separator()
        self.mnuFile.add_command(label = 'Playlist öffnen', command = self.mnuPlaylistOpen_Click)
        self.mnuFile.add_command(label = 'Playlist speichern', command = self.mnuPlaylistSave_Click)
        self.mnuFile.add_separator()
        self.mnuFile.add_command(label = 'Beenden', command = self.onClosing)
        # Menüleiste "Ansicht"
        self.mnuView = tkinter.Menu(self.mnuMainbar, font = self.fileFont, tearoff = 0)
        self.mnuView.add_command(command = self.mnuViewFullscreen_Click) # Vollbild
        self.mnuViewFullscreen_ShowState(self.gl_fullscreen)
        self.mnuView.add_command(command = self.mnuViewAspectMode_Click) # AspectMode
        self.mnuViewAspectMode_ShowState(self.gl_aspectMode)
        self.mnuView.add_command(label = '        Hintergrundfarbe', command = self.mnuViewBackground_Click)
        self.mnuView.add_command(command = self.mnuViewKeepVideoboxSize_Click) # Videogröße automatisch anpassen
        self.mnuViewKeepVideoboxSize_ShowState(self.gl_keepVideoboxSize)
        self.mnuView.add_command(label = 'F9    voreingestellte Transparenz (' + str(self.gl_alphaDefault) + ') setzen', command = self.mnuViewSetDefaultAlpha_Click)
        self.mnuView.add_separator()
        self.mnuView.add_command(label = 'F5    Playlist bereinigen', command = self.mnuViewShowCurrentTitle_Click)

        # Menüleiste "Hilfe"
        self.mnuHelp = tkinter.Menu(self.mnuMainbar, font = self.fileFont, tearoff = 0)
        self.mnuHelp.add_command(label = 'Info', command = self.mnuHelpAbout_Click)
        # Untermenüs in die oberste Menüleiste einhängen:
        self.mnuMainbar.add_cascade(label = 'Datei', menu = self.mnuFile)
        self.mnuMainbar.add_cascade(label = 'Ansicht', menu = self.mnuView)
        self.mnuMainbar.add_cascade(label = 'Hilfe', menu = self.mnuHelp)
        # gesamte Menüleiste anzeigen:
        self.YAMuPlayGUI.config(menu = self.mnuMainbar)

        # Steuerelemente erstellen:
        # self.pwMainpane (tkinter.PanedWindow: links/rechts)
        #      self.pwMediadir (tkinter.PanedWindow: oben/unten)
        #           self.frMediadirFind (tkinter.Frame: enthält Steuerelemente (Button und Entry) für Suche)
        #           self.trvMediadir    (tkinter.ttk.Treeview)
        #      self.pwPlayer (tkinter.PanedWindow: oben/Mitte/unten)
        #           self.frPlayerbuttons (tkinter.Frame: enthält Steuerelemente für den Mediaplayer)
        #           self.progbarMedia    (tkinter.ttk.Progressbar)
        #           self.pwPlaylist      (tkinter.PanedWindow: links/rechts)
        #                self.lstPlaylist       (tkinter.Listbox: aktuelle Playlist)
        #                self.frPlaylistButtons (tkinter.Frame: enthält Steuerelemente zum Verschieben und Löschen)
        self.pwMainpane = tkinter.PanedWindow(self.YAMuPlayGUI, orient = 'horizontal', sashwidth = 16) # sashwidth=16: Breite der Trennlinie dick genug machen, um sie auf einem (groben) Touchdisplay sicher zu erreichen
        self.pwMainpane.pack(fill = 'both', expand = 'yes')

        # linke Seite von pwMainpane:
        #   oben:  Frame-Container für Dateisuche: Button "Suchen", Entry "Suchbegriff"
        #   unten: Treeview-Steuerelement, das alle USB-Laufwerke inkl. Verzeichnisstruktur auflistet
        self.pwMediadir = tkinter.PanedWindow(self.pwMainpane, orient = 'vertical', sashwidth = 0)  # sashwidth=0: Breite der Trennlinie auf 0 setzen, damit sie nicht verschoben werden kann
        # oben:
        self.frMediadirFind = tkinter.Frame(self.pwMediadir)
        self.frMediadirFind.pack(fill = 'x')
        #self.frMediadirFind.pack(anchor = 'e') # beißt nicht an!
        self.butMediadirFind = tkinter.Button(self.frMediadirFind, font = self.fileFont, text = 'suchen')
        self.butMediadirFind.pack(side = 'left')
        self.entMediadirFind = tkinter.Entry(self.frMediadirFind, font = self.fileFont)
        self.entMediadirFind.pack(side = 'left', fill = 'x', expand = 'yes')
        #TODO: #self.pwMediadir.add(self.trvMediadir, minsize = 610) # Die Höhe (610 Pixel) des Playlist-Fensters ist hier auf eine Gesamthöhe von 720 Pixeln abgestimmt
        self.pwMediadir.add(self.frMediadirFind)
        # unten:
        self.frMediadir = tkinter.Frame(self.pwMediadir)#, bg = 'yellow')
        self.frMediadir.pack(fill = 'both', expand = 'yes')
        self.ysbMediadir = tkinter.Scrollbar(self.frMediadir, orient = tkinter.VERTICAL)
        self.trvMediadir = tkinter.ttk.Treeview(self.frMediadir, show = 'tree', xscrollcommand = None, yscrollcommand = self.ysbMediadir.set) # show = 'tree': nur den Inhalt anzeigen, nicht die Überschriftsfeld(er) für die Spalten des Steuerelementes
        #self.trvMediadir.font = self.fileFont # beißt nicht an!
        self.ysbMediadir['command'] = self.trvMediadir.yview
        self.trvMediadir.pack(side = 'left', expand = 'yes', fill = 'both')
        self.ysbMediadir.pack(side = 'left', anchor = tkinter.W, fill = tkinter.Y)
        # Supertolle Wurst:
        #   mit .pack(...) lässt sich der horizontale Scrollbalken nicht unter dem anderen Schmarrn (trvMediadir+vertikaler Scrollbalken) platzieren
        #   und mit .grid() im Frame funktioniert die Ausdehnung mit expand/sticky nicht!
        #self.xsbMediadir = tkinter.Scrollbar(self.frMediadir, orient = tkinter.HORIZONTAL)
        #self.xsbMediadir.pack(side = tkinter.BOTTOM)
        #self.xsbMediadir['command'] = self.trvMediadir.xview
        self.pwMediadir.add(self.frMediadir)
        self.pwMainpane.add(self.pwMediadir)

        # rechte Seite von pwMainpane:
        # Listbox-Steuerelement mit Playlist und Schaltflächen für den Mediaplayer
        #   Zeile 1: Schaltflächen für den Mediaplayer (Play/Pause, seek, prev, next, Stop)
        #   Zeile 2: Transparenz (alpha-Wert)
        #   Zeile 3: Fortschrittsbalken für aktive Mediendatei
        #   Zeile 4: Listbox-Steuerelement (Playlist), Schaltflächen für "Verschieben" + "Entfernen"
        self.pwPlayer = tkinter.PanedWindow(self.pwMainpane, orient = 'vertical', sashwidth = 0) # sashwidth=0: Breite der Trennlinie auf 0 setzen, damit sie nicht verschoben werden kann
        self.pwPlayer.pack()#fill = 'both', expand = 'yes')
        # Zeile 1: Schaltflächen für Mediaplayer
        self.frPlayerbuttons = tkinter.Frame(self.pwPlayer)
        self.frPlayerbuttons.pack(fill = 'none')
        self.butPlayPause = tkinter.Button(self.frPlayerbuttons, font = self.monoFont)
        self.butPlayPause.pack(side = 'left')
        self.updateButPlayPause()
        self.butRewind = tkinter.Button(self.frPlayerbuttons, font = self.monoFont, text = '<< ')
        self.butRewind.pack(side = 'left')
        self.butForward = tkinter.Button(self.frPlayerbuttons, font = self.monoFont, text = ' >>')
        self.butForward.pack(side = 'left')
        self.butPrev = tkinter.Button(self.frPlayerbuttons, font = self.monoFont, text = '|<<')
        self.butPrev.pack(side = 'left')
        self.butNext = tkinter.Button(self.frPlayerbuttons, font = self.monoFont, text = '>>|')
        self.butNext.pack(side = 'left')
        self.butStop = tkinter.Button(self.frPlayerbuttons, font = self.monoFont, text = ' □ ') # '□': U+25A1(9633) / '■': U+25A0(9632) / 'Stop')
        self.butStop.pack(side = 'left')
        self.pwPlayer.add(self.frPlayerbuttons)
        # Zeile 2: Transparenz (alpha-Wert)
        self.frAlpha = tkinter.Frame(self.pwPlayer)
        self.frAlpha.pack(fill = 'none')
        self.lblAlpha = tkinter.Label(self.frAlpha, font = self.fileFont, text = 'Transparenz:')
        self.lblAlpha.grid(column = 0, row = 0) #self.lblAlpha.pack(side = 'left')
        #self.spinAlpha = tkinter.Spinbox(self.frAlpha, values = (0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255))
        self.spinAlpha = tkinter.Spinbox(self.frAlpha, width = 4, from_ = 0, to = 255, increment = 15, font = self.fileFont, command = self.spinAlpha_command) # width = Anzahl der dargestellten Zeichen        #self.spinAlpha = tkinter.Spinbox(self.frPlayerbuttons, width = 4, from_ = 0, to = 255, increment = 15, font = self.fileFont # width = Anzahl der dargestellten Zeichen
        self.spinAlpha.delete(0, tkinter.END)          # Vorbelegung löschen
        self.spinAlpha.insert(0, self.gl_alphaDefault) # und Startwert eintragen
        self.spinAlpha.grid(column = 1, row = 0, pady = 10) #self.spinAlpha.pack(side = 'left')
        self.pwPlayer.add(self.frAlpha)
        # Zeile 3: Fortschrittsbalken
        self.scaleMedia = tkinter.Scale(self.pwPlayer, from_ = 0, to_ = 100, orient = tkinter.HORIZONTAL, command = self.scaleMedia_Move)
        self.scaleMedia.pack()
        self.pwPlayer.add(self.scaleMedia)
        # Zeile 4: Playlist mit vertikaler Scrollbar und dazugehörige Schaltflächen "Verschieben" + "Entfernen":
        # --> unschön, aber bei self.pwPlaylist.add(...) bekommt immer das letzte hinzugefügte Unter-Widget den übrigen Platz (hier self.frPlaylistButtons)
        self.pwPlaylist = tkinter.PanedWindow(self.pwPlayer, orient = 'horizontal', sashwidth = 0)  # sashwidth=0: Breite der Trennlinie auf 0 setzen, damit sie nicht verschoben werden kann
        self.pwPlaylist.pack()#fill = 'both', expand = 'yes')
        self.frPlaylist = tkinter.Frame(self.pwPlaylist)#, bg = 'yellow')
        self.frPlaylist.pack(fill = 'both', expand = 'yes')
        self.ysbPlaylist = tkinter.Scrollbar(self.frPlaylist, orient = tkinter.VERTICAL)
        self.lstPlaylist = tkinter.Listbox(self.frPlaylist, font = self.fileFont, selectmode = tkinter.BROWSE, xscrollcommand = None, yscrollcommand = self.ysbPlaylist.set)
        self.ysbPlaylist['command'] = self.lstPlaylist.yview
        self.lstPlaylist.pack(side = 'left', expand = 'yes', fill = 'both')#, fill = 'both', expand = 'yes')
        self.ysbPlaylist.pack(side = 'left', anchor = tkinter.W, fill = tkinter.Y)
        # Supertolle Wurst:
        #   mit .pack(...) lässt sich der horizontale Scrollbalken nicht unter dem anderen Schmarrn (lstPlaylist+vertikaler Scrollbalken) platzieren
        #   und mit .grid() im Frame funktioniert die Ausdehnung mit expand/sticky nicht!
        #self.xsbPlaylist = tkinter.Scrollbar(self.frPlaylist, orient = tkinter.HORIZONTAL)
        #self.xsbPlaylist.pack(side = tkinter.BOTTOM)
        #self.xsbPlaylist['command'] = self.lstPlaylist.xview
        self.frPlaylistButtons = tkinter.Frame(self.pwPlaylist)
        ####self.frPlaylistButtons.pack(side = 'right', anchor = tkinter.W)
        self.frPlaylistButtons.pack(side = 'left', anchor = tkinter.E)
        self.butPlaylistMoveUp = tkinter.Button(self.frPlaylistButtons, font = self.monoFont, text = '^')
        self.butPlaylistMoveUp.pack()
        self.butPlaylistRemove = tkinter.Button(self.frPlaylistButtons, font = self.monoFont, text = 'X')
        self.butPlaylistRemove.pack()
        self.butPlaylistMoveDn = tkinter.Button(self.frPlaylistButtons, font = self.monoFont, text = 'v')
        self.butPlaylistMoveDn.pack()
        self.pwPlaylist.add(self.frPlaylist)
        
        self.pwPlayer.add(self.pwPlaylist)
        self.pwMainpane.add(self.pwPlayer)
        self.pwMainpane.sash_place(0, int(w / 3), 17) # schlizbaeda v0.4.0: Aufteilung Treeview 1/3 zu Player 2/3
        
        # weitere tkinter-Toplevel-Fenster
        self.createVideobox()
        self.createAboutbox()

        # 2017-08-14 schlizbaeda V0.2: Die als Kommandozeilenparameter angegebenen Dateien in die Playlist einfügen:
        for arg in self.gl_argvFilenames:
            try:
                filetype = magic.from_file(arg, mime=True)
            except magic.MagicException as err:
                filetype = '[ERROR] MagicException: ' + str(err.filename)
            except OSError as err:
                filetype = "[ERROR] file doesn't exist: " + str(err.filename)
            except:
                filetype = '[ERROR]'
            if filetype.startswith('audio/') or filetype.startswith('video/'):
                if arg[0:len(self.GL_PATHSEPARATOR)] != self.GL_PATHSEPARATOR: # relativer Pfad
                    arg = os.getcwd() + self.GL_PATHSEPARATOR + arg # relative Pfadangabe mit dem "current working directory" absolut machen
                self.lstPlaylist.insert(tkinter.END, arg)
            elif filetype.startswith('text/'):
                # m3u-Playlist einlesen:
                try:
                    file = open(arg, 'r')
                except IOError as err:
                    pass
                except:
                    pass
                else:
                    for line in file:
                        line = str.strip(line, ' ')  # Leerzeichen vorne und hinten abschneiden ("trim")
                        if not line.startswith('#'): # Zeilen, die mit '#' beginnen, sind m3u-Kommentarzeilen
                            self.lstPlaylist.insert(tkinter.END, line.replace('\n', ''))
                    file.close()
                
        if self.gl_argvFilenames != []:
			# Autoplay:
            #self.butPlayPause_Click(None) # So direkt funzt es nicht, das wäre zu einfach: Man muss mit .after 200ms (oder so) warten bis die "mainloop" steht. Erst dann kann Autoplay gestartet werden 
            self.YAMuPlayGUI.after(200, self.autoplay) # hier darf nicht der Funktionsaufruf mit den Klammern/Parametern stehen, sondern nur der Name, was in Python eine Art Funktionszeiger darstellt!

    def createVideobox(self):
        # Toplevel-Widget (zusätzliches tkinter-Fenster) für die Anzeige des Videos:
        self.Videobox = tkinter.Toplevel()
        if not self.gl_appIcon is None:
            self.Videobox.tk.call('wm', 'iconphoto', self.Videobox._w, self.gl_appIcon) # Icongrafik self.gl_appIcon für Videobox verwenden
        self.Videobox.withdraw()                # Toplevel-Widget unsichtbar machen
        self.Videobox.geometry('320x180+80+40') # 2017-08-14 schlizbaeda V0.2: Standardabmessungen für Kommandozeilenparameter "-k <True>"
        if self.gl_VideoboxBackcolor:           # 2017-08-14 schlizbaeda V0.2: Hintergrundfarbe einstellen
            try:
                self.Videobox.configure(background=self.gl_VideoboxBackcolor) 
            except:
                pass # Wenn die angegebene Farbbezeichnung ungültig ist, einfach nichts tun!
        self.Videobox.bind('<Destroy>', self.Videobox_Destroy)
        self.Videobox.bind('<KeyPress>', self.Videobox_KeyPress) 
        self.Videobox.bind('<Configure>', self.Videobox_Configure) 
        self.Videobox.bind('<FocusIn>', self.Videobox_FocusIn) 
        self.Videobox.bind('<FocusOut>', self.Videobox_FocusOut) 

    def createAboutbox(self):
        def but_OK():
            self.Aboutbox.withdraw()
        
        # Toplevel-Widget (zusätzliches tkinter-Fenster) "About-Dialog":
        self.Aboutbox = tkinter.Toplevel()
        if not self.gl_appIcon is None:
            self.Aboutbox.tk.call('wm', 'iconphoto', self.Aboutbox._w, self.gl_appIcon) # Icongrafik self.gl_appIcon für Videobox verwenden
        self.Aboutbox.withdraw()
        self.Aboutbox.geometry('640x336')
        self.Aboutbox.title('Info zu ' + self.gl_appName + ' V' + self.gl_appVer)
        titleFont = tkinter.font.Font(family = 'DejaVuSans', weight = 'bold', size = 16)
        normalFont = tkinter.font.Font(family = 'DejaVuSans', weight = 'normal', size = 12)
        monospaceFont = tkinter.font.Font(family = 'Monospace', weight = 'normal', size = 10)
        lblTitle = tkinter.Label(self.Aboutbox, text = self.gl_appName + ' V' + self.gl_appVer, font = titleFont)
        lblTitle.pack(pady = 10)
        lblDesc1 = tkinter.Label(self.Aboutbox, text = 'Yet Another Music Player           Version ' + self.gl_appVer, font = normalFont)
        lblDesc1.pack()
        lblDesc2 = tkinter.Label(self.Aboutbox, text = 'basierend auf omxplayer.bin, dem performanten Mediaplayer für den RaspberryPi', font = normalFont)
        lblDesc2.pack()
        #lblDesc2.pack(pady = 10)
        lblDesc3 = tkinter.Label(self.Aboutbox, text = '', font = normalFont)
        lblDesc3.pack()
        #lblDesc4 = tkinter.Label(self.Aboutbox, text = 'entwickelt von schlizbäda', font = normalFont)
        #lblDesc4.pack()
        lblDesc5 = tkinter.Label(self.Aboutbox, text = 'Copyright (C) 2016 - 2018', font = normalFont)
        lblDesc5.pack()
        lblDesc6 = tkinter.Label(self.Aboutbox, text = 'e-mail: schlizbaeda@gmx.de', font = normalFont)
        lblDesc6.pack()
        
        # schlizbaeda v0.4.0: Frame einfügen für Textbox mit Y-Scrollbalken:
        frLic = tkinter.Frame(self.Aboutbox)#, bg = 'yellow')
        lblLic = tkinter.Label(frLic, text = 'Lizenz (GNU GPL v3):', font = normalFont) # caption
        lblLic.pack(anchor = tkinter.W)
        self.txtAboutboxLic = tkinter.Text(frLic, font = monospaceFont, wrap = 'word')
        self.txtAboutboxLic.pack(side = 'left', expand = 'yes', fill = 'both')
        # create a Scrollbar and associate it with txtLic:
        ysbLic = tkinter.Scrollbar(self.txtAboutboxLic, command = self.txtAboutboxLic.yview)
        ysbLic.pack(side = 'right', anchor = tkinter.W, fill = tkinter.Y)
        self.txtAboutboxLic['yscrollcommand'] = ysbLic.set
        #####self.txtAboutboxLic.insert('1.0', GPLv3)
        frLic.pack(fill = "both", expand = True)
        
        butOK = tkinter.Button(self.Aboutbox, text = '     OK     ', command = but_OK)
        butOK.pack(pady = 5)
        ## modale AboutBox -- schlizbaeda v0.4.0: mittlerweile finde ich ein Fenster "modeless" besser
        ## Quelle: tkinter.unpythonic.net/wiki/ModalWindow
        #self.Aboutbox.transient(self.YAMuPlayGUI)   # 1. Notwendigkeit für ein modales Fenster
        #self.Aboutbox.grab_set()                    # 2. Notwendigkeit für ein modales Fenster
        #self.YAMuPlayGUI.wait_window(self.Aboutbox) # 3. Notwendigkeit für ein modales Fenster
        pass



    ##### Funktionen für omxplayer-Aufruf #####
    def omxplayerDebugPrint(self):
        """
        2016-11-20 schlizbaeda V0.2: "Spielwiese" für omxplayer-DBus-Kommandos
        
        Diese Funktion wird bei Drücken von F2 aufgerufen und dient dazu,
        beliebige Tests für die omxplayer-Kommunikation einzufügen...
        Die lokale Variable ***showDebugMessages*** dient zum schnellen
        Aktivieren und Deaktivieren der Debuganweisungen
        """
        # Durch Übergabe von self.gl_verbosity als Funktionsparameter
        # werden die Debugmeldungen IMMER angezeigt,
        # egal welche Verbosity-Flags gesetzt sind.
        # Nur bei gl_verbosity == 0 wird nichts angezeigt.
        self.printVerbose(self.gl_verbosity, '')
        self.printVerbose(self.gl_verbosity, '[DEBUG]   F2: user debug messages')
        self.printVerbose(self.gl_verbosity, 'argv-files: ' + str(len(self.gl_argvFilenames)))
        for arg in self.gl_argvFilenames:
            #magicNumber = magic.Magic(mime=True) # Variante: Mit Klasse arbeiten, hier Aufruf des Konstruktors
            try:
                filetype = magic.from_file(arg, mime=True)
                #filetype = magic.from_buffer(open(arg).read(1024), mime=True)
            except magic.MagicException as err:
                filetype = '[ERROR] MagicException: ' + str(err.filename)
            except OSError as err:
                filetype = "[ERROR] file doesn't exist: " + str(err.filename)
            except:
                filetype = '[ERROR]'
            msg = '  ' + filetype + '  ' + arg
            self.printVerbose(self.gl_verbosity, msg)
        
        self.printVerbose(self.gl_verbosity, '')
        self.printVerbose(self.gl_verbosity, 'S c r e e n  geometry=' + str(self.YAMuPlayGUI.winfo_screenwidth()) + 'x' + str(self.YAMuPlayGUI.winfo_screenheight()))
        self.printVerbose(self.gl_verbosity, 'YAMuPlayGUI  geometry=' + str(self.YAMuPlayGUI.winfo_geometry()))
        self.printVerbose(self.gl_verbosity, 'Videobox     geometry=' + str(self.Videobox.winfo_geometry()))
        if not self.gl_omxplayer is None:
            ## "Einfache Variante": Direkte Funktionsaufrufe aus willprice/python-omxplayer-wrapper/omxplayer/player.py
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.can_quit=' + str(self.gl_omxplayer.can_quit()))
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.get_source=' + str(self.gl_omxplayer.get_source()))
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.volume=' + str(self.gl_omxplayer.volume()))
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.audio=' + str(self.gl_omxplayer.audio()))
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.video=' + str(self.gl_omxplayer.video()))
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.MaximumRate=' + str(self.gl_omxplayer.maximum_rate()))

            ## "Schwierige Variante": "Generische" Aufrufe von omxplayer-DBus-Kommandos
            ## Quelle: https://github.com/popcornmix/omxplayer (in README.md, Überschrift "DBUS CONTROL")
            ## Root-Interface:   DBus-Namaspace: org.mpris.MediaPlayer2
            ##                   Methoden:       org.mpris.MediaPlayer2.MethodName
            ##                   Eigenschaften:  org.freedesktop.DBus.Properties.Get bzw. org.freedesktop.DBus.Properties.Set
            ## Player-Interface: DBus-Namespace: org.mpris.MediaPlayer2.Player
            ##                   Methoden:       org.mpris.MediaPlayer2.Player.MethodName
            ##                   Eigenschaften:  org.freedesktop.DBus.Properties.Get bzw. org.freedesktop.DBus.Properties.Set (offenbar gleich wie beim Root-Interface)
            ##
            ## Es bestehen für das Player-Interface "generische" Aufrufmöglichkeiten, falls notwendige Definitionen in python-omxplayer-wrapper fehlen:
            ##    self.gl_omxplayer._get_root_interface().CanQuit()        # Eigenschaft aus dem Root-Interface
            ##    self.gl_omxplayer._get_properties_interface().ResWidth() # Eigenschaft aus dem Player-Interface
            ##    self.gl_omxplayer._get_properties_interface().Mute()     # Methode aus dem Player-Interface
            self.printVerbose(self.gl_verbosity, '    gl_omxplayer.width= ' + str(self.gl_omxplayer_GetWidth()))  #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.width=' + str(self.gl_omxplayer.width()))   #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.ResWidth (generic)=' + str(self.gl_omxplayer._get_properties_interface().ResWidth()))   # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methode ._get_properties_interface().ResWidth() durch offizielle Methode .width() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
            self.printVerbose(self.gl_verbosity, '    gl_omxplayer.height=' + str(self.gl_omxplayer_GetHeight())) #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.height=' + str(self.gl_omxplayer.height())) #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.ResHeight (generic)=' + str(self.gl_omxplayer._get_properties_interface().ResHeight())) # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methode ._get_properties_interface().ResHeight() durch offizielle Methode .height() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.Aspect (generic)=' + str(self.gl_omxplayer._get_properties_interface().Aspect()))
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.Fullscreen (generic)=' + str(self.gl_omxplayer._get_properties_interface().Fullscreen()))
            #self.printVerbose(self.gl_verbosity, '    gl_omxplayer.CanSetFullscreen (generic)=' + str(self.gl_omxplayer._get_properties_interface().CanSetFullscreen()))
            pass
       
    def omxplayerAdjustToplevel(self):
        # 2016-11-20 schlizbaeda V0.2: Anpassen der Fenstergröße an die Videogröße:
        self.printVerbose(self.GL_VERBOSITY_OMXPLAYER, '[OMX]     omxplayerAdjustToplevel')
        geometry = ''
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            screenW = self.Videobox.winfo_screenwidth()
            screenH = self.Videobox.winfo_screenheight()
            w = self.gl_omxplayer_GetWidth()  #w = self.gl_omxplayer.width()  #w = self.gl_omxplayer._get_properties_interface().ResWidth()  # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methode ._get_properties_interface().ResWidth() durch offizielle Methode .width() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
            h = self.gl_omxplayer_GetHeight() #h = self.gl_omxplayer.height() #h = self.gl_omxplayer._get_properties_interface().ResHeight() # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methode ._get_properties_interface().ResHeight() durch offizielle Methode .height() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
            scale = 1.0
            if w + h + self.gl_omxplayer_GetAspect() > 0.0: #if w + h + self.gl_omxplayer.aspect_ratio() > 0.0: #if w + h + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methode ._get_properties_interface().Aspect() durch offizielle Methode .aspect_ratio() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
                # Es handelt sich um ein Video, weil die Videoabmessungen > 0 sind (Für MP3-Audiodateien liefert omxplayer.bin width=0, height=0, aspect_ratio=0.0)
                if not self.gl_keepVideoboxSize:
                    while w * 1.25 > screenW or h * 1.25 > screenH:
                        w *= 0.8
                        h *= 0.8
                        scale *= 0.8
                    geometry = str(int(w)) + 'x' + str(int(h)) + '+' + str(int((screenW - w) / 2)) + '+' + str(int((screenH - h) / 2))
                    self.Videobox.geometry(geometry)
                    self.printVerbose(self.GL_VERBOSITY_RECEIVE, '[OMXrecv] Window size adjusted to video (' + str(int(scale * 100)) + '%): ' + geometry)
            else:
                # Es handelt sich um eine Audiodatei:
                self.Videobox.withdraw() # Toplevel-Widget unsichtbar machen
        return geometry
        
    def omxplayerFitToplevel(self):
        # 2016-11-20 schlizbaeda V0.2: Das Video in das bestehende Fenster größenmäßig einfügen:
        self.printVerbose(self.GL_VERBOSITY_OMXPLAYER, '[OMX]     omxplayerFitToplevel') 
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            if self.gl_omxplayer_GetWidth() + self.gl_omxplayer_GetHeight() + self.gl_omxplayer_GetAspect() > 0.0: #if self.gl_omxplayer.width() + self.gl_omxplayer.height() + self.gl_omxplayer.aspect_ratio() > 0.0: #if self.gl_omxplayer._get_properties_interface().ResWidth() + self.gl_omxplayer._get_properties_interface().ResHeight() + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methoden ._get_properties_interface().*() durch offizielle Methoden .*() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
                # Es handelt sich um ein Video, weil die Videoabmessungen > 0 sind (Für MP3-Audiodateien liefert omxplayer.bin width=0, height=0, aspect_ratio=0.0)
                if 'iconic' == self.Videobox.state():
                    # Die Videobox wurde minimiert:
                    # Video links oben über der Himbeere anzeigen:
                    self.omxplayerIconify()
                else:
                    # Die Videobox wurde nicht minimiert:
                    self.Videobox.deiconify()
                    self.Videobox.title(self.gl_omxplayer.get_source() + ' [' + self.gl_aspectMode + ']')
                    coord = self.Videobox.winfo_geometry().split('+')
                    sizes = coord[0].split('x')
                    coord[1] = int(coord[1]) + self.gl_dx
                    coord[2] = int(coord[2]) + self.gl_dy
                    self.gl_omxplayer.set_video_pos(coord[1], coord[2], coord[1] + int(sizes[0]), coord[2] + int(sizes[1]))

    def omxplayerIconify(self):
        # schlizbaeda v0.4.0: Video bei minimierter Videobox links oben über der Himbeere anzeigen:
        self.printVerbose(self.GL_VERBOSITY_OMXPLAYER, '[OMX]     omxplayerIconify') 
        x = 1 + self.gl_dx
        y = 1 + self.gl_dy
        w = 48
        h = 48
        self.gl_omxplayer.set_video_pos(x, y, x + w, y + h)

    def updateButPlayPause(self):
        if self.gl_omxplayer is None:
            playing = False
        else:
            playing = self.gl_omxplayer.playback_status() == 'Playing'

        if  playing == True:
            self.butPlayPause.config(text = '|| ')
        else:
            self.butPlayPause.config(text = ' > ')
        try:
            self.YAMuPlayGUI.update() # DoEvents
        except:
            pass
        # 2016-11-20 schlizbaeda V0.2: Playlist auf den aktuell gespielten Titel aktualisieren
        try:
            self.lstPlaylist.select_clear(0, tkinter.END)           # alle Markierungen in der Playlist löschen
            self.lstPlaylist.select_set(self.gl_omxplayerListindex) # aktuellen Titel in der Playlist anzeigen (selektieren)
            self.lstPlaylist.see(self.gl_omxplayerListindex)
        except:
            pass     
        
    def omxplayerRestart(self, file):
        self.printVerbose(self.GL_VERBOSITY_OMXPLAYER, '[OMX]     omxplayerRestart') 
        try:
            alpha = int(self.spinAlpha.get())
        except:
            alpha = self.gl_alphaDefault
        if alpha > 255:
            alpha = 255
        elif alpha < 0:
            alpha = 0
        self.spinAlpha.delete(0, tkinter.END)
        self.spinAlpha.insert(0, alpha)
        # 1. Prüfen, ob omxplayer bereits läuft:
        time.sleep(0.05) #v0.3.1: wichtig für self.gl_omxplayer.quit(), um zu verhindern, dass der omxplayer-Unterprozess so gach hängt, dass nicht einmal mehr ein (externer) kill -9 hilft!
        if not self.gl_omxplayer is None:
            self.gl_omxplayer.quit()
            self.gl_omxplayer = None
            try:
                self.YAMuPlayGUI.update() # DoEvents
            except:
                pass
        # 2. Neue omxplayer-Instanz erstellen und die Wiedergabe der angegebenen Datei starten:
        playing = False
        starttim = time.time() # Vergangene Sekunden seit dem 01. Januar 1970
        while playing == False:
            # Diese Schleife ist notwendig, da der omxplayer manchmal
            # beim Start eines Titels "Zeile 67:  <pid> Abgebrochen" meldet.
            # In diesem Falle würde sofort zum übernächsten Titel gesprungen werden,
            # was für den unbedarften Benutzer nicht nachvollziehbar ist!
            omxplayer_cmdlin = [] # 2017-11-25 schlizbaeda V0.2.2: AudioOutput übergeben
            if self.gl_audioOutput:
                # 2017-11-25 schlizbaeda V0.2.2: Kommandozeilenparameter -o nur verwenden, wenn er wirklich existiert!
                omxplayer_cmdlin.append('-o')
                omxplayer_cmdlin.append(self.gl_audioOutput)
            omxplayer_cmdlin.extend(['--alpha', str(alpha), '--aspect-mode', self.gl_aspectMode])
            self.printVerbose(self.GL_VERBOSITY_OMXPLAYER, '[OMXsend] cmdlin=' + str(omxplayer_cmdlin))
            try:
                self.gl_omxplayer = OMXPlayer(file, omxplayer_cmdlin) # 2017-11-25 schlizbaeda V0.2.2
            except SystemError: #v0.3.1: AUSLÖSENDE EXCEPTION für den Hänger der omxplayer-Unterprozesse
                 #self.printVerbose(self.GL_VERBOSITY_ERROR, '[ERROR]   v0.3.1: SystemError (shice!)')
                 time.sleep(0.05) #v0.3.1: wichtig für self.gl_omxplayer.quit(), um zu verhindern, dass der omxplayer-Unterprozess so gach hängt, dass nicht einmal mehr ein (externer) kill -9 hilft!
                 self.gl_omxplayer.quit() #v0.3.1: Beißt evtl nicht an... Dann braucht's einen kill -9 (oder so)
                 elf.gl_omxplayer = None
            except:
                # Diese allgemeine Exception tritt auf, wenn z.B. eine ungültige Mediadatei aufgerufen wird
                self.printVerbose(self.GL_VERBOSITY_ERROR, '[ERROR]   Fehler beim Laden der Datei ' + file)
                time.sleep(0.05) #v0.3.1: wichtig für self.gl_omxplayer.quit(), um zu verhindern, dass der omxplayer-Unterprozess so gach hängt, dass nicht einmal mehr ein (externer) kill -9 hilft!
                self.gl_omxplayer.quit()
                self.gl_omxplayer = None
            if self.gl_omxplayer is None:
                playing = False
            else:
                self.omxplayerAdjustToplevel() # 2016-11-20 schlizbaeda V0.2: Anpassen des Videofensters auf die Videogröße
                if not self.gl_fullscreen:
                    # Das Video soll in der Fensteransicht dargestellt werden:
                    self.omxplayerFitToplevel()
                try:
                    txt = self.gl_omxplayer.playback_status()
                except:
                    txt = ''
                playing = txt == 'Playing' or txt == 'Paused'
                time.sleep(0.05) # 2016-11-20 schlizbaeda V0.2: Diese kurze Wartezeit ist notwendig, damit self.gl_omxplayer.play() wie gewünscht anbeißt. Sonst startet der omxplayer.bin (zumindest bei MP3's) mit "Pause", nicht jedoch bei Filmen (verstehe ich nicht wirklich, aber es hilft: Die Mindestwartezeit beträgt am RPi2 0.02s)
                self.gl_omxplayer.play()
            # Timeout berücksichtigen:    
            tim = time.time()
            if tim - starttim >= 2.5:
                playing = True # Schleife immer verlassen, wenn die Datei nach 2,5s immer noch nicht abgespielt wird
        self.updateButPlayPause()
                
    def omxplaylist(self):
        self.printVerbose(self.GL_VERBOSITY_OMXPLAYER, '[OMX]     omxplaylist')
        try:
            self.gl_omxplayerListindex = int(self.lstPlaylist.curselection()[0]) # nullbasierend
        except:
            self.gl_omxplayerListindex = -1000000 # WICHTIG: Nicht -1 verwenden, da bei rekursiven Aufrufen aufgrund von Ereignissen der Wert sonst schnell über 0 rutschen kann und dann fängt die Playlist von vorne an! 1000000 Klick-Ereignisse muss man als Anwender in kurzer Zeit erst mal schaffen :-)

        while self.gl_omxplayerListindex >= 0 and self.gl_quit == 0:
            self.printVerbose(self.GL_VERBOSITY_NORMAL, '')
            self.printVerbose(self.GL_VERBOSITY_NORMAL, 'Title ' + str(self.gl_omxplayerListindex) + ': "' + self.lstPlaylist.get(self.gl_omxplayerListindex) + '"')
            try:
                filetype = magic.from_file(self.lstPlaylist.get(self.gl_omxplayerListindex), mime=True)
            except magic.MagicException as err:
                filetype = '[ERROR] MagicException: ' + str(err.filename)
            except OSError as err:
                filetype = "[ERROR] file doesn't exist: " + str(err.filename)
            except:
                filetype = '[ERROR]'
            if filetype.startswith('[ERROR]'):
                # Der aktuelle Titel ist fehlerhaft:
                self.printVerbose(self.GL_VERBOSITY_WARNING, '[WARN]    ' + filetype[8:]) # '[ERROR] ' aus dem Fehlerstring entfernen
            elif filetype.startswith('audio/') or filetype.startswith('video/'):
                # Der aktuelle Titel ist eine gültige Audiodatei oder eine Videodatei:
                self.omxplayerRestart(self.lstPlaylist.get(self.gl_omxplayerListindex)) # 2017-08-14 schlizbaeda V0.2: In der aktiven Playlist steht ab jetzt immer der KOMPLETTE Pfad (inkl. self.gl_MediaDir "/media/pi") drin!
                playing = True
                while playing == True and self.gl_quit == 0:
                    try:
                        self.YAMuPlayGUI.update() # DoEvents
                    except:
                        pass
                    time.sleep(0.05)
                    if self.gl_omxplayer is None:
                        playing = False
                    else:    
                        try:
                            txt = str(self.gl_omxplayer.playback_status())
                        except:
                            txt = 'None'
                        playing = txt == 'Playing' or txt == 'Paused'
            else:
                # Der aktuelle Titel ist eine andere Datei:
                self.printVerbose(self.GL_VERBOSITY_NORMAL, 'TODO: Dateityp=' + filetype)
            # Nächsten Eintrag aus der Playlist holen:
            self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen löschen
            if self.gl_omxplayerPrevevent == True:
                self.gl_omxplayerPrevevent = False
            else:
                self.gl_omxplayerListindex += 1
            self.lstPlaylist.select_set(self.gl_omxplayerListindex)
            self.lstPlaylist.see(self.gl_omxplayerListindex)
            
            try:
                self.gl_omxplayerListindex = int(self.lstPlaylist.curselection()[0]) # nullbasierend
            except:
                self.gl_omxplayerListindex = -1000000 # WICHTIG: Nicht -1 verwenden, da bei rekursiven Aufrufen aufgrund von Ereignissen der Wert sonst schnell über 0 rutschen kann und dann fängt die Playlist von vorne an! 1000000 Klick-Ereignisse muss man als Anwender in kurzer Zeit erst mal schaffen :-)
            if self.gl_omxplayerStopevent == True:
                self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen löschen
                self.gl_omxplayerListindex = -1000000 # WICHTIG: Nicht -1 verwenden, da bei rekursiven Aufrufen aufgrund von Ereignissen der Wert sonst schnell über 0 rutschen kann und dann fängt die Playlist von vorne an! 1000000 Klick-Ereignisse muss man als Anwender in kurzer Zeit erst mal schaffen :-)
        # Wenn das Programm hierher kommt, wurde die Playlist komplett abgespielt:
        self.gl_omxplayerStopevent = False # Merker für Stoptaste zurücksetzen
        self.gl_omxplayerPrevevent = False # Merker für |<<-Taste zurücksetzen
        time.sleep(0.05) #v0.3.1: wichtig für self.gl_omxplayer.quit(), um zu verhindern, dass der omxplayer-Unterprozess so gach hängt, dass nicht einmal mehr ein (externer) kill -9 hilft!
        if not self.gl_omxplayer is None:
            # Dieser if-Zweig wird nur ausgeführt, wenn diese def-Funktion aufgerufen wurde und die Playlist leer ist.
            try: #v0.3.1: Hier kann es beim Schließen des Programms zu einem "AttributeError" kommen, wenn noch eine Playlist läuft
                self.gl_omxplayer.quit()
            except AttributeError:
                pass
            self.gl_omxplayer = None
        self.updateButPlayPause() # Wenn die Playlist zu Ende ist, muss die Schaltfläche butPlayPause aktualisiert werden

    # 2017-09-20 schlizbaeda V0.2.1:
    # Hilfsfunktionen, da sich in künftigen Versionen des Moduls python-omxplayer-wrapper die folgenden Methoden ändern werden:
    #if self.gl_omxplayer._get_properties_interface().ResWidth() + self.gl_omxplayer._get_properties_interface().ResHeight() + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methoden ._get_properties_interface().*() durch offizielle Methoden .*() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
    def gl_omxplayer_GetAspect(self):
        #return self.gl_omxplayer._get_properties_interface().Aspect()    # inoffizielle Methode bis python-omxplayer-wrapper V0.2.3-py3.5		
        return self.gl_omxplayer.aspect_ratio()                         # offizielle Methode für künftige Versionen von python-omxplayer-wrapper

    def gl_omxplayer_GetHeight(self):                            
        #return self.gl_omxplayer._get_properties_interface().ResHeight() # inoffizielle Methode bis python-omxplayer-wrapper V0.2.3-py3.5
        return self.gl_omxplayer.height()                               # offizielle Methode für künftige Versionen von python-omxplayer-wrapper
		
    def gl_omxplayer_GetWidth(self):
        #return self.gl_omxplayer._get_properties_interface().ResWidth()  # inoffizielle Methode bis python-omxplayer-wrapper V0.2.3-py3.5
        return self.gl_omxplayer.width()                                # offizielle Methode für künftige Versionen von python-omxplayer-wrapper
        

    ##### Ereignishandler für omxplayer-Steuerung #####
    # Teil 1: Schaltflächen analog zu einem CD-Player
    def butPlayPause_Click(self, event):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butPlayPause_Click')
        if self.gl_omxplayer is None:
            # omxplayer läuft nicht:
            if len(self.lstPlaylist.curselection()) <= 0:
                # Wenn die Playlist abgeschlossen ist bzw. gerade nicht läuft, wird sie neu gestartet.
                # in der aktuellen Playlist ist nichts ausgewählt:
                self.lstPlaylist.select_set(0) # den ersten Titel auswählen
                self.lstPlaylist.see(0)
            self.omxplaylist()
        else:
            # omxplayer läuft:
            self.gl_omxplayer.play_pause()
            self.updateButPlayPause() 

    def butPrev_Click(self, event):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butPrev_Click')
        if self.gl_omxplayer is None:
            # omxplayer läuft nicht:
            if len(self.lstPlaylist.curselection()) <= 0:
                idx = int(self.lstPlaylist.size()) # letztes Element der Playlist wählen
            else:
                idx = int(self.lstPlaylist.curselection()[0])
            if idx > 0:
                idx -= 1
            self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen löschen
            self.lstPlaylist.select_set(idx)
            self.lstPlaylist.see(idx)
        else:
            # omxplayer läuft:
            self.gl_omxplayerPrevevent = True # bewirkt Berücksichtigung der |<<-Taste in der Funktion omxplaylist()
            if self.gl_omxplayer.position() <= 3.0:
                self.gl_omxplayerListindex -= 1
            self.gl_omxplayer.stop() # aktuellen Titel beenden (und in der Playlist fortfahren)
        if self.gl_omxplayerListindex < 0:
            self.gl_omxplayerListindex = 0

    def butNext_Click(self, event):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butNext_Click')
        if self.gl_omxplayer is None:
            # omxplayer läuft nicht:
            if len(self.lstPlaylist.curselection()) <= 0:
                idx = -1 # erstes Element der Playlist wählen
            else:
                idx = int(self.lstPlaylist.curselection()[0])
            if idx < int(self.lstPlaylist.size()) - 1:
                idx += 1
            self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen löschen
            self.lstPlaylist.select_set(idx)
            self.lstPlaylist.see(idx)
        else:
            # omxplayer läuft:
            self.gl_omxplayer.stop() # aktuellen Titel beenden (und in der Playlist fortfahren)

    def butRewind_ButtonPress(self, event): # entspricht Drücken der Taste
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butRewind_ButtonPress')
        self.gl_omxplayerRewinding = True
        self.gl_omxplayerForwarding = False
        starttim = time.time()
        delta = 0.5
        deltamax = 6.0 if self.gl_omxplayer is None else self.gl_omxplayer.duration() / 25
        if deltamax < 6.0: deltamax = 6.0 # mindestens 6 Sekunden springen
        while self.gl_omxplayerRewinding == True:
            if self.gl_omxplayer is None:
                # omxplayer läuft nicht:
                self.gl_omxplayerRewinding = False # while-Schleife beenden
            else:
                # omxplayer läuft:
                tim = time.time()
                if tim - starttim > 3.0:
                    delta = deltamax 
                elif tim - starttim > 1.5:
                    delta = 5.0
                elif tim - starttim > 0.75:
                    delta = 1.5
                pos = self.gl_omxplayer.position() - delta
                if pos <= 0.0:
                    pos = 0.0
                    self.gl_omxplayerRewinding = False # while-Schleife beenden
                self.gl_omxplayer.set_position(pos)
                self.printVerbose(self.GL_VERBOSITY_NORMAL, '  << ' + str(delta))
                time.sleep(0.1)
                try:
                    self.YAMuPlayGUI.update() # DoEvents
                except:
                    pass
        
    def butRewind_ButtonRelease(self, event): # entspricht Loslassen der Taste
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butRewind_ButtonRelease')
        self.gl_omxplayerRewinding = False
        self.gl_omxplayerForwarding = False

    def butForward_ButtonPress(self, event):# entspricht Drücken der Taste
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butForward_ButtonPress')
        self.gl_omxplayerRewinding = False
        self.gl_omxplayerForwarding = True
        starttim = time.time()
        delta = 0.5
        if self.gl_omxplayer is None:
            # omxplayer läuft nicht:
            duration = 0.0
            deltamax = 6.0
        else:
            # omxplayer läuft:
            duration = self.gl_omxplayer.duration() - 0.01 # Sprungziel minimal vor dem Ende der Mediendatei!
            deltamax = duration / 25
            if deltamax < 6.0: deltamax = 6.0 # mindestens 6 Sekunden springen
        while self.gl_omxplayerForwarding == True:
            if self.gl_omxplayer is None:
                # omxplayer läuft nicht:
                self.gl_omxplayerForwarding = False # while-Schleife beenden
            else:
                # omxplayer läuft:
                tim = time.time()
                if tim - starttim > 3.0:
                    delta = deltamax 
                elif tim - starttim > 1.5:
                    delta = 5.0
                elif tim - starttim > 0.75:
                    delta = 1.5
                pos = self.gl_omxplayer.position() + delta
                if pos >= duration:
                    # Hier muss überprüft werden, dass sich das Sprungziel
                    # nicht hinter der Gesamtdauer des Titels befindet,
                    # da sonst der omxplayer bei MP3-Dateien häufig nicht
                    # mehr richtig reagiert.
                    pos = duration
                    self.gl_omxplayerForwarding = False # while-Schleife beenden
                self.gl_omxplayer.set_position(pos)
                self.printVerbose(self.GL_VERBOSITY_NORMAL, '  >> ' + str(delta))
                time.sleep(0.1)
                try:
                    self.YAMuPlayGUI.update() # DoEvents
                except:
                    pass
        
    def butForward_ButtonRelease(self, event): # entspricht Loslassen der Taste
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butForward_ButtonRelease')
        self.gl_omxplayerRewinding = False
        self.gl_omxplayerForwarding = False

    def butStop_Click(self, event):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butStop_Click')
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            self.gl_omxplayerStopevent = True # bewirkt komplettes Ende der Playlist
            self.gl_omxplayer.stop()          # beendet die Wiedergabe des aktuellen Titels
            
    def spinAlpha_command(self):
        # 2016-11-20 schlizbaeda v0.2: Ereignishandler für das allgemeine command-Ereignis aus dem "Konstruktor" von spinAlpha
        alpha = self.spinAlpha.get()
        if alpha == '': alpha = '0'
        try:
            alpha = int(alpha)
        except:
            alpha = self.gl_alphaDefault
        if alpha > 255:
            alpha = 255
        elif alpha < 0:
            alpha = 0
        # Das Setzen des Alpha-Wertes (Transparenz) ist nur bei Videos möglich. Audiodateien werfen eine Exception --> daher abfangen
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'spinAlpha_command: alpha=' + str(alpha))
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            if self.gl_omxplayer_GetWidth() + self.gl_omxplayer_GetHeight() + self.gl_omxplayer_GetAspect() > 0.0: #if self.gl_omxplayer.width() + self.gl_omxplayer.height() + self.gl_omxplayer.aspect_ratio() > 0.0: #if self.gl_omxplayer._get_properties_interface().ResWidth() + self.gl_omxplayer._get_properties_interface().ResHeight() + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methoden ._get_properties_interface().*() durch offizielle Methoden .*() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
                # Es handelt sich um ein Video, weil die Videoabmessungen > 0 sind (Für MP3-Audiodateien liefert omxplayer.bin ResWidth=0, ResHeight=0, Aspect=0.0)
                self.gl_omxplayer.set_alpha(alpha) # Alpha-Wert (Transparenz) über dbus ändern
                self.printVerbose(self.GL_VERBOSITY_OMXPLAYER, '[OMXsend] set_alpha(' + str(alpha) + ')')
		
    def spinAlpha_KeyRelease(self, event): 
        # 2016-11-20 schlizbaeda V0.2: Ereignishandler für Änderung des Alpha-Wertes (Transparenz) über die Tastatur (Loslassen): Zu diesem Zeitpunkt ist der Textinhalt des Steuerelementes bereits aktualisiert!
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'spinAlpha_KeyRelease: ' + str(event))
        self.spinAlpha_command()

    # Fortschrittsbalken für aktuelle Mediadatei:
    def scaleMedia_Move(self, value):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'TODO: scaleMedia_Move(value=' + str(value) + ')')


    # Teil 2: Steuerung über die Playlist
    def lstPlaylist_Release(self, event): # --> Dient hier der Nachbildung eines toleranten Doppelklick-Ereignisses für Touchdisplays.
        # Im Release-Ereignis sind die Selektionen eines Listbox-Elementes aktuell,
        # was beim Button-Ereignis (Klick) noch nicht der Fall ist. Die Selektion
        # wird erst danach aktualisiert.
        try:
            self.YAMuPlayGUI.update() # DoEvents
        except:
            pass
        clickedTime = time.time()
        try:
            clickedItem = int(self.lstPlaylist.curselection()[0]) # nullbasierend
        except:
            clickedItem = -1
        if clickedItem >= 0 and clickedItem == self.gl_lstPlaylistClickedItem and clickedTime - self.gl_lstPlaylistClickedTime < 1.0:
            # die beiden letzten Klicks trafen das gleiche Listenelement innerhalb von 1 Sekunde:
            # Doppelklick!
            self.gl_lstPlaylistClickedItem = -1
            self.gl_lstPlaylistClickedTime = 0.0
            self.printVerbose(self.GL_VERBOSITY_NORMAL, 'lstPlaylist_Release: double click recognized')
            self.omxplaylist()
        else:
            # "erster" Klick: angeklicktes Element und Zeitpunkt merken
            self.gl_lstPlaylistClickedTime = clickedTime
            self.gl_lstPlaylistClickedItem = clickedItem
            self.printVerbose(self.GL_VERBOSITY_NORMAL, 'lstPlaylist_Release: first click recognized')
    
    ##### Ereignishandler des Treeview-Steuerelementes            #####
    ##### und der Playlist ("Verschieben", "Löschen", Drag+Drop)  #####
    def trvMediadir_Click(self, event): # --> Dient hier der Nachbildung eines toleranten Doppelklick-Ereignisses für Touchdisplays.
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'trvMediadir_Click')
        try:
            self.YAMuPlayGUI.update() # DoEvents
        except:
            pass
        clickedTime = time.time()
        try:
            clickedRow = self.trvMediadir.identify_row(event.y)
        except:
            clickedRow = ''
        if clickedRow != '' and clickedRow == self.gl_trvMediadirClickedRow and clickedTime - self.gl_trvMediadirClickedTime < 1.5:
            # die beiden letzten Klicks trafen das gleiche Treeview-Element innerhalb von 1,5 Sekunden:
            # Doppelklick!
            for sel in self.trvMediadir.selection():
                # Fallunterscheidung 'dir' oder 'fil'
                if self.trvMediadir.tag_has('dir', sel) == True:
                    # Verzeichnis (Directory):
                    self.printVerbose(self.GL_VERBOSITY_NORMAL, '  ' + sel + ' is a directory.')
                    pass
                else:
                    # normale Datei:
                    #self.lstPlaylist.insert(tkinter.END, sel) # alte Variante
                    self.lstPlaylist.insert(tkinter.END, self.gl_MediaDir + self.GL_PATHSEPARATOR + sel) # 2017-08-14 schlizbaeda V0.2: Den unvollständigen Pfad im Treeview-Steuerelement um self.gl_MediaDir ("/media/pi") erweitern
        else:
            # "erster" Klick: angeklicktes Element und Zeitpunkt merken
            self.gl_trvMediadirClickedTime = clickedTime
            self.gl_trvMediadirClickedRow = clickedRow

    def trvMediadir_ButtonRelease(self, event): # --> Dient hier der Nachbildung von "Drop" für Drag+Drop von trvMediadir nach lstPlaylist:
        def Add2Playlist(fil, idx):
            # angegebene Datei in der Playlist hinzufügen:
            self.lstPlaylist.insert(idx, fil)              # 2017-08-14 schlizbaeda V0.2: Den unvollständigen Pfad im Treeview-Steuerelement um self.gl_MediaDir ("/media/pi") erweitern
            self.lstPlaylist.select_clear(0, tkinter.END)  # alle Markierungen löschen
            self.lstPlaylist.select_set(idx)               # eingefügten Titel wählen
            self.lstPlaylist.see(idx)                      # eingefügten Titel ins Bildfeld scrollen
        
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'trvMediadir_ButtonRelease')
        xMediadir = self.pwMediadir.winfo_x() + self.trvMediadir.winfo_x()
        yMediadir = self.pwMediadir.winfo_y() + self.trvMediadir.winfo_y()
        xPlaylist = self.pwPlayer.winfo_x() + self.pwPlaylist.winfo_x()  + self.lstPlaylist.winfo_x() - self.frAlpha.winfo_x()
        yPlaylist = self.pwPlayer.winfo_y() + self.pwPlaylist.winfo_y()  + self.lstPlaylist.winfo_y() - self.frAlpha.winfo_y()
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   trvMediadir_ButtonRelease')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  RELEASE')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  trvMediadir abs:  x=' + str(xMediadir) + ', y=' + str(yMediadir) + ', width=' + str(self.trvMediadir.winfo_width()) + ', height=' + str(self.trvMediadir.winfo_height()))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '              rel:  x=' + str(self.trvMediadir.winfo_x()) + ', y=' + str(self.trvMediadir.winfo_y()))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  lstPlaylist abs:  x=' + str(xPlaylist) + ', y=' + str(yPlaylist) + ', width=' + str(self.lstPlaylist.winfo_width()) + ', height=' + str(self.lstPlaylist.winfo_height()))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '              rel:  x=' + str(self.lstPlaylist.winfo_x()) + ', y=' + str(self.lstPlaylist.winfo_y()))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  event             x=' + str(event.x) + ', y=' + str(event.y))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  event@lstPlaylist x=' + str(event.x - xPlaylist + xMediadir) + ', y=' + str(event.y - yPlaylist + yMediadir))
        if event.x >= xPlaylist - xMediadir and event.x < xPlaylist - xMediadir + self.lstPlaylist.winfo_width() and \
           event.y >= yPlaylist - yMediadir and event.y < yPlaylist - yMediadir + self.lstPlaylist.winfo_height():
            curIndex = self.lstPlaylist.nearest(event.y - yPlaylist + yMediadir) # liefert -1, wenn die Liste in lstPlaylist leer ist, ansonsten nullbasierend den Listenindex
            if curIndex < 0: curIndex = 0 # Wenn curIndex -1 ist wird die Auswahl mit .insert(curIndex) nicht hinzugefügt. Sie soll aber vorne rein!
            self.printVerbose(self.GL_VERBOSITY_DEBUG, '  --> inside Playlist: curIndex=' + str(curIndex))
            # Datenquelle ermitteln: Liste der selektierten Einträge aus trvMediadir
            for sel in self.trvMediadir.selection():
                # Fallunterscheidung 'dir' oder 'fil'
                if self.trvMediadir.tag_has('dir', sel) == True:
                    # Verzeichnis (Directory):
                    files = self.recursiveGetAllChildren(self.trvMediadir, sel)
                    print("vorher:  " + str(self.gl_omxplayerListindex))
                    firstitem = True
                    for fil in files:
                        self.lstPlaylist.insert(curIndex, self.gl_MediaDir + self.GL_PATHSEPARATOR + fil)
                        if firstitem:
                            # Den ersten eingefügten Titel selektieren:
                            self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen löschen
                            self.lstPlaylist.select_set(curIndex)         # eingefügten Titel wählen
                            self.lstPlaylist.see(curIndex)                # eingefügten Titel ins Bildfeld scrollen
                            firstitem = False
                        if self.gl_omxplayerListindex >= curIndex:
                            self.gl_omxplayerListindex += 1           # aktuellen Titel mitziehen!
                        curIndex += 1 # wichtig, damit das nächste Element aus trvMediadir-Auswahl in der richtigen Reihenfolge in lstPlaylist eingefügt wird
                    print("nachher: " + str(self.gl_omxplayerListindex))
                else:
                    # normale Datei: hinzufügen
                    ####Add2Playlist(self.gl_MediaDir + self.GL_PATHSEPARATOR + sel, curIndex)
                    self.lstPlaylist.insert(curIndex, self.gl_MediaDir + self.GL_PATHSEPARATOR + sel) # 2017-08-14 schlizbaeda V0.2: Den unvollständigen Pfad im Treeview-Steuerelement um self.gl_MediaDir ("/media/pi") erweitern
                    self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen löschen
                    self.lstPlaylist.select_set(curIndex)         # eingefügten Titel wählen
                    self.lstPlaylist.see(curIndex)                # eingefügten Titel ins Bildfeld scrollen
                    if self.gl_omxplayerListindex >= curIdx:
                        self.gl_omxplayerListindex += 1           # aktuellen Titel mitziehen!
                    curIndex += 1 # wichtig, damit das nächste Element aus trvMediadir-Auswahl in der richtigen Reihenfolge in lstPlaylist eingefügt wird
        else:
            self.printVerbose(self.GL_VERBOSITY_DEBUG, '  --> outside Playlist')
            
            
    def recursiveGetAllChildren(self, trv, item = '', depth = 0):
        children = trv.get_children(item)
        for child in children:
            children += self.recursiveGetAllChildren(trv, child, depth + 1)
        return children

    def butMediadirFind_Click(self, event):
        find = self.entMediadirFind.get()
        if True:
            if self.gl_trvMediadirChanged == True: # Die USB-Laufwerke haben sich seit dem letzten Aufruf geändert
                self.gl_trvMediadirChanged = False
                self.gl_trvMediadirList = self.recursiveGetAllChildren(self.trvMediadir)
                self.gl_trvMediadirFoundChg = True # auch die Trefferliste muss angepasst werden!
            if self.gl_trvMediadirFoundChg == True: # Der Suchstring hat sich geändert
                self.gl_trvMediadirFoundChg = False
                self.gl_trvMediadirFoundList = [item for item in self.gl_trvMediadirList if find.lower() in item.lower()] # List Comprehension (pythontypisch und effektiv)
                self.gl_trvMediadirFoundIndex = 0
            if self.gl_trvMediadirFoundList != []: # auf nicht-leere Liste prüfen
                self.trvMediadir.see(self.gl_trvMediadirFoundList[self.gl_trvMediadirFoundIndex]) # aktuelle Fundstelle im Steuerelement zur Anzeige bringen (Baumstruktur öffnen und Element in den sichtbaren Bereich rücken)
                self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butMediadirFind_Click: item found at pos. ' + str(self.gl_trvMediadirFoundIndex))
                #self.trvMediadir.selection_set(self.gl_trvMediadirFoundList[self.gl_trvMediadirFoundIndex].replace(' ', '\ ')) # aktuelle Fundstelle auswählen (selektieren): WICHTIG: Die Leerzeichen im Dateinamen müssen mit '\' "entwertet" werden, da sonst die Dateinamen "zerhackt" werden! Die resultierenden Teilstrings sind keine gültigen Einträge des Treeview-Steuerelementes
                self.trvMediadir.selection_set(self.gl_trvMediadirFoundList[self.gl_trvMediadirFoundIndex]) # obige Anweisung ist ein Schmarrn!
                self.gl_trvMediadirFoundIndex += 1
                if self.gl_trvMediadirFoundIndex >= len(self.gl_trvMediadirFoundList): self.gl_trvMediadirFoundIndex = 0
            else:
                self.gl_trvMediadirFoundIndex = -1 # nichts Passendes gefunden
                self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butMediadirFind_Click: item not found.')

    def entMediadirFind_KeyPress(self, event):
        # Es wurde im Suchstring-Steuerelement eine Taste gedrückt:
        # Der Suchstring hat sich geändert!
        if event.keysym_num == 65288 or event.keysym_num == 65535 or event.keysym_num < 65000:
            # Tasten "BackSpace" oder "Delete" oder normale Tasten
            #print('normale Taste')
            self.gl_trvMediadirFoundChg = True
        elif event.keysym_num == 65293 or event.keysym_num == 65421:
            # Tasten "Return" (bei den Buchstaben) oder "KP_Enter" (beim Ziffernblock)
            #print('ENTER')
            self.butMediadirFind_Click(event) # Suche durchführen
        else:
            # Tasten mit keysym_num >= 65000: Shift, Cursortasten, F-Tasten etc.
            #print('Sondertaste')
            pass


    def butPlaylistRemove_Click(self, event):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butPlaylistRemove_Click')
        try:
            selIndex = int(self.lstPlaylist.curselection()[0]) # nullbasierend
        except:
            selIndex = -1
        if selIndex >= 0:
            # es ist ein Playlisteintrag selektiert:
            self.lstPlaylist.delete(selIndex)
            self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen löschen
            self.lstPlaylist.select_set(selIndex)
            self.lstPlaylist.see(selIndex)
            if selIndex <= self.gl_omxplayerListindex:            
                self.gl_omxplayerListindex -= 1

    def butPlaylistMoveUp_Click(self, event):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butPlaylistMoveUp_Click')
        try:
            selIndex = int(self.lstPlaylist.curselection()[0]) # nullbasierend
        except:
            selIndex = -1
        if selIndex > 0:
            # es ist ein Playlisteintrag selektiert:
            selItem = self.lstPlaylist.get(selIndex)
            self.lstPlaylist.delete(selIndex)              # Ausgewählten Listeneintrag an der alten Stelle löschen
            self.lstPlaylist.insert(selIndex - 1, selItem) # den soeben gelöschten Listeneintrag davor wieder eintragen
            self.lstPlaylist.select_clear(0, tkinter.END)  # alle Markierungen löschen
            self.lstPlaylist.select_set(selIndex - 1)      # den verschobenen Listeneintrag selektieren
            self.lstPlaylist.see(selIndex - 1)             # den verschobenen Listeneintrag ins Bildfeld scrollen
            if selIndex - 1 == self.gl_omxplayerListindex: # Der verschobene Listeneintrag drückte den aktuellen Titel um eine Position weiter: 
                self.gl_omxplayerListindex += 1            # --> mitziehen
            elif selIndex == self.gl_omxplayerListindex:   # Der verschobene Listeneintrag ist der aktuell laufende Titel: 
                self.gl_omxplayerListindex -= 1            # --> mitziehen
                
    def butPlaylistMoveDn_Click(self, event):
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'butPlaylistMoveDn_Click')
        try:
            selIndex = int(self.lstPlaylist.curselection()[0]) # nullbasierend
        except:
            selIndex = -1
        if selIndex >= 0 and selIndex < self.lstPlaylist.size() - 1:
            # es ist ein Playlisteintrag selektiert:
            selItem = self.lstPlaylist.get(selIndex)
            self.lstPlaylist.delete(selIndex)              # Ausgewählten Listeneintrag an der alten Stelle löschen
            self.lstPlaylist.insert(selIndex + 1, selItem) # den soeben gelöschten Listeneintrag dahinter wieder eintragen
            self.lstPlaylist.select_clear(0, tkinter.END)  # alle Markierungen löschen
            self.lstPlaylist.select_set(selIndex + 1)      # den verschobenen Listeneintrag selektieren
            self.lstPlaylist.see(selIndex + 1)             # den verschobenen Listeneintrag ins Bildfeld scrollen
            if selIndex + 1 == self.gl_omxplayerListindex: # Der verschobene Listeneintrag drückte den aktuellen Titel um eine Position weiter: 
                self.gl_omxplayerListindex -= 1            # --> mitziehen
            elif selIndex == self.gl_omxplayerListindex:   # Der verschobene Listeneintrag ist der aktuell laufende Titel: 
                self.gl_omxplayerListindex += 1            # --> mitziehen

    ##### Ereignishandler für "USB-detect", basierend auf dem Modul pyudev #####
    def add_usbDrive(self, drive):
        for base, dirs, files in os.walk(self.gl_MediaDir):
            base = base[len(self.gl_MediaDir):]  # Inhalt von self.gl_MediaDir ("/media/pi") im Gesamtpfad vorne entfernen
            splitbase = base.split(self.GL_PATHSEPARATOR)
            if base != '':
                if splitbase[1] == drive:
                    insnode = ''
                    for ins in splitbase[:-1]:
                        if insnode != '': insnode = insnode + self.GL_PATHSEPARATOR
                        insnode = insnode + ins
                    nodeid = insnode
                    if nodeid != '': nodeid = nodeid + self.GL_PATHSEPARATOR
                    nodeid = nodeid + splitbase[-1] 
                    self.trvMediadir.insert(insnode, 'end', nodeid, text = splitbase[-1], tags = ('dir', 'simple')) # Eintrag als Directory markieren
                    for file in files:
                        self.trvMediadir.insert(nodeid, 'end', nodeid + self.GL_PATHSEPARATOR + file, text = file, tags = ('file', 'simple'))
        self.gl_trvMediadirChanged = True

    def remove_usbDrive(self, drive):
        self.trvMediadir.delete(drive)
        self.gl_trvMediadirChanged = True

    def usb_eventhandler(self, usbdevice):
        # hier kann ohne Probleme eine Wartezeit oder etwas anderes Längeres eingefügt werden,
        # da diese Routine nicht im Hauptthread läuft, sondern in einem parallelen Thread.
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   usb_eventhandler')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  #### {0} DEVICE ####'.format(usbdevice.action))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  driver:       ' + ('None' if usbdevice.driver is None else usbdevice.driver))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '  sys_name:     ' + ('None' if usbdevice.sys_name is None else usbdevice.sys_name))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    #### Device ####')
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    action:      ' + usbdevice.action)
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    subsystem:   ' + usbdevice.subsystem)
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    driver:      ' + ('None' if usbdevice.driver is None else usbdevice.driver))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    device_path: ' + usbdevice.device_path)
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    device_type: ' + ('None' if usbdevice.device_type is None else usbdevice.device_type))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    device_node: ' + ('None' if usbdevice.device_node is None else usbdevice.device_node))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    device_num:  ' + ('None' if usbdevice.device_type is None else usbdevice.device_type))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    sys_path:    ' + ('None' if usbdevice.sys_path is None else usbdevice.sys_path))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    sys_name:    ' + ('None' if usbdevice.sys_name is None else usbdevice.sys_name))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    sys_n umber:  ' + ('None' if usbdevice.sys_number is None else usbdevice.sys_number))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    tags:        ' + str(list(usbdevice.tags)))
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '    sequ_number: ' + str(usbdevice.sequence_number))
        #self.printVerbose(self.GL_VERBOSITY_DEBUG, '    attributes:  ' + str(iter(usbdevice.attributes)))
        tim = time.time() # Vergangene Sekunden seit dem 01. Januar 1970
        starttim = tim
        # 2017-09-20 schlizbaeda V0.2.1: Überprüfung mit Timeout, ob /media/pi überhaupt existiert:
        curMediaDrives = []
        try:
            curMediaDrives = os.listdir(self.gl_MediaDir)
        except:
            # Eine Exception kann auftreten, wenn kein USB-Laufwerk gemountet ist:
            # Dann existiert in /media u.U. nicht einmal das Unterverzeichnis /media/pi
            # und os.listdir(self.gl_MediaDir) "wirft" die Exception "FileNotFoundError: [Errno 2] No such file or directory: '/media/pi'"
            pass
        oldMediaDrives = copy.copy(curMediaDrives)
        if usbdevice.action == 'add' and usbdevice.driver == 'usb-storage':
            self.printVerbose(self.GL_VERBOSITY_USB, '[USB]     usb_eventhandler.add: "' + usbdevice.driver + '"')
            cnt = 0
            while cnt < 10 and tim - starttim <= 9.0 and self.gl_quit == 0:
                time.sleep(0.2)
                tim = time.time() # Vergangene Sekunden seit dem 01. Januar 1970
                try:
                    curMediaDrives = os.listdir(self.gl_MediaDir)
                except:
                    pass
                if curMediaDrives == oldMediaDrives:
                    cnt = 0
                else:
                    cnt += 1
            if oldMediaDrives != curMediaDrives:
                time.sleep(0.2)
                # Die Directoryeinträge unter /media/pi haben sich geändert (d.h. es ist ein neues USB-Laufwerk hinzugekommen)
                # neues Laufwerk unter /media/pi ermitteln:
                for drive in curMediaDrives:
                    if oldMediaDrives.count(drive) == 0:
                        self.add_usbDrive(drive)
        elif usbdevice.action == 'remove' and usbdevice.sys_name.find(':') >= 0:
            self.printVerbose(self.GL_VERBOSITY_USB, '[USB]     usb_eventhandler.remove: "' + usbdevice.sys_name + '"')
            # Die Eigenschaft usbdevice.sys_name enthält das Zeichen ':',
            # wenn es sich um ein korrespondierendes remove-Ereignis
            # zu einem vorausgegangenem add-Ereignis mit usbdevice.driver == 'usb-storage' handelt.
            while curMediaDrives == oldMediaDrives and tim - starttim <= 3.0 and self.gl_quit == 0:
                time.sleep(0.2)
                tim = time.time() # Vergangene Sekunden seit dem 01. Januar 1970
                curMediaDrives = os.listdir(self.gl_MediaDir)
            if oldMediaDrives != curMediaDrives:
                # Die Directoryeinträge unter /media/pi haben sich geändert (d.h. es ist ein neues USB-Laufwerk hinzugekommen)
                # entferntes Laufwerk unter /media/pi ermitteln:
                for drive in oldMediaDrives:
                    if curMediaDrives.count(drive) == 0:
                        self.remove_usbDrive(drive)


    # Teil 3: weitere Features ("nice to have")
    ##### Ereignishandler für die erweiterte Programmbedienung #####
    def mnuFileOpen_Click(self):
        filename = tkinter.filedialog.askopenfilename(title = 'Mediadatei öffnen', filetypes = [('Alle Dateien', '*')])
        if bool(filename):
            self.lstPlaylist.insert(tkinter.END, filename)

    def mnuPlaylistOpen_Click(self):
        filename = tkinter.filedialog.askopenfilename(title = 'Playlist öffnen', filetypes = [('m3u-Playlist', '*.m3u'), ('Alle Dateien', '*')])
        if bool(filename):
            try:
                file = open(filename, 'r')
            except IOError as err:
                tkinter.messagebox.showerror(title = 'Playlist öffnen', message = err)
            else:
                for line in file:
                    line = str.strip(line, ' ')  # Leerzeichen vorne und hinten abschneiden ("trim")
                    if not line.startswith('#'): # Zeilen, die mit '#' beginnen, sind m3u-Kommentarzeilen
                        self.lstPlaylist.insert(tkinter.END, line.replace('\n', ''))
                file.close()
        
    def mnuPlaylistSave_Click(self):
        if self.lstPlaylist.get(0, tkinter.END) != (): # nur speichern, wenn die Playlist auch wirklich Einträge enthält
            filename = tkinter.filedialog.asksaveasfilename(title = 'Playlist speichern', initialfile = 'playlist.m3u', filetypes = [('m3u-Playlist', '*.m3u'), ('Alle Dateien', '*')])
            if filename != '':
                try:
                    file = open(filename, 'w')
                except IOError as err:
                    tkinter.messagebox.showerror(title = 'Playlist speichern', message = err)
                else:
                    for line in self.lstPlaylist.get(0, tkinter.END):
                        file.write(line + '\n')
                    file.close()

    def mnuViewFullscreen_ShowState(self, state):
        # schlizbaeda v0.4.0: Anzeige des aktuellen Zustandes im Menüpunkt
        txt = 'F11  Vollbild ☑' if self.gl_fullscreen else 'F11  Vollbild ☐' # ☐ = U+2610(9744), ☑ = U+2611(9745), ☒ = U+2612(9746)
        self.mnuView.entryconfigure(0, label = txt)

    def mnuViewFullscreen_Click(self):
        # 2016-11-20 schlizbaeda V0.2: Wechsel zwischen Vollbild und Fensteransicht
        self.gl_fullscreen = not self.gl_fullscreen
        self.mnuViewFullscreen_ShowState(self.gl_fullscreen)
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            if self.gl_omxplayer_GetWidth() + self.gl_omxplayer_GetHeight() + self.gl_omxplayer_GetAspect() > 0.0: #if self.gl_omxplayer.width() + self.gl_omxplayer.height() + self.gl_omxplayer.aspect_ratio() > 0.0: #if self.gl_omxplayer._get_properties_interface().ResWidth() + self.gl_omxplayer._get_properties_interface().ResHeight() + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methoden ._get_properties_interface().*() durch offizielle Methoden .*() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
                # Es handelt sich um ein Video, weil die Videoabmessungen > 0 sind (Für MP3-Audiodateien liefert omxplayer.bin ResWidth=0, ResHeight=0, Aspect=0.0)
                self.gl_omxplayer.set_aspect_mode(self.gl_aspectMode)
                if self.gl_fullscreen:
                    # Das Video soll als Vollbild angezeigt werden:
                    self.gl_omxplayer.set_video_pos(0, 0, 0, 0)
                    # schlizbaeda v0.4.0: Hauptfenster aktivieren für bessere Bedienung über F11
                    self.YAMuPlayGUI.deiconify()
                    self.YAMuPlayGUI.focus_set()
                    # Toplevel-Widget erst unsichtbar machen, nachdem der Fokus auf dem Hauptfenster self.YAMuPlayGUI liegt:
                    # Sonst verliert die gesamte Anwendung den Fokus und das Setzen mit self.YAMuPlayGUI.focus_set() funktioniert nicht!
                    self.Videobox.withdraw()
                    self.printVerbose(self.GL_VERBOSITY_NORMAL, 'mnuViewFullscreen_Click: show video in fullscreen mode')
                else:
                    # Das Video soll in der Fensteransicht dargestellt werden:
                    self.printVerbose(self.GL_VERBOSITY_NORMAL, 'mnuViewFullscreen_Click: show video in window mode')
                    self.omxplayerFitToplevel()

    def mnuViewAspectMode_ShowState(self, mode):
        # schlizbaeda v0.4.0: Anzeige des aktuellen Zustandes im Menüpunkt
        txt = 'F12  AspectMode "' + mode + '"'
        self.mnuView.entryconfigure(1, label = txt)

    def mnuViewAspectMode_Click(self):
		# 2016-11-20 schlizbaeda V0.2: Videodarstellung innerhalb der angegebenen Abmessungen: AspectMode ändern
        if self.gl_aspectMode == 'letterbox':
            self.gl_aspectMode = 'fill' # unskalierten Ausschnitt des Videos innerhalb der Abmessungen anzeigen.
        elif self.gl_aspectMode == 'fill':
            self.gl_aspectMode = 'stretch' # Video innerhalb der angegebenen Abmessungen bis zum Rand strecken. Dabei treten bei falschem Seitenverhältnis Verzerrungen auf
        else:
            self.gl_aspectMode = 'letterbox' # Video innerhalb der angegebenen Abmessungen unverzerrt anzeigen. Dabei entstehen links/rechts oder oben/unten Leerbereiche
        self.mnuViewAspectMode_ShowState(self.gl_aspectMode)
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            if self.gl_omxplayer_GetWidth() + self.gl_omxplayer_GetHeight() + self.gl_omxplayer_GetAspect() > 0.0: #if self.gl_omxplayer.width() + self.gl_omxplayer.height() + self.gl_omxplayer.aspect_ratio() > 0.0: #if self.gl_omxplayer._get_properties_interface().ResWidth() + self.gl_omxplayer._get_properties_interface().ResHeight() + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methoden ._get_properties_interface().*() durch offizielle Methoden .*() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
                # Es handelt sich um ein Video, weil die Videoabmessungen > 0 sind (Für MP3-Audiodateien liefert omxplayer.bin ResWidth=0, ResHeight=0, Aspect=0.0)
                self.gl_omxplayer.set_aspect_mode(self.gl_aspectMode)
                self.Videobox.title(self.gl_omxplayer.get_source() + ' [' + self.gl_aspectMode + ']')
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'mnuViewAspectMode_Click: "' + self.gl_aspectMode + '"')

        
    def mnuViewBackground_Click(self): # 2017-08-14 schlizbaeda V0.2: Hintergrundfarbe einstellen
        try:
            bcol = tkinter.colorchooser.askcolor(color=self.gl_VideoboxBackcolor, title='Hintergrundfarbe der Videobox wählen')[1]
        except:
            # wenn die (per Kommandozeilenparameter angegebene) alte Farbe ungültig ist, den Farbwahldialog ohne Vorbelegung "color=..." öffnen
            bcol = tkinter.colorchooser.askcolor(title='Hintergrundfarbe der Videobox wählen')[1]
        if bcol:
            self.gl_VideoboxBackcolor = bcol
            try:
                self.Videobox.configure(background=self.gl_VideoboxBackcolor)
            except:
                pass # Wenn die angegebene Farbbezeichnung ungültig ist, einfach nichts tun!

    def mnuViewKeepVideoboxSize_ShowState(self, state):
        # schlizbaeda v0.4.0: Anzeige des aktuellen Zustandes im Menüpunkt
        # ACHTUNG:
        # Wenn self.gl_keepVideoboxSize gesetzt ist (true), wird die Videogröße bebehalten,
        # also nicht "automatisch angepasst". Daher muss das Häkchen invers gesetzt werden!
        txt = '        Videogröße automatisch anpassen ☐' if self.gl_keepVideoboxSize else '        Videogröße automatisch anpassen ☑' # ☐ = U+2610(9744), ☑ = U+2611(9745), ☒ = U+2612(9746)
        self.mnuView.entryconfigure(3, label = txt)

    def mnuViewKeepVideoboxSize_Click(self): # 2017-08-14 schlizbaeda V0.2: toggle self.gl_keepVideoboxSize
        self.gl_keepVideoboxSize = not self.gl_keepVideoboxSize
        self.mnuViewKeepVideoboxSize_ShowState(self.gl_keepVideoboxSize)
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'mnuViewKeepVideoboxSize_Click: ' + str(self.gl_keepVideoboxSize))

    def mnuViewSetDefaultAlpha_Click(self):
        # schlizbaeda v0.4.0: neuer Menüpunkt "Voreingestellte Transparenz setzen" (bisher nur über Taste F9)
        # Dient u.a. als "Rettung", wenn man den Alpha-Wert versehentlich auf 255 gestellt hat und die Steuerelemente "blind" nicht mehr findet...
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'mnuViewSetDefaultAlpha_Click: ' + str(self.gl_alphaDefault))
        self.spinAlpha.delete(0, tkinter.END)          # Aktuelle Belegung löschen
        self.spinAlpha.insert(0, self.gl_alphaDefault) # und Defaultwert eintragen
        self.spinAlpha_command()                       # Alpha-Wert aktualisieren
        #self.spinAlpha.focus_force()                   # setzt den Eingabefokus auf das spinAlpha-Widget. Dies wird jedoch auf http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/universal.html NICHT empfohlen: ("This is impolite.")

    def mnuViewShowCurrentTitle_Click(self):
        # schlizbaeda v0.4.0: neuer Menüpunkt "Aktuellen Titel anzeigen" (bisher nur über Taste F5)
        self.printVerbose(self.GL_VERBOSITY_NORMAL, 'mnuViewShowCurrentTitle_Click')
        self.YAMuPlayGUI.config(cursor = 'watch') # Mauszeiger als "Sanduhr" darstellen, da insbesondere die Bereinigung etwas dauern kann...
        self.YAMuPlayGUI.update()                 # DoEvents (wichtig, damit die Mauszeigeränderung angezeigt wird)
        # 1. Playlist aktualisieren (laufenden Titel auswählen)
        if self.gl_omxplayer is None:
            # omxplayer läuft nicht:
            idx = -1
        else:
            # omxplayer läuft:
            idx = self.gl_omxplayerListindex # aktueller Titel
        try:
            self.lstPlaylist.select_clear(0, tkinter.END) # alle Markierungen in der Playlist löschen
            if idx >= 0:
                self.lstPlaylist.select_set(idx)          # ermittelten Titel in der Playlist anzeigen (selektieren)
                self.lstPlaylist.see(idx)                 # Playlist zum ermittelten Titel scrollen
        except:
            pass
        # 2. bereinigen: Fehlerhafte Einträge in der Playlist löschen
        idx = 0#self.lstPlaylist
        for filenam in self.lstPlaylist.get(0, 'end'):
            try:
                filetype = magic.from_file(filenam, mime=True)
            except magic.MagicException as err:
                filetype = '[ERROR] MagicException: ' + str(err.filename)
            except OSError as err:
                filetype = "[ERROR] file doesn't exist: " + str(err.filename)
            except:
                filetype = '[ERROR]'
            if filetype.startswith('[ERROR]') or not (filetype.startswith('audio/') or filetype.startswith('video/')):
                self.lstPlaylist.delete(idx)          # fehlerhaften Eintrag aus der Playlist entfernen
                if self.gl_omxplayerListindex >= idx: # Der gelöschte Listeneintrag ist hinter dem aktuell laufenden Titel: 
                    self.gl_omxplayerListindex -= 1   # --> mitziehen
                idx = idx - 1                         # idx verringern, da ja soeben ein Eintrag entfernt wurde 
            idx = idx + 1
        self.YAMuPlayGUI.config(cursor = '') # "normalen" Mauszeiger darstellen


    def mnuHelpAbout_Click(self):
        # GPL v3 - Kurzversion, falls die Lizenzdatei nicht lesbar ist:
        GPLv3 = '                ' + self.gl_appName + ' - Yet Another Music Player\n' + \
                '                Copyright (C) 2016-2018 schlizbaeda\n' + \
                '\n' + \
                self.gl_appName + ' is free software: you can redistribute it and/or modify\n' + \
                'it under the terms of the GNU General Public License as published by\n' + \
                'the Free Software Foundation, either version 3 of the License\n' + \
                'or any later version.\n' + \
                '\n' + \
                self.gl_appName + ' is distributed in the hope that it will be useful,\n' + \
                'but WITHOUT ANY WARRANTY; without even the implied warranty of\n' + \
                'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n' + \
                'GNU General Public License for more details.\n' + \
                '\n' + \
                'You should have received a copy of the GNU General Public License\n' + \
                'along with ' + self.gl_appName + '. If not, see <http://www.gnu.org/licenses/>.\n'
        # GPL v3 vollständig aus Datei "COPYING" einlesen:
        try:
            licfile = open('COPYING')
        except:
            licfile = None
        if not licfile is None:
            GPLv3 = licfile.read()
            licfile.close()

        # Anzeige der Aboutbox:        
        try:			
            self.Aboutbox.deiconify()
        except tkinter.TclError:
            # Die Aboutbox wurde mit dem roten "X" geschlossen und gelöscht: neu anlegen!
            self.createAboutbox()
            self.Aboutbox.deiconify()
        self.txtAboutboxLic.delete('1.0', 'end')    
        self.txtAboutboxLic.insert('1.0', GPLv3)

    def printTerminalHelp(self): # Ausgabe eines Hilfetextes auf der Konsole
        self.printVerbose(self.GL_VERBOSITY_HELP, self.gl_appName + ' V' + self.gl_appVer)
        self.printVerbose(self.GL_VERBOSITY_HELP, 'Yet Another Music Player -- Version ' + self.gl_appVer)
        msg = '''
Aufruf:
yamuplay.py [Parameter] [Mediadatei(en)]

Parameter:
  -o <audio>   Auswahl des Gerätes für die Audioausgabe
  -o hdmi
  -o local
  -o both
  -o alsa[:device]

  -f <bool>    "full screen"
  -f 0         False: Videoanzeige in einem Fenster
  -f 1         True:  Videoanzeige als Vollbild

  -a <mode>    "aspect mode"
  -a letterbox Vollständige Skalierung in das Videofenster ohne Verzerrung.
               Es entstehen Ränder an der zu großen Seite
  -a fill      Skalierung in das Videofenster auf die kleinere Kante.
               zu große Bereiche werden abgeschnitten und sind unsichtbar.
  -a stretch:  Anpassung an die Fenstergröße mit Verzerrung

  -k <bool>    "keep video size"
  -k 0         False: Zu Beginn eines Videos wird die erforderliche
                      Fenstergröße ermittelt und zentriert angezeigt.
  -k 1         True:  Ein neues Video wird in das bestehende Fenster skaliert.
                      Die Größe des Videofensters wird nicht verändert.

  -c <bcol>    "back colour"
  -c black     Standardfarbe "schwarz"
  -c white     Standardfarbe "weiß"
  -c red       Standardfarbe "rot"
  -c \#ffff00  RGB-Farbe (gelb)

  -alpha <int> Transparenz (Defaultwert)
  -alpha 0     Videodarstellung vollständig transparent (unsichtbar)
  -alpha 255   Videodarstellung vollständig deckend
               Es wird empfohlen, einen Wert zwischen 0 und 200 zu verwenden,
               um bei Bedarf den Desktop mit F9 sichtbar machen zu können.

  -dx <pixel>  X-Offset zwischen Videodarstellung (GPU) und Videofenster (CPU)
  -dy <pixel>  Y-Offset zwischen Videodarstellung (GPU) und Videofenster (CPU)
               Mein 24"-Drexfernseher hat eine Auflösung von 1824x984 Pixeln,
               über EDID(?) meldet er aber 1920x1080! Dadurch fehlen in X- und
               Y-Richtung jeweils 96 Pixel. Das Video ist gegenüber dem Fenster
               in jede Richtung um 48 Pixel (96/2) verschoben.
               Mit -dx 48 und -dy 48 kann das kompensiert werden.
               --> Dies scheint offenbar bei mehreren Fernsehern so zu sein...
                   again what learned: Kein Schaden ohne Nutzen :-)

  -v           Ausführlichkeitsstufe (verbosity) der Konsolenausgaben (Flags):
               2^0 =   1: ERROR     Fehler ausgeben
               2^1 =   2: WARNING   Warnungen ausgeben
               2^2 =   4: HELP      Hilfetext beim Programmstart ausgeben
               2^3 =   8: NORMAL    aktuelle Aktion bzw. GUI-Ereignis ausgeben
               2^4 =  16: USB       USB-Ereignisse ausgeben
               2^5 =  32: OMXPLAYER Kommandos für den omxplayer ausgeben
               2^6 =  64: RECEIVE   Rückgabewerte vom omxplayer ausgeben
               2^7 = 128: DEBUG     Debugmeldungen ausgeben


Tastaturbelegung:
  F1:    Anzeige einer Aboutbox (Menüpunkt Hilfe-->Info)
  F2:    Debugausgabe im Konsolenfenster: def omxplayerDebugPrint(self):
  F3:    Dateisuche
  F5:    Playlist aktualisieren (laufenden Titel auswählen) und bereinigen
  F9:    Transparenz auf Defaultwert setzen (Kommandozeilenparameter -alpha)
  F10:   Öffnen des Menüs (offenbar ein internes TKinter-Feature)
  F11:   Wechsel zwischen Videoanzeige im Fenster und Vollbild
  F12:   Wechsel der "aspect modes": letterbox, fill, stretch
  DEL:   Löschen des markierten Titels aus der Playlist
  SPACE: Play/Pause

Copyright (C) 2016 - 2018 by schlizbaeda (GNU GPL v/3)


'''
        # TODO: Weitere geplante Tastenbelegungen
        #  ENTER: entspricht Doppelklick # TODO: Die Umsetzung wird vareckt: Steuerelement mit aktuellem Fokus ermitteln, entsprechende Fallunterscheidung in den Ereignishandler (bäh)...
        #  SPACE: siehe ENTER
        self.printVerbose(self.GL_VERBOSITY_HELP, msg)

    ##### globale Ereignishandler der GUI:
    def YAMuPlayGUI_KeyPress(self, event):
        # 2016-11-20 schlizbaeda V0.2: Globales "KeyPress"-Ereignis für allgemeine Steuerung über die Tastatur
        #   F1: About-Box anzeigen
        #   F2: Debugausgaben jetzt anzeigen
        #   F3: Dateisuche
        #   F5: Playlist aktualisieren (laufenden Titel auswählen) und bereinigen
        #   F9: Alpha-Wert (Transparenz) auf Default-Wert setzen
        #  F10: öffnet das Menü --> offenbar eine interne TKinter-Geschichte 
        #  F11: Umschalten Vollbild/Fensteransicht
        #  F12: "AspectMode" wählen: "letterbox" | "fill" | "stretch"
        #  DEL: Löschen des markierten Titels aus der Playlist
        if event.char == event.keysym:
            msg = 'Normal Key %r' % event.char
        elif len(event.char) == 1:
            msg = 'Punctuation Key %r (%r)' % (event.keysym, event.char)
            if event.keysym == 'space':
                # Leertaste: Play/Pause
                self.butPlayPause_Click(event)
            elif event.keysym == 'Delete':
                # Löschen des markierten Titels aus der Playlist
                self.butPlaylistRemove_Click(event)
        else:
            msg = 'Special Key %r' % event.keysym
            if event.keysym == 'F1':
                # About-Box anzeigen
                self.mnuHelpAbout_Click()
            elif event.keysym == 'F2':
                # Debugausgaben jetzt anzeigen
                self.omxplayerDebugPrint()
            elif event.keysym == 'F3':
                # Dateisuche
                self.butMediadirFind_Click(event) # Suche durchführen
            elif event.keysym == 'F5':
                # Playlist aktualisieren (laufenden Titel auswählen)
                self.mnuViewShowCurrentTitle_Click()
            elif event.keysym == 'F9':
                # Alpha-Wert (Transparenz) auf Default-Wert setzen:
                # Dient u.a. als "Rettung", wenn man den Alpha-Wert versehentlich auf 255 gestellt hat und die Steuerelemente "blind" nicht mehr findet...
                self.mnuViewSetDefaultAlpha_Click()
            elif event.keysym == 'F11':
                # F11 ist auch im VLC-Player die Taste für den Wechsel Fensteransicht/Vollbild
                self.mnuViewFullscreen_Click()
            elif event.keysym == 'F12':
                self.mnuViewAspectMode_Click()
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   YAMuPlayGUI_KeyPress: ' + msg)

    def YAMuPlayGUI_FocusIn(self, event):
        # schlizbaeda v0.4.0:
        self.spinAlpha_command() # Transparenz des Videos auf den Wert des Widgets spinAlpha setzen

    def YAMuPlayGUI_FocusOut(self, event):
        # schlizbaeda v0.4.0:
        # Das Setzen des Alpha-Wertes (Transparenz) ist nur bei Videos möglich. Audiodateien werfen eine Exception --> daher abfangen
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            if self.gl_omxplayer_GetWidth() + self.gl_omxplayer_GetHeight() + self.gl_omxplayer_GetAspect() > 0.0: #if self.gl_omxplayer.width() + self.gl_omxplayer.height() + self.gl_omxplayer.aspect_ratio() > 0.0: #if self.gl_omxplayer._get_properties_interface().ResWidth() + self.gl_omxplayer._get_properties_interface().ResHeight() + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methoden ._get_properties_interface().*() durch offizielle Methoden .*() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
                # Es handelt sich um ein Video, weil die Videoabmessungen > 0 sind (Für MP3-Audiodateien liefert omxplayer.bin ResWidth=0, ResHeight=0, Aspect=0.0)
                if 'iconic' == self.Videobox.state():
                    # Die Videobox wurde minimiert:
                    self.omxplayerIconify()
                #elif 'withdrawn' == self.Videobox.state():
                #    # Diesen Fall hier nicht abfangen, da beim Verschieben des Hauptfensters self.YAMuPlayGUI das Videovollbild durchaus transparenter werden soll!
                else:
                    # Die Videobox wurde nicht minimiert:
                    alpha = self.spinAlpha.get()
                    if alpha == '': alpha = self.gl_alphaDefault
                    try:
                        alpha = int(alpha)
                    except:
                        alpha = self.gl_alphaDefault
                    if alpha > 255:
                        alpha = 255
                    elif alpha < 0:
                        alpha = 0
                    # Falls der derzeit eingestellte Alpha-Wert kleiner ist als der Alpha-Defaultwert,
                    # wird dieser Wert verwendet, nicht der Defaultwert!
                    # ansonsten würde es beim Verschieben "untransparenter" werden als im Normalfall!
                    if alpha > self.gl_alphaDefault:
                        alpha = self.gl_alphaDefault
                    self.gl_omxplayer.set_alpha(alpha) # Alpha-Wert (Transparenz) über dbus ändern
                    self.printVerbose(self.GL_VERBOSITY_NORMAL, 'YAMuPlayGUI_FocusOut: alpha=' + str(alpha))


    def Videobox_Destroy(self, event):
        # v0.3.2: Dieser Ereignishandler fängt eine Menge Folgefehler ab, weil das Fenster "Videobox" geschlossen wird und deshalb nicht mehr existiert
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            self.gl_omxplayer.set_video_pos(0, 0, 0, 0)    # omxplayer-Video als Vollbild darstellen
            # WICHTIG: resultierendes Vollbild nur halb transparent darstellen, da das Schließen der Videobox mitunter unbeabsichtigt geschieht!
            try:
                alpha = int(self.spinAlpha.get())
            except:
                alpha = self.gl_alphaDefault
            if alpha > 255:
                alpha = 255
            elif alpha < 0:
                alpha = 0
            self.spinAlpha.delete(0, tkinter.END) # Aktuelle Belegung löschen
            self.spinAlpha.insert(0, alpha if alpha < self.gl_alphaDefault else self.gl_alphaDefault) # und aktuellen Wert eintragen
            self.spinAlpha_command()              # Alpha-Wert aktualisieren
        # ...und für den nächsten Titel sofort wieder eine neue Instanz des Videobox-Fensters erstellen:
        self.createVideobox()

    def Videobox_KeyPress(self, event):
        # 2016-11-20 schlizbaeda V0.2: Globales "KeyPress"-Ereignis für allgemeine Steuerung über die Tastatur
        #   F9: Alpha-Wert (Transparenz) auf Default-Wert setzen
        #  F10: optimale Fenstergröße anhand der Videogröße ermitteln
        #  F11: Umschalten Vollbild/Fensteransicht
        #  F12: "AspectMode" wählen: "letterbox" | "fill" | "stretch"
        if event.char == event.keysym:
            msg = 'Normal Key %r' % event.char
        elif len(event.char) == 1:
            msg = 'Punctuation Key %r (%r)' % (event.keysym, event.char)
            if event.keysym == 'space':
                # Leertaste: Play/Pause
                self.butPlayPause_Click(event)
        else:
            msg = 'Special Key %r' % event.keysym
            if event.keysym == 'F9':
                # Alpha-Wert (Transparenz) auf Default-Wert setzen:
                # Dient u.a. als "Rettung", wenn man den Alpha-Wert versehentlich auf 255 gestellt hat und die Steuerelemente "blind" nicht mehr findet...
                self.spinAlpha.delete(0, tkinter.END)          # Aktuelle Belegung löschen
                self.spinAlpha.insert(0, self.gl_alphaDefault) # und Defaultwert eintragen
                self.spinAlpha_command()                       # Alpha-Wert aktualisieren
                #self.spinAlpha.focus_force()                   # setzt den Eingabefokus auf das spinAlpha-Widget. Dies wird jedoch auf http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/universal.html NICHT empfohlen: ("This is impolite.")
            elif event.keysym == 'F10':
                # optimale Fenstergröße anhand der Videogröße ermitteln:
                self.printVerbose(self.GL_VERBOSITY_NORMAL, 'TODO: Videobox_KeyPress F10')
                keep = self.gl_keepVideoboxSize  # Modus für "Videogröße anpassen" merken
                self.gl_keepVideoboxSize = False # Modus "Videogröße anpassen" für self.omxplayerAdjustToplevel setzen
                self.omxplayerAdjustToplevel()
                self.gl_keepVideoboxSize = keep  # Modus für "Videogröße anpassen" wiederherstellen
            elif event.keysym == 'F11':
                # F11 ist auch im VLC-Player die Taste für den Wechsel Fensteransicht/Vollbild
                self.mnuViewFullscreen_Click()
            elif event.keysym == 'F12':
                self.mnuViewAspectMode_Click()
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   Videobox_KeyPress:    ' + msg)

    def Videobox_Configure(self, event):
        # 2016-11-20 schlizbaeda V0.2: Das Toplevel-Widget Videobox wurde in der Größe verändert
        if not self.gl_fullscreen:
            # Das Video wird gerade in der Fensteransicht dargestellt:
            self.omxplayerFitToplevel()
        self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   Videobox size: ' + self.Videobox.state())

    def Videobox_FocusIn(self, event):
        # schlizbaeda v0.4.0:
        self.spinAlpha_command() # Transparenz des Videos auf den Wert des Widgets spinAlpha setzen

    def Videobox_FocusOut(self, event):
        # schlizbaeda v0.4.0:
        # Das Setzen des Alpha-Wertes (Transparenz) ist nur bei Videos möglich. Audiodateien werfen eine Exception --> daher abfangen
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            if self.gl_omxplayer_GetWidth() + self.gl_omxplayer_GetHeight() + self.gl_omxplayer_GetAspect() > 0.0: #if self.gl_omxplayer.width() + self.gl_omxplayer.height() + self.gl_omxplayer.aspect_ratio() > 0.0: #if self.gl_omxplayer._get_properties_interface().ResWidth() + self.gl_omxplayer._get_properties_interface().ResHeight() + self.gl_omxplayer._get_properties_interface().Aspect() > 0.0: # 2017-09-20 schlizbaeda V0.2.1: inoffizielle Methoden ._get_properties_interface().*() durch offizielle Methoden .*() ersetzt, damit yamuplay.py auch bei Updates von willprice/python-omxplayer-wrapper weiterhin funktioniert...
                # Es handelt sich um ein Video, weil die Videoabmessungen > 0 sind (Für MP3-Audiodateien liefert omxplayer.bin ResWidth=0, ResHeight=0, Aspect=0.0)
                if 'iconic' == self.Videobox.state():
                    # Die Videobox wurde minimiert:
                    self.omxplayerIconify()
                elif 'withdrawn' == self.Videobox.state():
                    # Die Videobox wurde unsichtbar (wegen Videovollbild):
                    self.printVerbose(self.GL_VERBOSITY_DEBUG, '[DEBUG]   Videobox.withdrawn (invisible) due to fullscreen mode')
                else:
                    # Die Videobox wurde nicht minimiert:
                    alpha = self.spinAlpha.get()
                    if alpha == '': alpha = self.gl_alphaDefault
                    try:
                        alpha = int(alpha)
                    except:
                        alpha = self.gl_alphaDefault
                    if alpha > 255:
                        alpha = 255
                    elif alpha < 0:
                        alpha = 0
                    # Falls der derzeit eingestellte Alpha-Wert kleiner ist als der Alpha-Defaultwert,
                    # wird dieser Wert verwendet, nicht der Defaultwert!
                    # ansonsten würde es beim Verschieben "untransparenter" werden als im Normalfall!
                    if alpha > self.gl_alphaDefault:
                        alpha = self.gl_alphaDefault
                    self.gl_omxplayer.set_alpha(alpha) # Alpha-Wert (Transparenz) über dbus ändern
                    self.printVerbose(self.GL_VERBOSITY_NORMAL, 'Videobox_FocusOut: alpha=' + str(alpha))


    ##### Ereignishandler für Strg+C, "kill <Prozess-ID>" und Programm beenden ("Alt+F4") #####
    def onClosing_cleanup(self):
        """
        Wenn YAMuPlay beendet wird, während gerade eine Mediadatei mit
        omxplayer.bin abgespielt wird, kommt es im aufrufenden Terminal
        zu Problemen mit stdin(?): Die eingegebenen Zeichen werden nicht
        angezeigt!
        Wenn der omxplayer.bin läuft, wird er hier angehalten, kurz
        gewartet und omxplayer.bin beendet. Die Wartezeit ist
        vermutlich notwendig, damit sich das Terminal wieder "fängt".
        Grund: ?
        """
        if not self.gl_omxplayer is None:
            # omxplayer läuft:
            self.gl_omxplayerStopevent = True # bewirkt komplettes Ende der Playlist
            self.gl_omxplayer.stop()          # beendet die Wiedergabe des aktuellen Titels
            time.sleep(0.5)                   # TODO: Prüfen, ob diese Zeit mit FullHD-Video am RPi1 auch ausreichend ist...
            self.gl_omxplayer.quit()          # Sauberes Beenden der noch vorhandenen omxplayer-Instanz beim Programmende
    
    # Programm über WM_DELETE_WINDOW beenden (z.B. durch Alt+F4 in der GUI oder Anklicken der Beenden-Schaltfläche mit dem "X"):
    def onClosing(self):
        self.onClosing_cleanup()
        self.gl_quit = 1 # Merker setzen (1 = Programm wurde "normal" beendet)
        self.YAMuPlayGUI.quit()

    # Programmabbruch durch Strg+C im aufrufenden Terminal:
    def keyCtrl_C(self, signal, frame):
        self.onClosing_cleanup()
        self.gl_quit = 2 # Merker setzen (2 = Programm wurde über Ctrl+C im aufrufenden Terminal beendet)
        self.YAMuPlayGUI.quit()

    # Programm über "kill <Prozess-ID>" beenden:
    def terminateProcess(self, signal, frame):
        self.onClosing_cleanup()
        self.gl_quit = 4 # Merker setzen (4 = Programm wurde über "kill <Prozess-ID>" beendet)
        self.YAMuPlayGUI.quit()
        
    # regelmäßiger Aufruf, damit Strg+C funktioniert:
    def do_nothing(self):
        self.YAMuPlayGUI.after(200, self.do_nothing)

    def run(self):
        # Verzeichnis /media einlesen:
        self.trvMediadir.tag_configure('dir', font = self.dirFont)
        self.trvMediadir.tag_configure('file', font = self.fileFont)
        #trvMediadir.tag_configure('file', background = 'yellow')
        try:
            for drive in os.listdir(self.gl_MediaDir):
                self.add_usbDrive(drive)
        except:
            # Eine Exception kann auftreten, wenn kein USB-Laufwerk gemountet ist:
            # Dann existiert in /media u.U. nicht einmal das Unterverzeichnis /media/pi
            # und os.listdir(self.gl_MediaDir) "wirft" die Exception "FileNotFoundError: [Errno 2] No such file or directory: '/media/pi'"
            self.printVerbose(self.GL_VERBOSITY_WARNING, '[WARN]    "' + self.gl_MediaDir + '" ist leer')
            self.printVerbose(self.GL_VERBOSITY_WARNING, '          Es wurde vermutlich noch kein USB-Laufwerk angeschlossen...')
        # Ereignishandler binden:
        self.YAMuPlayGUI.bind('<KeyPress>', self.YAMuPlayGUI_KeyPress)
        self.YAMuPlayGUI.bind('<FocusIn>', self.YAMuPlayGUI_FocusIn)
        self.YAMuPlayGUI.bind('<FocusOut>', self.YAMuPlayGUI_FocusOut)
        #self.trvMediadir.bind('<<TreeviewSelect>>', self.trvMediadir_TreeviewSelect) # funzt!
        self.trvMediadir.bind('<Button-1>', self.trvMediadir_Click)
        #self.trvMediadir.bind('<Double-1>', self.trvMediadir_DblClick)       # wird im Ereignis <Button-1> manuell (über den Code) ausgewertet
        #self.trvMediadir.bind('<ButtonPress>', self.trvMediadir_ButtonPress) # beißt sich mit dem Ereignis '<Button-1>': <Button-1> ist offenbar "stärker"
        self.trvMediadir.bind('<ButtonRelease>', self.trvMediadir_ButtonRelease)
        self.entMediadirFind.bind('<KeyPress>', self.entMediadirFind_KeyPress)
        self.butMediadirFind.bind('<Button-1>', self.butMediadirFind_Click)
		
        #self.lstPlaylist.bind('<Button-1>', self.lstPlaylist_Click)
        self.lstPlaylist.bind('<ButtonRelease>', self.lstPlaylist_Release)
        #self.lstPlaylist.bind('<Double-1>', self.lstPlaylist_DblClick)
        self.butPlaylistMoveUp.bind('<Button-1>', self.butPlaylistMoveUp_Click)
        self.butPlaylistMoveDn.bind('<Button-1>', self.butPlaylistMoveDn_Click)
        self.butPlaylistRemove.bind('<Button-1>', self.butPlaylistRemove_Click)
        # Schaltflächen des Mediaplayers
        self.butPlayPause.bind('<Button-1>', self.butPlayPause_Click)
        self.butRewind.bind('<ButtonPress>', self.butRewind_ButtonPress)
        self.butRewind.bind('<ButtonRelease>', self.butRewind_ButtonRelease)
        self.butForward.bind('<ButtonPress>', self.butForward_ButtonPress)
        self.butForward.bind('<ButtonRelease>', self.butForward_ButtonRelease)
        self.butPrev.bind('<Button-1>', self.butPrev_Click)
        self.butNext.bind('<Button-1>', self.butNext_Click)
        self.butStop.bind('<Button-1>', self.butStop_Click)
        self.spinAlpha.bind('<KeyRelease>', self.spinAlpha_KeyRelease) # 2016-11-20 schlizbaeda V0.2: Ereignis für Änderung des Alpha-Wertes (Transparenz)
		
        # Ereignishandler für Strg+C, "kill <Prozess-ID>" und Programmende (Alt+F4) einrichten:
        self.YAMuPlayGUI.protocol('WM_DELETE_WINDOW', self.onClosing) # normales Programmende
        signal.signal(signal.SIGINT, self.keyCtrl_C)         # Abbruch durch Ctrl+C im aufrufenden Terminal
        signal.signal(signal.SIGTERM, self.terminateProcess) # Abbruch durch "kill <Prozess-ID>"
        # hier könnte man für alle SIG...-Signale, die standardmäßig zum Programmabbruch führen (also die meisten),
        # ein Ereignis definieren, aber das lasse ich jetzt aus Performancegründen (und Faulheit) weg :-)
        self.YAMuPlayGUI.after(200, self.do_nothing)
		
        # USB-Ereignishandler einrichten:
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('usb') # filtert nur die USB-Ereignisse
        observer = pyudev.MonitorObserver(monitor, callback = self.usb_eventhandler, name = 'USB observer')
        observer.daemon
        observer.start()
		
        # tkinter-Mainloop starten:
        self.YAMuPlayGUI.mainloop()
        
        # mainloop wurde beendet:
        observer.stop()
        self.printVerbose(self.GL_VERBOSITY_NORMAL, '')
        if self.gl_quit & 1:
            self.printVerbose(self.GL_VERBOSITY_NORMAL, 'Das Programm wurde vom Anwender "normal" beendet.')
        elif self.gl_quit & 2:
            self.printVerbose(self.GL_VERBOSITY_NORMAL, 'Das Programm wurde über Ctrl+C im aufrufenden Terminalfenster abgebrochen.')
        elif self.gl_quit & 4:
            self.printVerbose(self.GL_VERBOSITY_NORMAL, 'Das Programm wurde über "kill <Prozess-ID>" beendet.')
        else:
            self.printVerbose(self.GL_VERBOSITY_NORMAL, 'Das Programm wurde auf unbekannte Weise beendet, self.gl_quit=' + str(self.gl_quit))


if __name__ == '__main__':
    tkinter_app = YAMuPlay().run()

#EOF
