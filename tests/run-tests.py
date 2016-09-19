#!/usr/bin/env python3
import os, sys
from inspect import getsourcefile

# Import the main llvm-select script, using the appropriate calls for our Python version
# (File location code from here: <http://stackoverflow.com/a/18489147>)
mainPyFile = os.path.dirname(os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))) + '/llvm-select.py'
if sys.version_info >= (3,5):
	import importlib.util
	spec = importlib.util.spec_from_file_location('llvm-select', mainPyFile)
	llvm_select = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(llvm_select)
else:
	from importlib.machinery import SourceFileLoader
	llvm_select = SourceFileLoader('llvm-select', mainPyFile).load_module()

# Version strings that should be rejected
rejectThese = [
	'hg',
	'3.',
	'1.2.3.4',
	'-3.7.0',
	'2.5',
	'2.6.1',
	'3.5'
]

# Version strings that should be accepted
acceptThese = [
	'3.7.0',
	'2.6',
	'3.4',
	'3.4.1',
	'3.5.0'
]

# Verify that the version string parser rejects the invalid strings
for verString in rejectThese:
	if llvm_select.LLVMVersionDetails.fromVersionString(verString) != None:
		print('Error: accepted invalid version string "' + verString + '"!')
		sys.exit(1)

# Verify that the version string parser accepts the valid strings
for verString in acceptThese:
	if llvm_select.LLVMVersionDetails.fromVersionString(verString) == None:
		print('Error: rejected valid version string "' + verString + '"!')
		sys.exit(1)

# Test the tarball details for all of the real version numbers
realVersions = [
	'2.6', '2.7', '2.8', '2.9',
	'3.0', '3.1', '3.2', '3.3',
	'3.4',   '3.4.1', '3.4.2',
	'3.5.0', '3.5.1', '3.5.2',
	'3.6.0', '3.6.1', '3.6.2',
	'3.7.0', '3.7.1',
	'3.8.0', '3.8.1',
	'3.9.0'
]
for verString in realVersions:
	version = llvm_select.LLVMVersionDetails.fromVersionString(verString)
	if version == None:
		print('Error: rejected real version string "' + verString + '"!')
		sys.exit(1)
	
	print('Version:   ', version)
	print('Extension: ' + version.extension)
	print('Tarballs:  ' + str(version.tarballs))
	
	# Download and unpack the source tarballs for the current version
	builder = llvm_select.LLVMBuilder(version)
	builder.download(showProgress=False)
	
	# Verify that all of the tarballs downloaded and extracted properly
	shouldExist = ['./llvm-src/CMakeLists.txt', './llvm-src/tools/clang/CMakeLists.txt']
	if version.tarballs['compiler-rt'] != None:
		shouldExist.append('./llvm-src/projects/compiler-rt/CMakeLists.txt')
	if version.tarballs['libcxx'] != None:
		shouldExist.append('./llvm-src/projects/libcxx/CMakeLists.txt')
	for file in shouldExist:
		if os.path.exists(file) == False:
			print('Error: tarball extraction didn\'t work properly for LLVM version ' + verString + '!')
			llvm_select.LLVMBuilder.cleanupFiles(version)
			sys.exit(1)
	
	# Perform cleanup
	llvm_select.LLVMBuilder.cleanupFiles(version)
	print('All tests passed for LLVM version `' + verString + '`.\n')
