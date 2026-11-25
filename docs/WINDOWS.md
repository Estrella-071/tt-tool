# Windows installation-free portable version

English · [繁體中文](WINDOWS.zh-TW.md) · [日本語](WINDOWS.ja.md) · [한국어](WINDOWS.ko.md)

> This technical record includes historical versions and measurements. For current setup and supported workflows, see [the main guide](../README.md).

## Ordinary user

Select `tt-tool-emulator-版本号-Windows-x64.zip` in the project's GitHub Releases, completely unzip it, and double-click `启动钓鱼助手.bat`. Whether the corresponding version is already available on the download page shall be subject to the actual release of the project. Do not download the GitHub automatically generated Source code ZIP in place of the portable package.

Applicable to 64-bit Windows 10/11. The package comes with independent CPython, Tcl/Tk, NumPy, OpenCV, Pillow and MSS; there is no need to install Python, Anaconda, PyCharm or run additional pip, and there is no need to download components when starting up for the first time. LDPlayer or MuMu simulators and games still need to be prepared by yourself. The program does not modify the system Python, registry, or PATH.

`app/` in the root directory saves the complete project source code and resources, `runtime/` saves the independent running environment, and `data/` saves the local configuration, logs, screenshots and videos after running. Double-click the entry to use the isolation mode of the package interpreter, and do not read the Python package and PYTHONPATH installed by the user.

Unzip to a location writable by the current account. Do not place it in the compressed package preview window, a read-only disk, or a system directory that requires elevated privileges to write. Repeated startup of the same data directory will prompt you to switch to an already open window. Separate copies in different folders should still avoid controlling the same emulator at the same time.

For first-time use, you still need to set up space mapping, select windows, frame the entire game area, and start fishing through the start button or shortcut keys. See [README](../README.md) for operating steps.

## Updates and troubleshooting

- Update: Exit the old version first and extract the new package to a new folder. Keep the old directory backup; when you need to inherit the settings, only copy `config.json` and `speed_profile.json` in the old `data/` to `data/` in the new package. No need to create files that do not exist. When migrating from the source version, copy these two files in the project root directory. Historical screenshots and videos can continue to be retained in the old directory.
- Unable to open: Double-click `检查运行环境.bat` to retain the displayed error; the startup error is written to `data/logs/startup.log`. Don't expose unchecked error logs.
- The file is intercepted or missing: check whether it comes from the project release page, whether the verification values ​​are consistent, and then follow the system prompts; do not turn off security software as a routine step.
- Inconsistent permissions: The assistant is only considered running with the same permissions if the emulator is run as administrator.
- Share: Publish the original ZIP you built, do not re-zip the portable directory you have already used.

## Maintainer regenerates

Run from the warehouse root directory:

```bash
python build_windows.py
```

The build entry only requires the standard library of Python 3.10 or above. The first build requires an Internet connection, downloads the operating environment and Windows dependencies from the fixed list, and checks SHA-256 one by one. The files in `.build-cache/` can be reused later. The build will not read native `config.json` or bring logs, screenshots, or videos into the finished product.

The output is at `dist/tt-tool-emulator-版本号-Windows-x64.zip`. Building on a Windows host will also use the package interpreter to check Tk, ImageTk, image templates, video codecs and display interfaces; this check does not take screenshots or send keystrokes. The same portable package can be assembled on other operating systems, but binary structure and file integrity checks are not equivalent to Windows runtime verification. Before publishing, you still need to check the interface, frame selection, pause and real simulator operation on Windows.

After uploading the source code to GitHub, you can also enter **Actions → Windows portable → Run workflow**. The workflow is built and checked on a Windows machine, and a downloadable build product is provided upon success. Manually add the portable ZIP to GitHub Release after downloading; the workflow does not automatically release the release. The warehouse must contain `.github/workflows/windows-portable.yml`, and do not miss directories starting with a dot.

`packaging/windows-runtime.lock.json` Fixed dependency version, source and hash. When updating dependencies, you must also check Windows x64/Python 3.12 compatibility and licensing, and verify the actual download before updating the list; do not just change the version string. The current locked package does not have an additional `.data` installation directory for wheel; to add such dependencies, you must first expand and test the build rules.

This project uses an independent running environment directory to achieve installation-free, and does not require temporary unpacking of a single EXE file on the user's computer. Please always distribute the portal, app and runtime together. Source code is generated from an explicit file manifest; third-party binaries retain their upstream license, and the version and download source are recorded in the package `DEPENDENCIES.json`.
