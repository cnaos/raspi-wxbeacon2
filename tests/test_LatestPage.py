import unittest

from omron_env_sensor import OmronLatestPage


class ExportPagePositionTestCase(unittest.TestCase):
    def test_calcpage_latest_page_0_to_0(self):
        target = OmronLatestPage(0)
        result = target.calcPage(0)
        self.assertEqual(1, len(result))
        self.assertEqual("[0]", str(result))
        self.assertEqual(0, result[0])

    def test_calcpage_latest_page_0_to_1(self):
        target = OmronLatestPage(1)
        result = target.calcPage(0)
        self.assertEqual(2, len(result))
        self.assertEqual("[0, 1]", str(result))
        self.assertEqual(0, result[0])
        self.assertEqual(1, result[1])

    def test_calcpage_latest_page_0_to_2047(self):
        target = OmronLatestPage(2047)
        result = target.calcPage(0)
        self.assertEqual(2048, len(result))
        self.assertEqual(0, result[0])
        self.assertEqual(2047, result[2047])

    def test_calcpage_latest_page_0_to_2048_invalid(self):
        target = OmronLatestPage(0)
        with self.assertRaises(IndexError):
            target.calcPage(2048)

    def test_calcpage_latest_page_0_to_minus1_invalid(self):
        target = OmronLatestPage(0)
        with self.assertRaises(IndexError):
            target.calcPage(-1)

    def test_calcpage_latest_page_1_to_1(self):
        target = OmronLatestPage(1)
        result = target.calcPage(1)
        self.assertEqual(1, len(result))
        self.assertEqual("[1]", str(result))
        self.assertEqual(1, result[0])

    def test_calcpage_latest_page_1_to_2(self):
        target = OmronLatestPage(2)
        result = target.calcPage(1)
        self.assertEqual(2, len(result))
        self.assertEqual("[1, 2]", str(result))
        self.assertEqual(1, result[0])
        self.assertEqual(2, result[1])

    def test_calcpage_latest_page_2046_to_2047(self):
        target = OmronLatestPage(2047)
        result = target.calcPage(2046)
        self.assertEqual(2, len(result))
        self.assertEqual("[2046, 2047]", str(result))
        self.assertEqual(2046, result[0])
        self.assertEqual(2047, result[1])

    def test_calcpage_latest_page_2046_to_0(self):
        target = OmronLatestPage(0)
        result = target.calcPage(2046)
        self.assertEqual(3, len(result))
        self.assertEqual("[2046, 2047, 0]", str(result))
        self.assertEqual(2046, result[0])
        self.assertEqual(2047, result[1])
        self.assertEqual(0, result[2])

    def test_calcpage_latest_page_2046_to_1(self):
        target = OmronLatestPage(1)
        result = target.calcPage(2046)
        self.assertEqual(4, len(result))
        self.assertEqual("[2046, 2047, 0, 1]", str(result))
        self.assertEqual(2046, result[0])
        self.assertEqual(2047, result[1])
        self.assertEqual(0, result[2])
        self.assertEqual(1, result[3])


if __name__ == '__main__':
    unittest.main()
