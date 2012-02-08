# About
Hex Viewer is a plugin for Sublime Text 2 that allows the toggling of a file into a hex viewing mode.  Hex Viewer also supports hex editing.

<img src="http://dl.dropbox.com/u/342698/HexViewer/preview.png" border="0"/>

# Installation 
- Download is available in Package Control or you can download or clone directly and drop into your Sublime Text 2 packages directory (plugin folder must be named HexViewer)
- You may need to restart Sublime Text 2 after installation

# Features
- Toggling a file into hex view mode
- Search bytes by address
- Customizable highlight of byte and corresponding ASCII representation
- Customizable byte grouping and bytes per line
- Hex inspector to view current selected bytes as different unit types (endianness is configurable.)
- Display total selected number of bytes and addresses of first group of consecutive bytes in status bar
- Hex editing
- Checksumming of files
- Generate a hash from a entered string or selection
- Auto open binary files in Hex Viewer (disabled by default)

# Commands

## Overview
There are 10 commands available via the command palette or by key-bindings.

- Hex Viewer: Toggle Hex View
- Hex Viewer: Show Hex Inspector
- Hex Viewer: Toggle Endianness (Big|Little)
- Hex Viewer: Set Bits Per Group
- Hex Viewer: Set Bytes Per Line
- Hex Viewer: Find By Address
- Hex Viewer: Show Hex Edit Panel
- Hex Viewer: Discard All Edits
- Hex Viewer: Export Bin
- Hex Viewer: Get Checksum
- Hex Viewer: Generate Hash

## Hex Viewer: Toggle Hex View
Toggle file in or out of hex view

## Hex Viewer: Show Hex Inspector
Show the Hex Inspector panel.  The Hex Inspector is a panel which shows the current selected byte as different unit types: byte (8 bit), short(signed 8 bit), word (16 bit), int (signed 16 bit), dword (double word 32 bit), longint (signed 32 bit), float (32 bit floating point), double (floating point 64 bit), and binary (8 bit binary).

## Hex Viewer: Toggle Endiannes (Big|Little)
Toggle the parsing of bytes to big or little endian when showing unit types in Hex Inspector

## Hex Viewer: Set Bits Per Group
Allows selection from the quick panel the grouping of bytes by 8, 16, 32, 64, and 128 bits.  This will reload the file with this formatting.  All edits will be lost, so export your changes before you do this.

## Hex Viewer: Set Bytes Per Line
Allows selection form the quick panel the the number of bytes to be shown on a line: 8, 10, 16, 24, 32, 48, 64, 128, 256, 512.  If the selected value is not divisible by the "bits per group", the closet number of bytes per line will be used.

## Hex Viewer: Find By Address
Find the byte at the specified address.  Input is received through the input panel.

## Hex Viewer: Show Hex Edit Panel
Invoking this command will take the currently selected bytes on a line and display them in an input panel.  They can then be modified and submitted to replace the original bytes.  Strings can also be used by using the "s:" prefix followed by the equivalent ASCII characters that are to replace the selected bytes.

## Hex Viewer: Discard All Edits
If at any time you would like to discard all of the changes you have currently made to the hex view, you can invoke this command, and a clean hex view will be reloaded.

## Hex Viewer: Export Bin
This command exports the current hex view to a binary file, and if the option is enabled, it will display the checksum of the newly generated binary file.

## Hex Viewer: Run Checksum
By default, it opens up a quick panel with all available hashes that can be used as a checksum.  When an algorithm is selected, it is used to retrieve the checksum for the current file in hex view mode.

## Hex Viewer: Generate Hash
Shows a quick panel allowing you to select the desired hash, and then shows an input panel that allows you to specify the string to be hashed. A panel is then displayed with your generated hash accoriding to specifications.

## Hex Viewer: Generate Hash from Selection
Allows you to genrate hashes from your current selection(s).  Multiselect regions' content will be combined and evaluated together.  If a region contains newlines, they will be hashed as well.

# Configurable settings
Settings are configurable in the hex_viewer.sublime-settings file.

- configure byte highlight color, icon, and style
- configure edit highlight color, icon, and style
- set default bits per group
- set default bytes per line
- custom font and font size
- whether to auto show the Hex Inspector panel on hex view load
- whether Hex Inspector is enabled at all
- hash algorithm to use when checksumming
- whether to checksum on file export automatically
- enable/disable auto open of specified binary files

# Source Code
https://github.com/facelessuser/HexViewer/zipball/master

# License

Hex Viewer is released under the MIT license.

Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Version 1.6
- Report Tiger-192 as big endian as most hashing programs do

# Version 1.5
- Allow the hashing of current selection(s).  Multiselect regions's content will be combined and evaluated together
- Update hash progress quicker
- Chunk hashes entered in the input panel in case very large amounts of data are pasted in

# Version 1.4
- Fix issue where some selections will select an extra hex char that is not really selected
- Update missing item from changelog

# Version 1.3
- Decrease debounce threads to one

# Version 1.2
- Auto open specified binary files in Hex Viewer (disabled by default)

# Version 1.1
- Add MD2 so Windows OS can find it (Mac and Linux do not have this one; Mac uses MDC2 for some reason)

# Version 1.0
- Allow unicode text in "Generate Hash"

# Version 0.9
- String to hash not always working now fixed
- Fixes for when certain hashes are not found

# Version 0.8
- New hash algorithms: Whirlpool and Tiger-192
- Checksums are now threaded
- Exposed new command to tap into hashes called "Hex Viewer: Generate Hash"
- Rework logic to determine which hashes are available

# Version 0.7
- New hash algorithms from openssl: sha, mdc2, md4, ripemd160 (dynamcially added if system supports them)
- Rename "Get Checksum" command to "Run Checksum"
- When invoking shortcut or command for checksumming, show quick panel with all valid hash algorithms to choose from

# Version 0.6
- Commands accessible from menu Tools > Packages > Hex Viewer
- Fix checksum not responding to settings change
- Add CRC32 and ADLER32 hash algorithms for checksums

# Version 0.5
- New progress animation in status bar when reading bin file
- Setting to enable or disable highlight throttling (default is disabled)
- Don't display incorrect byte count when highlight is throttled
- Get hex char range only once
- Better highlighting of edits
- A little cleanup

# Version 0.4
- Hide Inspector tmLanguage file
- Chunk checksum and export for faster, more linear performance with large files
- Thread binary file reading and show progress of bytes parsed in status bar
- If hex view command is issued while a file is being converted, abort the conversion
- Simplify logic with hex view; always close original tab and load in new one opposed to conditional logic (easier with threading)
- Add setting to throttle highlighting selected bytes
- Add divider in settings menu

# Version 0.3
- On export, rename tab to new export name
- Fix checksum failing when passing certain data through Sublime Text run_command API
- Account for NaNs in floats and doubles in Hex Inspector

# Version 0.2
- Fix issue where large blocks get highlighted when the end of line is selected
- Add checksum command (also runs when export is made)

# Version 0.1
- Initial release
