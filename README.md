# yamuplay
YAMuPlay -- Yet Another MUsic PLAYer -- Version 0.3

## Hinweis zur aktuellen Version V0.3
YAMuPlay nutzt folgende externe Module:
* python3-dbus, V1.2.4
* https://github.com/willprice/python-omxplayer-wrapper.git, V0.2.3
* https://github.com/pyudev/pyudev.git, V0.21.0
* https://github.com/ahupp/python-magic.git, V0.4.13

Da es in der Vergangenheit immer wieder zu Kompatibilitätsproblemen kam,
wenn die jeweils neueste Programmversion der verwendeten Python-Module 
heruntergeladen wurde, wird dem yamuplay-Repository ab V0.2.1 IMMER der 
tatsächlich verwendete Versionsstand der genannten GitHub-Repositorys 
der verwendeten Module hinzugefügt, um von inkompatiblen Updates und 
Änderungen durch die Maintainer dieser Module unabhängig zu bleiben.

Bei größeren Versionssprüngen von YAMuPlay werden künftig vor den 
Änderungen die dann aktuellen Versionsstände der benötigten externen 
Module eingebunden.

Der Grund für diese Maßnahme ist eine Vereinfachung für den Anwender. 
Ein simpler Download mit
```shell
git clone https://github.com/schlizbaeda/yamuplay.git
```
und Durchführung der Installation nach der hier beschriebenen 
Vorgehensweise sollte dann prinzipiell immer funktionieren.

## Download und Installation inklusive aller Module und Bibliotheken
yamuplay (GPL v3)
```shell
cd /home/pi
git clone https://github.com/schlizbaeda/yamuplay.git
cd yamuplay
chmod 755 yamuplay.py
```

python3-dbus V1.2.4 (MIT)
```shell
cd /home/pi/yamuplay
sudo apt-get install python3-dbus
```

python-omxplayer-wrapper V0.2.3 (LGPL v3)
```shell
cd /home/pi/yamuplay/python-omxplayer-wrapper
sudo python3 setup.py install
```

pyudev V0.21.0 (LGPL v2.1)
```shell
cd /home/pi/yamuplay/pyudev
sudo python3 setup.py install
```

python-magic V0.4.13 (MIT)
```shell
cd /home/pi/yamuplay/python-magic
sudo python3 setup.py install
```

## Anleitung
Eine ausführliche Anleitung befindet sich in [`latex/YAMuPlay.pdf`](https://github.com/schlizbaeda/yamuplay/blob/master/latex/YAMuPlay.pdf)

Beim Start von `./yamuplay.py` im Terminalfenster erscheint im Terminal folgende Kurzanleitung:
```shell
YAMuPlay V0.3
Yet Another Music Player -- Version 0.3

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

Tastaturbelegung:
  F1:    Anzeige einer Aboutbox (Menüpunkt Hilfe-->Info)
  F2:    Debugausgabe im Konsolenfenster: def omxplayerDebugPrint(self):
  F3:    Dateisuche
  F5:    Playlist aktualisieren (laufenden Titel auswählen)
  F9:    Transparenz auf Defaultwert setzen (Kommandozeilenparameter -alpha)
  F10:   Öffnen des Menüs (offenbar ein internes TKinter-Feature) 
  F11:   Wechsel zwischen Videoanzeige im Fenster und Vollbild
  F12:   Wechsel der "aspect modes": letterbox, fill, stretch
  DEL:   Löschen des markierten Titels aus der Playlist

Copyright (C) 2016 - 2018 by schlizbaeda (GNU GPL v3)
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

23.09.2017:
yamuplay V0.2.1
* lokale Kopien der verwendeten Versionsstände der anderen GitHub-Repositorys aufgenommen
* Korrekturen kleinerer Laufzeitfehler

04.01.2018:
yamuplay V0.2.2
* Neuer Kommandozeilenparameter -o <audio>
Die neuen Versionen des omxplayers unterstützen jetzt auch die Audioausgabe 
über ALSA. Eine sauber eingerichtete Soundkarte (USB, I²S) kann somit
verwendet werden. Wichtig für den nächsten Faschingswagen :-)

25.01.2018:
yamuplay V0.3 (Version für den Faschingswagen am 04. und 11.02.2018)
* Bugfix: 
  Die Menüpunkte "Vollbild" und "AspectMode" lieferten eine Fehlermeldung,
  wenn sie für eine Audiodatei aufgerufen wurden.
* vertikale Scrollbalken in trvMediadir (Verzeichnisbaum) und lstPlaylist
* Drag+Drop von trvMediadir nach lstPlaylist:
  Ermöglicht das Einfügen von Mediadateien an der gewünschten Stelle
* Neue Tastenfunktionen:
  F3:  Dateisuche (wie Schaltfläche "suchen")
  F5:  Playlist aktualisieren (laufenden Titel auswählen)
  DEL: ausgewählten Eintrag in der Playlist entfernen
  
## TODO's:
Ich plane, folgende Punkte in einer künftigen Version einzubauen:
* Fortschrittsbalken für aktuellen Titel aktivieren
* Anzeige von Titelnummer und aktueller Laufzeit (wie beim echten CD-Spieler)
* Lautstärke über omxplayer einstellen --> ab v0.2.2 über ALSA gelöst
* omxplayer-eigenes Fading beseitigen (falls möglich) --> in den neuen Versionen nicht mehr vorhanden
* Erkennung anderer USB-Gerätetypen (z.B. Smartphones) , nicht nur klassische Speichergeräte (mass storage device)
* Einlesevorgang bei riesigen USB-Speichern optimieren (Hintergrundthread?)
* Bilder (*.JPG, *.PNG etc.) in Form einer Diashow anzeigen
* Bluetooth-Empfang von Smartphones, um Spotify-Musik abspielen zu können
* Ergänzend alle offenen Punkte aus der LaTeX-Dokumentation (Kapitel 2.3)
