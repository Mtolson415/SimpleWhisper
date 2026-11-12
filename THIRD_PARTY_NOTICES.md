# Third-party notices

Original source is [MIT licensed](LICENSE). Dependencies retain upstream terms.

| Component | License information |
| --- | --- |
| Python | [Python license](https://docs.python.org/3/license.html) |
| Tcl/Tk | [License terms](https://www.tcl-lang.org/software/tcltk/license.html); existing feather resource retained |
| sounddevice / PortAudio | [sounddevice](https://github.com/spatialaudio/python-sounddevice/blob/master/LICENSE), [PortAudio](https://www.portaudio.com/license.html) |
| CFFI / pycparser | [CFFI](https://cffi.readthedocs.io/en/latest/license.html), [pycparser](https://github.com/eliben/pycparser/blob/main/LICENSE) |
| PyInstaller | [GPL with bootloader exception](https://pyinstaller.org/en/stable/license.html) |
| whisper.cpp | [MIT](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE); separate container |

The portable package preserves collected runtime files and includes build-environment Python/Tcl/Tk licenses. Weights are separate; consult upstream terms. Docker images contain separately licensed system components. Pins live in requirements, build requirements, Dockerfile, Compose and models.lock.json.
