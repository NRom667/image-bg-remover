# Background Remover
This app removes the background from an image and saves it as a transparent PNG.

**Click below to open the demo video**
[![Demo Video](<images/スクリーンショット.png>)](https://vimeo.com/1177951381?share=copy&fl=sv&fe=ci)

# Features
- Add foreground / background points to fine-tune the cutout area
  - If detailed adjustment is unnecessary, Microsoft Paint included with Windows can be convenient
- High-accuracy segmentation powered by SAM2.1
  - SAM2.1 can be downloaded from within the app

# Download
You can download it from the [Releases page](https://github.com/NRom667/image-bg-remover/releases).

Please download the latest file ending with `.7z`.
![How to download](<images/ダウンロード方法.png>)

# Support the Author
If this software is useful to you, support via OFUSE would be appreciated.
It helps support future improvements and updates.

[Support the author on OFUSE](https://ofuse.me/rom1234)

# Detailed Functions
- Load JPG / PNG images
- Add foreground / background points
- Model selection: SAM2.1 tiny, small, base+, large
- Choose whether to blur mask edges and adjust the blur amount
- Save as a transparent PNG

# Supported Environment
- Windows 11

# Technologies Used
- Python
- PySide6: GUI rendering
- meta/SAM2.1: image segmentation
  - CPU processing only

# About AI Usage
Codex was used in the development of this app.

# Build Notes / Commands
- To run directly without building: `python main.py`
- To build: run `scripts\build_windows.ps1`
- Version information: described in `src\__init__.py`

# License
- See `LICENSE` for the license of this application itself.
- See `THIRD_PARTY_LICENSES.txt` for third-party license information.
