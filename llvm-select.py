#!/usr/bin/env python3
#  
#  LLVM-Select
#  
#  Copyright (c) 2016 Adam Rehn
#  
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#  
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#  
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
import argparse, glob, os, platform, re, shutil, stat, subprocess, sys, tarfile

# Exception class for representing when a required command is not available
class CommandNotAvailableError(Exception):
	def __init__(self, command):
		self.command = command

# Utility functionality
class Utility:
	
	# Writes the contents of a file
	@staticmethod
	def putFileContents(filename, data):
		f = open(filename, 'w', encoding='utf8')
		f.write(data)
		f.close()
	
	# Fix for Windows-related issues in shutil.rmtree() under some versions of Python
	# From: <https://bitten.edgewall.org/ticket/253>
	# "Catch shutil.rmtree failures on Windows when files are read-only, and only remove if root exists."
	@staticmethod
	def _rmtree(root):
		def _handle_error(fn, path, excinfo):
			os.chmod(path, 0o666)
			os.chmod(path, stat.S_IWRITE)
			fn(path)
		if os.path.exists(root):
			return shutil.rmtree(root, onerror=_handle_error)
	
	# Removes a file or directory if it exists
	@staticmethod
	def removeIfExists(item):
		if os.path.lexists(item):
			if os.path.isdir(item):
				if platform.system() == 'Windows':
					Utility._rmtree(item)
				else:
					shutil.rmtree(item)
			else:
				os.unlink(item)
	
	# Determines if a command can be run successfully
	@staticmethod
	def commandSucceeded(command):
		try:
			proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			(stdout, stderr) = proc.communicate(None)
			return True if (proc.returncode == 0) else False
		except:
			return False
	
	# Executes a command, and throws an exception if it fails
	@staticmethod
	def runOrFail(command, cwd=None, env=None, input=None, showOutput=False, suppressOutputOnError=False):
		proc = subprocess.Popen(
			command,
			stdout=(subprocess.PIPE if showOutput == False else None),
			stderr=(subprocess.PIPE if showOutput == False else None),
			stdin=subprocess.PIPE,
			universal_newlines=True,
			cwd=cwd,
			env=env
		)
		(stdout, stderr) = proc.communicate(input)
		if (proc.returncode != 0):
			if showOutput == False and suppressOutputOnError == False:
				print(stdout)
				print(stderr)
			raise Exception('Command ' + str(command) + ' failed with exit code ' + str(proc.returncode))
	
	# Verifies that the specified command is available, and throws an exception if it is not
	@staticmethod
	def errorIfNotAvailable(command, versionFlag='--version'):
		if Utility.commandSucceeded([command, versionFlag]) == False:
			raise CommandNotAvailableError(command)

# Represents all of the information we need for building a specific version of LLVM and Clang
class LLVMVersionDetails:
	def __init__(self, major, minor, revision):
		self.major = major
		self.minor = minor
		self.revision = revision
		self._populateFields()
	
	def __str__(self):
		s = str(self.major) + '.' + str(self.minor)
		if self.revision != None:
			s = s + '.' + str(self.revision)
		return s
	
	# "Private" helper method for the methods below
	def _tarballVersionString(self, tarballName):
		
		# For LLVM 3.4.1 and 3.4.2, the version numbers for compiler-rt and libcxx are still just 3.4
		if tarballName in ['compiler-rt', 'libcxx'] and (self.major == 3 and self.minor == 4):
			return str(self.major) + '.' + str(self.minor)
		
		# For all other releases, all version numbers are properly synchronised
		return str(self)
	
	# Constructs the download URL for the specified tarball source
	def tarballURL(self, tarballName):
		if self.tarballs[tarballName] == None:
			return None
		
		return 'http://llvm.org/releases/' + self._tarballVersionString(tarballName) + '/' + self.tarballFilename(tarballName)
	
	# Constructs the filename for the specified tarball source
	def tarballFilename(self, tarballName):
		tarball = self.tarballs[tarballName]
		if tarball != None:
			return tarball + '-' + self._tarballVersionString(tarballName) + self.extension
		
		return None
	
	@staticmethod
	def fromVersionString(versionString):
		
		# Attempt to parse the version string
		try:
			version = list([int(v) for v in versionString.split('.')])
		except:
			return None
		
		# Check that the version string has either two or three components
		if len(version) < 2 or len(version) > 3:
			return None
		
		# Check that none of the components are negative numbers
		for v in version:
			if v < 0:
				return None
		
		# The minimum supported version is 2.6, which first added the source tarball for clang
		if version[0] < 2 or (version[0] == 2 and version[1] < 6):
			return None
		
		# 3.4.1 is the first version to include a revision number
		if len(version) == 3 and (version[0] < 3 or (version[0] == 3 and version[1] < 4)):
			return None
		
		# All versions after 3.4 require a revision number
		if len(version) == 2 and (version[0] > 3 or (version[0] == 3 and version[1] > 4)):
			return None
		
		# Construct an object to represent the details of the parsed version number
		return LLVMVersionDetails(version[0], version[1], version[2] if len(version) == 3 else None)
	
	# "Private" method for populating our detail fields based on the version number
	def _populateFields(self):
		self.extension = self._determineExtenion()
		self.tarballs = self._listTarballs()
	
	# Determines the file extension of the source tarballs for this LLVM version
	def _determineExtenion(self):
		
		# Versions 2.7 through to 2.9 use the extension .tgz,
		# Versions 2.6 and 3.0 use the extension .tar.gz,
		# Versions 3.1 through to 3.4.2 use .src.tar.gz,
		# Versions 3.5.0 and onwards use .src.tar.xz
		if self.major == 2 and self.minor > 6:
			return '.tgz'
		elif (self.major == 2 and self.minor == 6) or (self.major == 3 and self.minor == 0):
			return '.tar.gz'
		elif self.major == 3 and self.minor < 5:
			return '.src.tar.gz'
		else:
			return '.src.tar.xz'
	
	# Determines the list of source tarballs for this LLVM version
	def _listTarballs(self):
		
		# All versions have an LLVM tarball
		tarballs = {}
		tarballs['llvm'] = 'llvm'
		
		# Versions 2.6 through 3.2, and 3.4, name the clang tarball "clang"
		# Versions 3.3, and 3.5.0 and onwards, name it "cfe"
		if self.major < 3 or (self.major == 3 and (self.minor < 3 or (self.minor == 4 and self.revision == None))):
			tarballs['clang'] = 'clang'
		else:
			tarballs['clang'] = 'cfe'
		
		# Version 3.1 and onwards include compiler-rt, which we build under macOS and Linux
		tarballs['compiler-rt'] = None
		if platform.system() != 'Windows' and (self.major > 3 or (self.major == 3 and self.minor >= 1)):
			tarballs['compiler-rt'] = 'compiler-rt'
		
		# Version 3.3 and onwards include libc++, which we only build under macOS
		tarballs['libcxx'] = None
		if platform.system() == 'Darwin' and (self.major > 3 or (self.major == 3 and self.minor >= 3)):
			tarballs['libcxx'] = 'libcxx'
		
		return tarballs

# Provides functionality for building LLVM/Clang from source
class LLVMBuilder:
	
	# The list of valid CMake build types for LLVM
	CmakeBuildTypes = ['Release', 'Debug', 'RelWithDebInfo', 'MinSizeRel']
	
	def __init__(self, version):
		self.version = version
	
	# Cleans up the files from a build, even if it was interrupted
	@staticmethod
	def cleanupFiles(version):
		for tarballName in version.tarballs:
			tarball = version.tarballFilename(tarballName)
			if tarball != None:
				Utility.removeIfExists(os.getcwd() + '/' + tarball)
				Utility.removeIfExists(os.getcwd() + '/' + tarballName + '-src')
	
	# "Private" method to download and unpack a source tarball
	def _downloadAndUnpackTarball(self, tarballName, destinationDir, cleanup=True, showProgress=True):
		
		# Download the source tarball
		url = self.version.tarballURL(tarballName)
		filename = os.getcwd() + '/' + self.version.tarballFilename(tarballName)
		Utility.runOrFail(['curl', '-f', url, '-o', filename], showOutput=showProgress)
		
		# Unpack the tarball
		# (Under Windows, we use the slower Python tarfile library to avoid a dependency the `tar` command)
		if platform.system() == 'Windows':
			with tarfile.open(filename) as tar:
				
				# Determine the top-level directory that the extracted files will reside in
				rootDir = (tar.getnames())[0]
				while (os.path.dirname(rootDir) != ''):
					rootDir = os.path.dirname(rootDir)
				
				# Extract the files and rename the top-level directory
				tar.extractall()
				shutil.move(os.getcwd() + '/' + rootDir, destinationDir)
		else:
			os.makedirs(destinationDir)
			Utility.runOrFail(['tar', '-xvf', filename, '-C', destinationDir, '--strip-components=1'])
		
		# Perform cleanup
		if cleanup == True:
			os.unlink(filename)
	
	# Verifies that all of the prerequisites for building LLVM/Clang from source are met
	def verifyBuildPrerequisitesMet(self):
		Utility.errorIfNotAvailable('curl')
		Utility.errorIfNotAvailable('cmake')
		if platform.system() != 'Windows':
			Utility.errorIfNotAvailable('tar')
	
	# Downloads and extracts the LLVM source tarballs
	def download(self, showProgress=True):
		
		# Download, unpack, and remove the source tarballs
		for tarballName in self.version.tarballs:
			if self.version.tarballs[tarballName] != None:
				dir = os.getcwd() + '/' + tarballName + '-src'
				self._downloadAndUnpackTarball(tarballName, dir, showProgress=showProgress)
		
		# Move the extracted directory for clang into place
		shutil.move(os.getcwd() + '/clang-src', os.getcwd() + '/llvm-src/tools/clang')
		
		# Move the extracted directories for the optional components into place
		if self.version.tarballs['compiler-rt'] != None:
			shutil.move(os.getcwd() + '/compiler-rt-src', os.getcwd() + '/llvm-src/projects/compiler-rt')
		if self.version.tarballs['libcxx'] != None:
			shutil.move(os.getcwd() + '/libcxx-src', os.getcwd() + '/llvm-src/projects/libcxx')
	
	# Builds LLVM from the extracted source
	def build(self, buildType, installationRoot, showProgress=True, cleanup=True):
		
		# Create the build directory inside of the LLVM root source directory
		buildDir = os.getcwd() + '/llvm-src/build'
		os.makedirs(buildDir)
		
		# Determine the installation directory location
		installDir = installationRoot + os.sep + str(self.version) + '-' + buildType
		
		# Determine which CMake generator we are using for the current platform
		# (Note that Ninja can have some issues under Windows with certain LLVM versions, so we don't use it)
		# (Note also that under Windows when MinGW g++ is available, we prefer it over cl.exe)
		cmakeGenerator = 'Unix Makefiles'
		if platform.system() != 'Windows' and Utility.commandSucceeded(['ninja', '--version']) == True:
			cmakeGenerator = 'Ninja'
		elif platform.system() == 'Windows' and Utility.commandSucceeded(['g++', '-v']) == False:
			cmakeGenerator = 'NMake Makefiles'
		
		# When compiling under Windows with MinGW, running tblgen.exe can fail if libstdc++-6.dll cannot be found,
		# so we need to build llvm-tblgen and clang-tblgen with flags to statically link against libgcc and libstdc++
		extraCmakeFlags = []
		if platform.system() == 'Windows' and Utility.commandSucceeded(['g++', '-v']) == True:
			
			# Create a build directory for tblgen
			buildDirTG = os.getcwd() + '/llvm-src/build-tblgen'
			os.makedirs(buildDirTG)
			
			# Run cmake with the extra flags
			env = os.environ.copy()
			env['LDFLAGS']  = env.get('LDFLAGS', '')  + ' -static-libgcc -static-libstdc++'
			env['CXXFLAGS'] = env.get('CXXFLAGS', '') + ' -static-libgcc -static-libstdc++'
			env['CFLAGS']   = env.get('CFLAGS', '')   + ' -static-libgcc'
			Utility.runOrFail([
				'cmake',
				'-DCMAKE_BUILD_TYPE=' + buildType,
				'-DLLVM_INCLUDE_TESTS=false',
				'-G', cmakeGenerator,
				'..'
			], cwd=buildDirTG, showOutput=showProgress, env=env)
			
			# Build llvm-tblgen and clang-tblgen
			Utility.runOrFail(['cmake', '--build', '.', '--target', 'llvm-tblgen'], cwd=buildDirTG, showOutput=showProgress)
			Utility.runOrFail(['cmake', '--build', '.', '--target', 'clang-tblgen'], cwd=buildDirTG, showOutput=showProgress)
			
			# Use the pre-built tblgen during the subsequent compilation
			extraCmakeFlags = [
				'-DLLVM_TABLEGEN=' + buildDirTG + '/bin/llvm-tblgen.exe',
				'-DCLANG_TABLEGEN=' + buildDirTG + '/bin/clang-tblgen.exe'
			]
		
		# Generate the makefile
		Utility.runOrFail([
			'cmake',
			'-DCMAKE_INSTALL_PREFIX=' + installDir,
			'-DCMAKE_BUILD_TYPE=' + buildType,
			'-DLLVM_ENABLE_EH=true',
			'-DLLVM_ENABLE_RTTI=true',
			'-DLLVM_INCLUDE_TESTS=false'
		] + extraCmakeFlags + [
			'-G', cmakeGenerator,
			'..'
		], cwd=buildDir, showOutput=showProgress)
		
		# Perform the build and install it
		Utility.runOrFail(['cmake', '--build', '.'], cwd=buildDir, showOutput=showProgress)
		Utility.runOrFail(['cmake', '--build', '.', '--target', 'install'], cwd=buildDir, showOutput=showProgress)
		
		# As a follow-up to the tblgen.exe related fix above, copy the correct version of libstdc++-6.dll to the bin directory
		# (We do it this way for everything other than tblgen.exe because the flags for statically linking libstdc++ can break other parts of the LLVM/Clang compilation)
		if platform.system() == 'Windows' and Utility.commandSucceeded(['g++', '-v']) == True:
			proc = subprocess.Popen(['where', 'g++'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
			(stdout, stderr) = proc.communicate(None)
			dllPath = os.path.dirname(stdout.strip()) + '/libstdc++-6.dll'
			if os.path.exists(dllPath):
				shutil.copy2(dllPath, installDir + '/bin/libstdc++-6.dll')
		
		# Perform cleanup
		if cleanup == True:
			LLVMBuilder.cleanupFiles(self.version)
		
		# Return the installation directory
		return installDir

# Represents the main functionality of llvm-select itself
class LLVMSelect:
	
	# Determines the installation directory for library versions under the current platform
	@staticmethod
	def getInstallationDir():
		if platform.system() == 'Windows':
			return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '\\versions'
		else:
			return '/usr/local/llvm'
	
	# Retrieves the list of installed library versions
	@staticmethod
	def getInstalledVersions():
		versions = []
		for item in glob.glob(LLVMSelect.getInstallationDir() + '/*'):
			itemName = os.path.basename(item)
			match = re.match('[0-9]\\..+-(.+)', itemName)
			if os.path.isdir(item) and match != None and match.group(1) in LLVMBuilder.CmakeBuildTypes:
				versions.append(itemName)
		return versions
	
	# Removes an existing installed library version
	@staticmethod
	def removeLibraryVersion(llvmVersion, buildType):
		libraryDir = LLVMSelect.getInstallationDir() + os.sep + llvmVersion + '-' + buildType
		shutil.rmtree(libraryDir)
		print('Removed `' + libraryDir + '`.')
	
	# Sets the specified library version as the active library version
	@staticmethod
	def setActiveLibraryVersion(llvmVersion, buildType):
		if platform.system() == 'Windows':
			
			# Under Windows, write the batch file to call the correct version of llvm-config
			versionsRoot = LLVMSelect.getInstallationDir()
			exeLocation = versionsRoot + '\\' + llvmVersion + '-' + buildType + '\\bin\\llvm-config.exe'
			batLocation = os.path.dirname(versionsRoot) + '\\bin\\llvm-config.cmd'
			Utility.putFileContents(batLocation, '@echo off\n"' + exeLocation + '" %*')
			print('Set llvm-config to point to `' + exeLocation + '`.')
			
		else:
			
			# Under macOS and Linux, simply update the symlink for llvm-config
			llvmConfigPath = LLVMSelect.getInstallationDir() + '/' + llvmVersion + '-' + buildType + '/bin/llvm-config'
			symlinkPath = '/usr/local/bin/llvm-config'
			Utility.removeIfExists(symlinkPath)
			Utility.runOrFail(['ln', '-s', llvmConfigPath, symlinkPath])
			print('Set llvm-config to point to `' + llvmConfigPath + '`.')

if __name__ == '__main__':
	
	# Parse command-line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('--list',       action='store_true', help='List installed library versions')
	parser.add_argument('--remove',     action='store_true', help='Remove an installed library version')
	parser.add_argument('--install',    action='store_true', help='Install a new library version')
	parser.add_argument('--no-cleanup', action='store_true', help='Don\'t remove build files after installing a new library version')
	parser.add_argument('version',      default='', nargs='?', help='LLVM version')
	parser.add_argument('buildtype',    default='Release', nargs='?', help='Build type (' + (', '.join(LLVMBuilder.CmakeBuildTypes)) + ')')
	args = parser.parse_args()
	
	# Verify that the specified build type is a valid value
	if args.buildtype not in LLVMBuilder.CmakeBuildTypes:
		print('Error: invalid build type "' + args.buildtype + '"')
		print('Valid build types: ' + ', '.join(LLVMBuilder.CmakeBuildTypes))
		sys.exit(1)
	
	# Parse the specified LLVM version string (if any)
	version = LLVMVersionDetails.fromVersionString(args.version)
	
	# For all other arguments than `--list`, we require a valid LLVM version to be specified
	if args.list == False and args.version == '':
		print('Error: you must specify an LLVM version.')
		sys.exit(1)
	elif args.list == False and version == None:
		print('Error: unsupported LLVM version "' + args.version + '".')
		sys.exit(1)
	
	# Determine if we are adding, removing, listing, or selecting a library version
	if args.list == True:
		
		# Retrieve the list of installed versions and display them to the user
		versions = LLVMSelect.getInstalledVersions()
		if len(versions) > 0:
			print('Installed library versions:')
			print('\n'.join(versions))
		else:
			print('There are no library versions currently installed.')
		
	elif args.remove == True:
		
		# Attempt to remove the specified library version
		try:
			LLVMSelect.removeLibraryVersion(str(version), args.buildtype)
		except Exception as e:
			print(e)
			print('Error: failed to remove the specified library version.')
			sys.exit(1)
		
	elif args.install == True:
		
		# Attempt to install the specified library version
		try:
			builder = LLVMBuilder(version)
			builder.verifyBuildPrerequisitesMet()
			builder.download()
			installDir = builder.build(args.buildtype, LLVMSelect.getInstallationDir(), cleanup=(args.no_cleanup == False))
			print('Library installed to: ' + installDir)
		except CommandNotAvailableError as e:
			print('Error: ' + e.command + ' is required for the build process.')
			print('Please ensure ' + e.command + ' is installed and available in the system PATH.')
			sys.exit(1)
		except BaseException as e:
			print(e)
			sys.exit(1)
		finally:
			if args.no_cleanup == False:
				LLVMBuilder.cleanupFiles(version)
	else:
		
		# Verify that the specified library version is currently installed
		requestedVersionStr = str(version) + '-' + args.buildtype
		if requestedVersionStr not in LLVMSelect.getInstalledVersions():
			print('Error: the specified library version is not currently installed.')
			sys.exit(1)
		
		# Set the specified library version as the active library version
		try:
			LLVMSelect.setActiveLibraryVersion(str(version), args.buildtype)
		except Exception as e:
			print(e)
			sys.exit(1)
