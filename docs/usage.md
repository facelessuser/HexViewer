# User Guide {: .doctitle}
Configuring and using HexViewer.

---

# Commands
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
Shows a quick panel allowing you to select the desired hash, and then shows an input panel that allows you to specify the string to be hashed. A panel is then displayed with your generated hash according to specifications.

## Hex Viewer: Generate Hash from Selection
Allows you to generate hashes from your current selection(s).  Multi-select regions' content will be combined and evaluated together.  If a region contains newlines, they will be hashed as well.

## Hex Viewer: Abort (Hex Conversion|Export|Checksum)
Abort the given action.

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
