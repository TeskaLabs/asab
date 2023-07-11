---
author: Jakub Boukal
commit: 4db78e814d48f1911e1ce8df476f25be725764f0
date: 2019-12-10 17:55:51+01:00
title: Timer

---

!!! example

	```python title=timer.py linenums="1"
	#!/usr/bin/env python3
	import asab
	
	
	class TimerApplication(asab.Application):
	
	
		async def initialize(self):
			# The timer will trigger a message publishing at every second
			self.Timer = asab.Timer(self, self.on_tick, autorestart=True)
			self.Timer.start(1)
	
	
		async def on_tick(self):
			print("Think!")
	
	
	if __name__ == '__main__':
		app = TimerApplication()
		app.run()
	
	```
