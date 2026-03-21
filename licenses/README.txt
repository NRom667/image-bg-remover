This folder contains license texts for third-party components used by the app
or bundled into the Windows build output.

Included here:
- PyInstaller bootloader license text
- NumPy license texts bundled with the installed wheel
- Hydra Core license text
- iopath license text
- PyTorch license text
- TorchVision license text
- sam2 package license text

Notes:
- SAM2.1 model weights are not bundled with this app. They are downloaded by the
  app separately when needed.
- PySide6 / Shiboken6 are used under the Qt for Python licensing terms. The
  installed wheel metadata in this environment exposes the Qt commercial license
  notice, while the package metadata declares LGPL/GPL/commercial licensing.
  See THIRD_PARTY_LICENSES.txt for the summarized notice used by this project.
