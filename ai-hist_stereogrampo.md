ai-hist_stereogrampo
20250723tdwm

1. 
provide gui code that will give options to take photo pairs to produce sterograms, in red+cyan format, or side-by-side, or left-right-left;
use settings file in app-dir to retain folder choice.

images may be in a single folder [of multiple pairs], sub-dirs [similarly possibly mult pairs], or separated L + R folders;
if mult pairs in a single folder, assume first image is left, second right.

use an alignment algorithm to ensure both images of a pair are matched by rotation to be equally horizontal to each other.

provide  another option by checkbox to output .mpo files of the pairs.

place the output of each process in a duplicate folder/tree, that is appended '_3d_[source]' for stereograms, and/or likewise '_mpo_[source]';
put a log of files produced in root of source folder tree

provide another option to delete originals, with warning to confirm:

have start, pause and exit buttons;
base the theme and layout of the gui, and the buttons, on attached pair3d app.

provide complete code, with logging and docstrings;
keep log file in app-dir.


2. 
no output of mpo files; folders are present, but empty

all new folders should be in a copy of the source tree, less empty folders, named '_-3d_[source]'


3. 
after file deletion, recursively delete empty dir tree [incl. any .picasa.ini files present in otherwise empty dir's];

sbs option needs a 'reversed[crossview]' option, where the images are combined the opposite way around;

use checkbox instead of radio to allow creation of various stereogram types simultaneously;

give window a scrollbar - currently opens without start\pause\exit buttons accessible;

naming convention for created files should be, use name of first file of source pair, then;
- leave as-is for .mpo
- prepend appropriate 'rc_' for anaglyph, 'lrl_' for left-right-left, 'ii_' for standard side-by-side, or 'xi_' for reversed sbs


4. 
total count, and progress bar, need to include only files in _pairs dir's [include extra, separate, count of '_singles'?], as bar fails to finish on end of creating stereo imgs due to included count of _singles and won't exit without valid 'unfinished' warning;

why can created .mpo files not be opened by usual stereo image programs ['StereoPhoto Maker' (cannot open image) and '3dComposer Viewer' (Error loading file.)]