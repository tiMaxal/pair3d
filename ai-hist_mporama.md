grok20250808tdwm

1. provide complete code for a python gui app that will take .mpo files from a user designated location [by folder finder], to output stereogram formats [anaglyph, side-by-side crossview, SBS parallel view, single R and/or L, LRL] designated by checkbox, to be saved in user-defined folder [default to, created '_x2' folder in source dir];
have a checkbox to include sub-directories;
if sub-dir's true, radio button choice to save output in chosen/default root folder, or each treated sub-dir [create copy of tree if in other than source tree, no folder created if no .mpo present];
use original filename with prefix, for each format ..
- rc = anaglyph
- xi = crossview
- ii = parallel
- lrl = Left-Right-Left
use suffix for singles, '_r' or '_l' appropriately;
include horizontally adjacent 'start' and 'exit' buttons at the bottom

2. proffer name for app, not seen elsewhere, short, 'catchy', descriptive
   ['stereosnap']
   - from chatgpt:
       - Here are a few short, “catchy but descriptive” name ideas that I can’t find in use elsewhere for stereo MPO-to-stereogram conversion:
          - MPOx2 – plays on “MPO” + “times two” (two frames) and output formats.
          - Stereoforge – suggests crafting stereo images.
          - Anaglyfix – catchy, hints at fixing/making anaglyphs.
          - DepthMint – fresh “minting” of depth images.
          - Twinview – twin images for stereo viewing.
          - Parallaxer – built around the parallax concept.
          - FrameMeld – merging left/right frames.
          - DepthSmith – artisanal depth-image creation.
          - X2View – “times two” view; quick and memorable.
          - Optix2 – optics + x2, short and techy.
    [give only options that contain 'mpo' - tdwm]
      - Here’s a focused list of short, catchy, descriptive names that all contain “mpo” and aren’t in use elsewhere:
          - mpomorph – morph your MPOs into new formats.
          - mpoview – view MPOs in multiple stereogram styles.
          - mpomagic – MPO transformations made easy.
          - mpomate – your friendly MPO companion tool.
          - mpomix – mix MPOs into various stereo formats.
          - mpomake – make outputs from your MPO files.
          - mpoforge – forge new images from MPO sources.
    [try to amalgamate 'mpo' into a word [does not nave to be at start] - ensure not used as project/repo name on github -tdwm]
        names that embed “mpo” anywhere in the word, and ensure they appear unused as GitHub project or repository names based on a quick search.
          - Temporama – like “panorama,” but with mpo in the middle; suggests immersive stereo views.
          - Amphorama – blends mpo into “amphora” or “panorama,” implying stereo imagery.
          - Compomate – includes mpo; hints at composing MPO files into new outputs.
          - Impovue – wraps mpo into “improve” or “improvise,” with a “view” twist.
          - Promograph – embeds mpo into “monograph” or “photograph”; evokes stereo imagery.
          - Campolex – contains mpo; a techy-sounding name suggesting complexity or multiplexing.

3. currently considering app names 'MPOrtx' 'MPOrama';
provide checkbox option 'separate to formats', for folders named for each prefix\suffix [under '_x2', whether at root or in sub-dirs];
swap positions of xi + lrl checkboxes;
put root/subs radio buttons below sub-dir's checkbox [keep radios greyed until checkbox activated];
use color scheme [incl. buttons] + progress bar / time / filecount from attached app

4. radio buttons not visible until checkbox activated - should be able to be seen but grayed out [to prevent gui layout 'jump'];
'separate to formats' should be below radios;
make input/output boxes [that contain folder path text] background and border light-blue;
provide 'total' filecount on selection of input dir [and update on check/uncheck 'process sub-dirs'];
do not create unused format folders;
provide logging and add full docstrings

5. needed 'import sys' at top of code;
option needed for having prefix/suffix added to filename, even when in separated dir's [place beside 'format folders' labelled 'no filename change', default false - if not activated, give all output files prefix/suffix of format];
radio buttons should be text blue and bg lightcoral

7. format folders don't need '_' in the naming conventions [only the filename prefix/suffix naming]

8. create a readme for the app

9.  after 'select output formats', provide checkboxes for 
`retain metadata if present:
    Exif    IPTC    XMP`;
also toggles for 'all'/'none';
default checked for exif and xmp;

10. retain current user settings in file [associate by app-name];
progress bar total/processed should be a multiple of .mpo filecount [depending on formats checked to process];
exif is not transferring fully [ie, no Copyright], xmp none at all, likewise iptc transfers none

[various issues with metadata transfer failure - tdwm]

11. IPTC of input files not empty - content of the previously attached sample:
By-line: tiMaskal fotWograf.com
CopyrightNotice: Copyright © 2019 by tiMaskal fotWograf.com All Rights Reserved

XMP may be extracted, but has not been written to the output file[s];
now exif only written to file of first checkbox format, others blank

adapt code to using exiftool-py?