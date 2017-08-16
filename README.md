# yamuplay
YAMuPlay -- Yet Another MUsic PLAYer -- Version 0.2

## Download und Installation inklusive aller Module und Bibliotheken
yamuplay                    GPL v3
```shell
cd /home/pi
git clone https://github.com/schlizbaeda/yamuplay.git
cd yamuplay
chmod 755 yamuplay.py
```

python-omxplayer-wrapper    LPGL v3
```shell
cd /home/pi/yamuplay
git clone https://github.com/willprice/python-omxplayer-wrapper.git
cd python-omxplayer-wrapper
sudo python3 setup.py install
```

python3-dbus                MIT
```shell
cd /home/pi/yamuplay
sudo apt-get install python3-dbus
```

pyudev v0.21.0              LPGL v2.1
```shell
cd /home/pi/yamuplay
git clone https://github.com/pyudev/pyudev.git
cd pyudev
sudo python3 setup.py install
```

python-magic                MIT
```shell
cd /home/pi/yamuplay
git clone https://github.com/ahupp/python-magic.git
cd python-magic
sudo python3 setup.py install
```

## Anleitung
Eine ausführliche Anleitung befindet sich demnächst in ./latex/YAMuPlay.pdf

Beim Start von ./yamuplay.py im Terminalfenster erscheint im Terminal folgende Kurzanleitung:
```shell
YAMuPlay V0.2
Yet Another Music Player -- Version 0.2

Aufruf:
YAMuPlay [Parameter] [Mediadatei(en)]

Parameter:
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
               Mein 24"-Drexfernseher hat eine Auflösung von 1824x984 Pixel,
               über EDID(?) meldet er aber 1920x1080! Dadurch fehlen in X- und
               Y-Richtung jeweils 96 Pixel. Das Video ist gegenüber dem Fenster
               in jede Richtung um 48 Pixel (96/2) verschoben.
               Mit -dx 48 und -dy 48 kann das kompensiert werden.
               Kein Schaden ohne Nutzen :-)

Tastaturbelegung:
  F1:   Anzeige einer Aboutbox (Menüpunkt Hilfe-->Info)
  F2:   Debugausgabe im Konsolenfenster: def omxplayerDebugPrint(self):
  F9:   Transparenz auf Defaultwert setzen (Kommandozeilenparameter -alpha)
  F10:  Öffnen des Menüs (offenbar ein internes TKinter-Feature) 
  F11:  Wechsel zwischen Videoanzeige im Fenster und Vollbild
  F12:  Wechsel der "aspect modes": letterbox, fill, stretch

Copyright (C) 2016 - 2017 by schlizbaeda (GNU GPL v3)
```

## Historie:
28.02.2016:
yamuplay V0.1 - in der Konfiguration für den Faschingswagen 2016 (Thema "500 Jahre Reinheitsgebot") 
  siehe https://github.com/schlizbaeda/bauwong

16.08.2017:
yamuplay V0.2
* Umstellung auf objektorientiere python3-Syntax (mein Dank gilt meigrafd)
* Fenstergröße der GUI flexibler gestaltet
* immer vollständige Pfade in der Playlist
* Videodarstellung Vollbild oder im Fenster mit diversen Optionen
* Unterstützung von Kommandozeilenparametern

## TODO's:
Ich plane, folgende Punkte in einer künftigen Version einzubauen:
* Scrollbalken für Playlist einfügen
* Drag+Drop für Playlists
* Fortschrittsbalken für aktuellen Titel aktivieren
* Anzeige von Titelnummer und aktueller Laufzeit (wie beim echten CD-Spieler)
* Lautstärke über omxplayer einstellen
* omxplayer-eigenes Fading beseitigen (falls möglich)
* Erkennung anderer USB-Gerätetypen (z.B. Smartphones) , nicht nur klassische Speichergeräte (mass storage device)
* Einlesevorgang bei riesigen USB-Speichern optimieren (Hintergrundthread?)
