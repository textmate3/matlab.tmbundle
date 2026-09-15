"""Tests for the two Introduce Variable commands.

They ask for a name through tm_dialog, so a stand-in under Tests/fixtures
answers instead, and no window opens. TM_SUPPORT_PATH has to point at a
Bundle Support checkout, which is where the dialog helper lives.

Run from the bundle's directory:

    TM_SUPPORT_PATH=../bundle-support.tmbundle/Support/shared \\
      "$TM_PYTHON" Tests/python_commands_tests.py
"""

import os
import plistlib
import subprocess
import sys
import unittest

BUNDLE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIALOG_STUB = os.path.join(BUNDLE, "Tests/fixtures/tm_dialog")

DOCUMENT = "a = 1;\nb = a + 2;\nc = a + 3;\n"


def command_script(name):
    with open(os.path.join(BUNDLE, "Commands", name), "rb") as plist:
        return plistlib.load(plist)["command"]


def run(name, document, answer=None, line_number=2):
    environment = {
        **os.environ,
        "DIALOG": DIALOG_STUB,
        "TM_LINE_NUMBER": str(line_number),
    }
    if answer is None:
        environment.pop("DIALOG_STUB_ANSWER", None)
    else:
        environment["DIALOG_STUB_ANSWER"] = answer

    selection = environment.pop("TM_SELECTED_TEXT", None)
    return subprocess.run(
        [sys.executable, "-c", command_script(name)],
        input=document,
        env=environment if selection is None else {**environment, "TM_SELECTED_TEXT": selection},
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def run_with_selection(name, document, selection, answer, line_number=2):
    return subprocess.run(
        [sys.executable, "-c", command_script(name)],
        input=document,
        env={
            **os.environ,
            "DIALOG": DIALOG_STUB,
            "DIALOG_STUB_ANSWER": answer,
            "TM_SELECTED_TEXT": selection,
            "TM_LINE_NUMBER": str(line_number),
        },
        capture_output=True,
        text=True,
        check=True,
    ).stdout


class OnOneLine(unittest.TestCase):
    NAME = "Introduce variable.tmCommand"

    def test_no_selection_leaves_the_document_alone(self):
        self.assertEqual(run(self.NAME, DOCUMENT), DOCUMENT)

    def test_the_selection_becomes_an_assignment_above_its_line(self):
        result = run_with_selection(self.NAME, DOCUMENT, "a + 2", "total")
        self.assertEqual(result, "a = 1;\ntotal = a + 2;\nb = total;\nc = a + 3;\n")

    def test_only_that_line_changes(self):
        result = run_with_selection(self.NAME, DOCUMENT, "a + 2", "total")
        self.assertIn("c = a + 3;", result)

    def test_a_canceled_dialog_still_produces_a_usable_name(self):
        result = run_with_selection(self.NAME, DOCUMENT, "a + 2", "")
        self.assertIn("var = a + 2;", result)


class Throughout(unittest.TestCase):
    NAME = "Introduce variable (throughout).tmCommand"

    def test_no_selection_leaves_the_document_alone(self):
        # This used to raise NameError, because the variable holding the line
        # to insert at was only assigned when there was a selection.
        self.assertEqual(run(self.NAME, DOCUMENT), DOCUMENT)

    def test_every_occurrence_is_replaced(self):
        result = run_with_selection(self.NAME, DOCUMENT, "a + ", "part")
        self.assertNotIn("a + ", result.replace("part = a + ;", ""))

    def test_the_assignment_goes_above_the_first_use(self):
        result = run_with_selection(self.NAME, DOCUMENT, "a + 2", "total")
        lines = result.splitlines()
        self.assertEqual(lines[0], "a = 1;")
        self.assertEqual(lines[1], "total = a + 2;")
        self.assertEqual(lines[2], "b = total;")

    def test_a_match_on_the_first_line_puts_the_assignment_above_it(self):
        result = run_with_selection(self.NAME, "x = 1;\ny = x;\n", "1", "one")
        self.assertEqual(result.splitlines()[0], "one = 1;")


if __name__ == "__main__":
    unittest.main(verbosity=2)
