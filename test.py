# -*- coding: utf-8 -*-=

from os       import environ, listdir
from os.path  import join
from platform import system
from sys      import version
from time     import sleep, time

import logging

logging.basicConfig(format = '%(asctime)s %(message)s', level = logging.DEBUG)

system = system()
isTravis = environ.get('TRAVIS', 'false') == 'true'

if isTravis and system == 'Windows':
    print('\n>>> Will be mocking instead of using the real MciSendStringW function for most tests.\n')
    try:
        from unittest.mock import patch
    except ImportError:
        try:
            from pip import main as pipmain
        except ImportError:
            from pip._internal import main as pipmain

        # Before python 3.3 (including python 2.7.20 and earlier),
        # mocking/patching wasn't part of the standard library. So you need
        # to get those via pip. You specifically need version 2.0.0 - newer
        # versions require python 3.3, utterly defeating the purpose of making
        # the library available on pypi.
        pipmain(['install', 'mock==2.0.0'])
        from mock   import patch
        from ctypes import windll

from playsound import playsound, PlaysoundException
import unittest

durationMarginLow  = 0.2
duratingMarginHigh = 2.0
expectedDuration   = None
testCase           = None

def mockMciSendStringW(command, buf, bufLen, bufStart):
    decodeCommand = command.decode('utf-16')

    if command.startswith(u'open '):
        testCase.assertEqual(windll.winmm.mciSendStringW(command, buf, bufLen, bufStart), 306)  # 306 indicates drivers are missing. It's fine.
        return 0
    
    if command.endswith(u' wait'):
        testCase.assertEqual(windll.winmm.mciSendStringW(command, buf, bufLen, bufStart), 0)
        sleep(expectedDuration)
        return 0

    if command.startswith(u'close '):
        global sawClose
        sawClose = True
        testCase.assertEqual(windll.winmm.mciSendStringW(command, buf, bufLen, bufStart), 0)
        return 0

class PlaysoundTests(unittest.TestCase):
    def helper(self, file, approximateDuration, block = True):
        startTime = time()
        path = join('test_media', file)
        print(path.encode('utf-8'))

        if isTravis and system == 'Windows':
            with patch('ctypes.windll.winmm.mciSendStringW', side_effect = mockMciSendStringW):
                global expectedDuration, sawClose, testCase
                testCase = self
                sawClose = False
                expectedDuration = approximateDuration
                playsound(path, block = block)
                self.assertTrue(sawClose)
        else:
            playsound(path, block = block)
        duration = time() - startTime
        self.assertTrue(approximateDuration - durationMarginLow <= duration <= approximateDuration + duratingMarginHigh, 'File "{}" took an unexpected amount of time: {:.2f} - expected ~{:.2f}'.format(file.encode('utf-8'), duration, approximateDuration))

    testBlockingASCII_MP3 = lambda self: self.helper('Damonte.mp3', 1.1)
    testBlockingASCII_WAV = lambda self: self.helper('Sound4.wav',  1.3)
    testBlockingCYRIL_WAV = lambda self: self.helper(u'Буква_Я.wav', 1.6)
    testBlockingSPACE_MP3 = lambda self: self.helper('Discovery - Go at throttle up (2).mp3', 2.3)
    testNonBlockingRepeat = lambda self: self.helper(u'Буква_Я.wav', 0.0, block = False)

    def testMissing(self):
        with self.assertRaises(PlaysoundException) as context:
            playsound('fakefile.wav')

        message = str(context.exception).lower()
            
        for sub in ['not', 'fakefile.wav']:
            self.assertIn(sub, message, '"{}" was expected in the exception message, but instead got: "{}"'.format(sub, message))

if __name__ == '__main__':
    print(version)
    import sys
    print(sys.executable)
    print(sys.path)
    unittest.main()