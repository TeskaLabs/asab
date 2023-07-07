import asab


class TestCrash_01(asab.Application):
	async def main(self):
		raise Exception("This is a custom exception.")


if __name__ == "__main__":
	app = TestCrash_01()
	app.run()
