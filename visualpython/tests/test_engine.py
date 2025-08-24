import unittest
from visualpython.core import VisualPythonEngine

class TestVisualPythonEngine(unittest.TestCase):
    def setUp(self):
        self.engine = VisualPythonEngine(backend='tkinter', width=800, height=600)

    def test_variable_assignment(self):
        code = "x = 100"
        self.engine.execute(code)
        self.assertIn('x', self.engine.variables)
        self.assertEqual(self.engine.variables['x'], 100)

    def test_print_statement(self):
        code = 'print("Hello, World!")'
        self.engine.execute(code)
        self.assertTrue(any(kf['text'] == "Hello, World!" for kf in self.engine.keyframes))

    def test_for_loop(self):
        code = """
for i in range(3):
    offset = i * 40
    print(f"Element {i} at offset {offset}")
"""
        self.engine.execute(code)
        self.assertTrue(any(kf['text'] == "Element 0 at offset 0" for kf in self.engine.keyframes))
        self.assertTrue(any(kf['text'] == "Element 1 at offset 40" for kf in self.engine.keyframes))
        self.assertTrue(any(kf['text'] == "Element 2 at offset 80" for kf in self.engine.keyframes))

if __name__ == '__main__':
    unittest.main()
