import unittest
from repeaterstart import BackgroundDownload 

class TestBackgroundDownload(unittest.TestCase):
    def test_successful_download(self):
        url = 'https://example.com/file.txt'
        filename = '/tmp/test_file.txt'
        bg_download = BackgroundDownload(url, filename)
        bg_download.start()
        bg_download.join()
        self.assertTrue(bg_download.finished)
        self.assertTrue(bg_download.success)

    def test_failed_download(self):
        url = 'https://nonexistenturl.invalid/file.txt'
        filename = '/tmp/test_file.txt'
        bg_download = BackgroundDownload(url, filename)
        bg_download.start()
        bg_download.join()
        self.assertTrue(bg_download.finished)
        self.assertFalse(bg_download.success)

if __name__ == '__main__':
    unittest.main()
