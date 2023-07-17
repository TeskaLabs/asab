import asab


class TestCrash_02(asab.Application):
	async def main(self):
		_ = 22 / 0


if __name__ == "__main__":
	app = TestCrash_02()
	app.run()
