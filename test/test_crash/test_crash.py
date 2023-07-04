import unittest
import subprocess


class TestCrashApp01(unittest.TestCase):
	app_crash_path = "test/test_crash/app_crash_01.py"

	def test_exit_code(self):
		"""The app should exit with code 1 when custom Exception is raised."""
		exit_code = subprocess.call(['python3', '{}'.format(self.app_crash_path)])
		self.assertEqual(exit_code, 1)

	def test_exception_message(self):
		"""The app should display Exception traceback."""
		completed_process = subprocess.run(['python3', '{}'.format(self.app_crash_path)], capture_output=True, text=True)
		error_output = completed_process.stderr  # Standard error
		expected_error_msg = "Exception: This is a custom exception."
		self.assertEqual(error_output.splitlines()[-1], expected_error_msg)


class TestCrashApp02(unittest.TestCase):
	app_crash_path = "test/test_crash/app_crash_02.py"

	def test_exit_code(self):
		"""The app should exit with code 1 when ZeroDivisionError is raised."""
		exit_code = subprocess.call(['python3', '{}'.format(self.app_crash_path)])
		self.assertEqual(exit_code, 1)

	def test_exception_message(self):
		"""The app should display ZeroDivisionError traceback."""
		completed_process = subprocess.run(['python3', '{}'.format(self.app_crash_path)], capture_output=True, text=True)
		error_output = completed_process.stderr  # Standard error
		expected_error_msg = "ZeroDivisionError: division by zero"
		self.assertEqual(error_output.splitlines()[-1], expected_error_msg)


class TestCrashApp03(unittest.TestCase):
	app_crash_path = "test/test_crash/app_crash_03.py"

	def test_exit_code(self):
		"""The app should exit with code 0 when Exception is caught."""
		exit_code = subprocess.call(['python3', '{}'.format(self.app_crash_path)])
		self.assertEqual(exit_code, 0)

	def test_exception_message(self):
		"""The app should caught Exception when it is raised."""
		completed_process = subprocess.run(['python3', '{}'.format(self.app_crash_path)], capture_output=True, text=True)
		output = completed_process.stdout  # Standard output
		self.assertEqual(output.splitlines()[-1], "Exception was caught.")


if __name__ == '__main__':
	unittest.main()
