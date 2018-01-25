Folgende Einstellungen werden vorgenommen (25.01.2018):
uname -a # Verwendete Raspbian-Version:
Linux raspberrypi 4.9.59-v7+ #1047 SMP Sun Oct 29 12:19:23 GMT 2017 armv7l GNU/Linux
Die angepassten Konfigurationsdateien sind in diesem Unterverzeichnis enthalten

System und Desktop anpassen:
----------------------------
Raspbian-Menü-->Einstellungen-->Appearance Settings:
   --> Layout="Centre image on screen"
   --> Picture=""raspberry-pi-logo.png"

Raspbian-Menü-->Einstellungen-->Tastatur und Maus
   --> Double-click Delay=1990 ("Gering"): Millisekunden für Pause zwischen den beiden Klicks


yamuplay V0.3 installieren:
---------------------------
laut Anleitung auf https://github.com/schlizbaeda/yamuplay (README.md)


yamuplax ins System einbinden:
------------------------------
HiFiBerry DAC+:
   /boot/config.txt
   /etc/asound.conf
Bildschirmschoner aus:
   /etc/lightdm.conf
Icons für yamuplay im Raspbian-Menü und auf dem Desktop
   /usr/share/applications/yamuplay.desktop

   cd ~/Desktop
   ln -s /usr/share/applications/yamuplay.desktop


matchbox-keyboard (Touch-Tastatur) einbinden:
---------------------------------------------
Die Anleitung aus meinem LaTeX-Dokument funktioniert immer noch.
--> es scheint aber mittlerweile ein Raspbian-Paket zu geben:
    sudo apt-get install matchbox-keyboard # beißt am RPi an!


TODOs:
======
* F-Tasten in Matchbox-Keyboard aufnehmen
* yamuplay soll bei ENTER die angezeigte Datei in die Playlist einfügen
* bei einem Directory soll der GESAMTE INHALT in die Playlist eingefügt werden
* dto. bei SHIFT+Doppelklick?

schlizbäda
