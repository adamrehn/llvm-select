LLVM/Clang Library Version Selector Tool
========================================

`llvm-select` is designed to simplify the management of side-by-side installations of multiple versions of the LLVM and Clang development libraries. `llvm-select` provides the ability to easily build any version of LLVM/Clang from source, and select which installed version is reported to build tools by the `llvm-config` command.

**Installers are available for Windows, macOS, and Linux from the [Releases page](https://github.com/adamrehn/llvm-select/releases).**


Contents
--------

- [Prerequisites](#prerequisites)
- [Installing library versions](#installing-library-versions)
- [Selecting the active library version](#selecting-the-active-library-version)
- [Viewing the list of installed library versions](#viewing-the-list-of-installed-library-versions)
- [Removing an installed library version](#removing-an-installed-library-version)
- [Compatible library versions](#compatible-library-versions)
- [Generating the installer](#generating-the-installer)
- [License](#license)


Prerequisites
-------------

The following tools are required to be in the system PATH:

- [Python](https://www.python.org/) 3.x
- [CMake](https://cmake.org/)
- [Curl](https://curl.haxx.se/)
- `tar` under macOS and Linux (under Windows, the slower Python `tarfile` library is used instead)
- A C++11-compliant compiler:
    - GCC or Clang under macOS and Linux
    - Either GCC (through MinGW) or Visual Studio under Windows

Under macOS and Linux, if [Ninja](https://ninja-build.org/) is available, it will be used to speed up compilation. Due to issues compiling some versions of LLVM/Clang with Ninja under Windows, Ninja is not used under Windows even if it is available.


Installing library versions
---------------------------

To install a new version of the LLVM/Clang libraries, use the following command (`sudo` is not required under Windows):

```
sudo llvm-select --install VERSION BULDTYPE
```

Where `VERSION` is the desired version number, and `BUILDTYPE` is one of the [supported CMake build types for LLVM](http://llvm.org/docs/CMake.html#frequently-used-cmake-variables):

- `Release` (the default if no build type is explicitly specified)
- `Debug`
- `RelWithDebInfo`
- `MinSizeRel`

The requested version will be downloaded and built from source, and installed to the following location:

- `/usr/local/llvm/VERSION-BUILDTYPE` under macOS and Linux
- `C:\llvm\versions\VERSION-BUILDTYPE` under Windows (if you used the default installation directory when you first ran the installer)

For example, for a release build of LLVM/Clang 3.9.0, the installed location would be `/usr/local/llvm/3.9.0-Release` or `C:\llvm\versions\3.9.0-Release`, respectively.


Selecting the active library version
------------------------------------

To make a particular version of the LLVM/Clang libraries the "active" one (the one reported by the `llvm-config` command), use the following command (again, `sudo` is not required under Windows):

```
sudo llvm-select VERSION BUILDTYPE
```

For example, to set the release build of LLVM/Clang 3.9.0 to be the active version, you would use `sudo llvm-select 3.9.0-Release`.

The mechanism used to redirect `llvm-config` is platform-specific:

- Under macOS and Linux, a symlink is created at `/usr/local/bin/llvm-config` pointing at `/usr/local/llvm/VERSION-BUILDTYPE/bin/llvm-config`.
- Under Windows, the batch script `C:\llvm\bin\llvm-config.cmd` is written to execute `C:\llvm\versions\VERSION-BUILDTYPE\bin\llvm-config.exe`.


Viewing the list of installed library versions
----------------------------------------------

To view the list of library versions that are currently installed, use the command:

```
llvm-select --list
```


Removing an installed library version
-------------------------------------

To remove a library version that is currently installed, use the command (again, `sudo` is not required under Windows):

```
sudo llvm-select --remove VERSION BUILDTYPE
```


Compatible library versions
---------------------------

The minimum supported version of LLVM/Clang that can be built from source using `llvm-select` is **LLVM 2.6**. This is the first release to include the source tarball for Clang.


Generating the installer
------------------------

To generate the installation package for `llvm-select` for your platform, simply run the `generate-installer.py` script in the `installer` directory.

Under macOS and Linux, [fpm](https://github.com/jordansissel/fpm) is required to be in the PATH. `fpm` will be invoked to generate a `.pkg` file under macOS, and either a `.deb` file under Debian-based Linux distributions or an `.rpm` file under RPM-based Linux distributions.

Under Windows, the [Nullsoft Scriptable Install System (NSIS)](http://nsis.sourceforge.net/) is required to be in the PATH. (Either the original 32-bit version or the [64-bit version](https://bitbucket.org/dgolub/nsis64) will work.) `makensis` will be invoked to generate the installer `.exe` file.


License
-------

Copyright &copy; 2016, Adam Rehn. Licensed under the MIT License. See the file [LICENSE](https://github.com/adamrehn/llvm-select/blob/master/LICENSE) for details.
