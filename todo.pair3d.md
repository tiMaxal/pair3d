to do:
- [done] `start` button
- [done] progress bar
- [done] show no. of files being processed
- [done] `pause` button
- [done] also cause 'pause' to pause timer
- [done] `exit` button
- [done] process subfolders
- [done] allow setting values for TIME_DIFF_THRESHOLD + HASH_DIFF_THRESHOLD
- action 'alt' for keyboard control
- [show folder contents in 'chooser', ie whether images exist there]
- [done] move progress bar below timer\filecount lines
   [instead of showing info at ends of bar]
- integrate 'mov3dpairs'
- Cross-platform support: Windows and Linux [+ mac?]
- i8n .. lang's 
    - DE
    - FR
    - IT
    - ES
    - JP
    - CH\ZH 


Package as:
- Windows .exe (standalone)
- Debian .deb package

[
    update readme
 - "`pair3d` is a cross-platform GUI tool .. "
 ]
 __Installation__
Windows:
- Download the latest pair3d.exe from the Releases section.
- Run the executable. No installation required.

Linux (Debian/Ubuntu):
- Download the latest pair3d.deb from the Releases section.
- Install the package:
`bash`
`Copy`
`Edit`
`sudo dpkg -i pair3d.deb`
  Launch pair3d from your applications menu or by running pair3d in the terminal.

 __Usage__
- Launch pair3d.
- Click on the "Browse" button to select the folder containing your images.
- The tool will process the images and display the number of pairs and singles found.
- Check the pairs/ and singles/ folders created inside your selected directory.

[Screenshots]

  *Main interface of pair3d*

  *Results after processing images.*



- pipe folder of pairs to `StereoPhotoMaker` for processing to stereogram images
   [anaglyph \ sbs \ uni]



__✅ Usage Instructions (when icons are in imgs/ folder)__


*🔧 PyInstaller .exe (Windows)*
- Makefile entry:

make
exe:
	pyinstaller --onefile --windowed --icon=imgs/pair3d.ico pair3d.py

*🐧 .desktop launcher (Linux)*
- Create pair3d.desktop and reference the PNG:

ini:
[Desktop Entry]
Type=Application
Name=pair3d
Exec=pair3d
Icon=imgs/pair3d.png
Terminal=false
Categories=Graphics;

- Then install with -
bash:
cp pair3d.desktop ~/.local/share/applications/

*🍎 macOS app bundling (Py2app or manual)*
- Use the .icns icon -
bash:
--iconfile imgs/pair3d.icns
