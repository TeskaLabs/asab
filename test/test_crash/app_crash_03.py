import asab


class TestCrash_03(asab.Application):
	async def main(self):
		try:
			_ = 22 / 0
		except ZeroDivisionError:
			raise Exception("Division by zero is not possible.")


if __name__ == "__main__":
	app = TestCrash_03()
	try:
		app.run()
	except Exception:
		print("Exception was caught.")
