#!/usr/bin/env python3
import os, platform, shutil, subprocess, sys

# The current version number for llvm-select
VERSION = '1.0.0'

# Reads the contents of a file
def getFileContents(filename):
	f = open(filename, 'r')
	data = f.read()
	f.close()
	return data

# Writes the contents of a file
def putFileContents(filename, data):
	f = open(filename, 'w', encoding='utf8')
	f.write(data)
	f.close()

# Wrapper for os.makedirs() that deals with the broken behaviour of exist_ok in Python 3.4.0
def makeDirs(d):
	try:
		os.makedirs(d, exist_ok=True)
	except FileExistsError:
		pass

# Determines if a command succeeded
def commandSucceeded(command):
	try:
		proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		(stdout, stderr) = proc.communicate(None)
		return True if (proc.returncode == 0) else False
	except:
		return False

# Verifies that the specified command is available, and prints an error if it is not
def errorIfNotAvailable(command, versionFlag='--version'):
	if commandSucceeded([command, versionFlag]) == False:
		print('Error: ' + command + ' is required in order to generate the installer.')
		print('Please ensure ' + command + ' is installed and available in the system PATH.')
		sys.exit(1)

# Checks that all of the prerequisites are met for generating the installer
def checkInstallerPrerequisites():
	if platform.system() == 'Windows':
		errorIfNotAvailable('makensis', versionFlag='/VERSION')
	else:
		errorIfNotAvailable('fpm')		

# Creates the installer package for the current platform
def createInstaller():
	
	# Remove any previously-generated installer
	installerDir = os.getcwd() + '/install'
	if os.path.exists(installerDir) == True:
		shutil.rmtree(installerDir)
	
	# Create the required directories
	makeDirs(installerDir + '/bin')
	
	# Copy llvm-select
	if platform.system() == 'Windows':
		shutil.copy2('../llvm-select.py', installerDir + '/bin/llvm-select.py')
		shutil.copy2('./windows/llvm-select.cmd', installerDir + '/bin/llvm-select.cmd')
		installerScript = getFileContents('./windows/installer.nsi')
		installerScript = installerScript.replace('__VERSION__', VERSION)
		putFileContents(installerDir + '/installer.nsi', installerScript)
	else:
		shutil.copy2('../llvm-select.py', installerDir + '/bin/llvm-select')
		subprocess.call(['chmod', '755', './llvm-select'], cwd=installerDir + '/bin')
	
	# Generate the installer package
	if platform.system() == 'Windows':
		subprocess.call(['makensis', 'installer.nsi'], cwd=installerDir)
	else:
		
		# Determine the platform-specific arguments for fpm
		packageType = None
		platformArgs = []
		if platform.system() == 'Darwin':
			
			# Under macOS, we need to specify a package identifier prefix
			packageType = 'osxpkg'
			platformArgs = ['--osxpkg-identifier-prefix', 'com.adamrehn']
			
		else:
			
			# Determine if this is a Debian-based or RPM-based Linux distro
			# (Command from here: <https://ask.fedoraproject.org/en/question/49738/how-to-check-if-system-is-rpm-or-debian-based/>)
			isRpmBased = commandSucceeded(['/usr/bin/rpm', '-q', '-f', '/usr/bin/rpm'])
			packageType = 'rpm' if isRpmBased else 'deb'
		
		# Package using fpm
		subprocess.call([
			'fpm',
			'-s', 'dir',
			'-t', packageType,
			'--name', 'llvm-select',
			'--version', VERSION
		] + platformArgs + [
			'--prefix', '/usr/local',
			'./bin'
		], cwd=installerDir)
	
	# Inform the user of the output directory location
	print('Installation package generated in `' + installerDir + '`')

# Generate the installer
checkInstallerPrerequisites()
createInstaller()
