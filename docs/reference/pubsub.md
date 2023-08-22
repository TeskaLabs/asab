# Publish-Subscribe

**Publish-subscribe** is a messaging pattern where senders of messages, called **publishers**,
send the messages to receivers, called **subscribers**, via the PubSub **message bus**.

Publishers don't directly interact with subscribers in any way.
Similarly, subscribers express interest in one or more message types and only receive messages that are of interest,
without knowledge of which publishers, if any, there are.

The ASAB `PubSub` module operates with a simple messages, defined by their *message type*, which is a string.
The message can carry optional positional and keyword arguments.
The delivery of a message is implemented as a the standard Python function.

!!! note
	We recommend to add `!` (an exclamation mark) at the end of the message type in order to distinguish this object from
	other types such as Python class names or functions. 

	Examples:

	- `Application.run!`

	- `Application.tick/600!`

	- `Message.received!`


!!! note
	There is a default, application-wide Publish-Subscribe message
	bus at `Application.PubSub` that can be used to send messages.
	Alternatively, you can create your own instance of `PubSub` and enjoy isolated PubSub delivery space.

## Subscription

The method `PubSub.subscribe()` subscribes to a message type. Messages will be delivered to a `callback` callable (function or method).
The `callback` can be a standard callable or an `async` coroutine.
Asynchronous `callback` means that the delivery of the message will happen in a `Future`, asynchronously.

`Callback` callable will be called with the first argument.

!!! example

	Example of a subscription to an `Application.tick!` messages:

	``` python
	class MyClass:
		def __init__(self, app):
			app.PubSub.subscribe("Application.tick!", self.on_tick)

		def on_tick(self, message_type):
			print(message_type)
	```

!!! example

	Asynchronous version of the above:

	``` python
	class MyClass:
		def __init__(self, app):
			app.PubSub.subscribe("Application.tick!", self.on_tick)

		async def on_tick(self, message_type):
			print("Wait for it...")
			await asyncio.sleep(3.0)
			print(message_type)
	```

To simplify the process of subscription to `PubSub`, ASAB offers the decorator-based *"subscribe all"* functionality.

!!! example

	In the following example, both `on_tick()` and `on_exit()` methods are subscribed to `Application.PubSub` message bus.

	``` python
	class MyClass:
		def __init__(self, app):
			app.PubSub.subscribe_all(self)

		@asab.subscribe("Application.tick!")
		async def on_tick(self, message_type):
			print(message_type)

		@asab.subscribe("Application.exit!")
		def on_exit(self, message_type):
			print(message_type)
	```

!!! example

	``` python
	async def my_coroutine(self):
		# Subscribe for a two application events
		subscriber = asab.Subscriber(
			self.PubSub,
			"Application.tick!",
			"Application.exit!"
		)
		async for message_type, args, kwargs in subscriber:
			if message_type == "Application.exit!":
				break;
			print("Tick.")
	```

## Publishing

`PubSub.publish()` publishes a message to the PubSub message bus. It will be delivered to each subscriber synchronously. 
It means that the method returns after each subscribed `callback` is called.

!!! example

	The example of a message publish to the `Application.PubSub` message bus:

	``` python
	def my_function(app):
		app.PubSub.publish("My.Message!")
	```

Asynchronous publishing of a message is requested by `asynchronously=True` argument.
The `publish()` method returns immediately and the delivery of the message to subscribers happens,
when control returns to the event loop.

!!! example

	The example of a **asynchronous version** of a message publish to the `Application.PubSub` message bus:

	``` python
	def my_function(app):
		app.PubSub.publish("My.Message!", asynchronously=True)
	```

## Synchronous vs. asynchronous messaging

ASAB PubSub supports both modes of a message delivery: synchronous and asynchronous.
Moreover, PubSub also deals with modes, when asynchronous code (coroutine) does publish to synchronous code and vice versa.

| | Synchronous publish | Asynchronous publish |
| --- | --- | --- |
| Synchronous subscribe | called immediately | `call_soon()` |
| Asynchronous subscribe | `ensure_future()` | `call_soon()` and `ensure_future()` |


## Application-wide PubSub

ASAB provides the application-wide Publish-Subscribe message bus.

### Well-Known Messages

ASAB itself publishes various well-known messages published on `Application.PubSub`:

| Message | Published when... |
| ---: | --- |
| **Application.init!** | ...the application is in the [init-time](/reference/application/reference/#init-time) after the configuration is loaded, logging is setup, the event loop is constructed etc. |
| **Application.run!** | ...the application enters the [run-time](/reference/application/reference/#run-time). |
| **Application.stop!** | ...the application wants to stop the [run-time](/reference/application/reference/#run-time). It can be sent multiple times because of a process of graceful run-time termination. The first argument of the message is a counter that increases with every **Application.stop!** event. |
| **Application.exit!** | ...the application enters the [exit-time](/reference/application/reference/#exit-time). |
| **Application.hup!** | ...the application receives UNIX signal `SIGHUP` or equivalent.|
| **Application.housekeeping!** | ...the application is on the time for [housekeeping](#housekeeping). |
| Tick messages | ...periodically with the specified tick frequency. | 

### Tick messages

Tick messages are published by the application periodically. 
For example, **Application.tick!** is published every tick, **Application.tick/10!** is published every 10th tick etc.
The tick frequency is configurable to whole seconds, the default is *1 second*.

```ini
[general]
# tick every 3 seconds
tick_period = 3
```

| Message | Default period |
| ---: | --- |
| **Application.tick!** | Every second. |
| **Application.tick/10!** | Every 10 seconds. |
| **Application.tick/60!** | Every minute. |
| **Application.tick/300!** | Every 5 minutes. |
| **Application.tick/600!** | Every 10 minutes. |
| **Application.tick/1800!** | Every 30 minutes. |
| **Application.tick/3600!** | Every hour. |
| **Application.tick/43200!** | Every 12 hours. |
| **Application.tick/86400!** | Every 24 hours. |


### Housekeeping

Housekeeping is intended for scheduled processes that run once a day, e.g. for cleaning server databases. 

```python
app.PubSub.subscribe("Application.housekeeping!", clean_recycle_bin)

def clean_recycle_bin(msg):
	...
```

The application checks every ten minutes if it's time for housekeeping.
If the UTC time reaches the value for housekeeping, the app will publish **Application.housekeeping!**
and schedules the next housekeeping for tomorrow at the same time.
There is also a time limit, which is set to 05:00 AM UTC by default.

By default, the time for housekeeping is set to 03:00 AM UTC and the limit to 05:00 AM UTC.


Housekeeping can be also configured to run during the application [init-time](/reference/application/reference/#init-time).
Housekeeping time, time limit, and housekeeping at startup can be changed in the configuration file:

``` ini
[housekeeping]
at=19:30
limit=21:00
run_at_startup=yes
```

This sets the housekeeping time to 7:30 PM UTC and the time limit to 9:00 PM UTC.
The time must be written in the format 'HH:MM'.
Remember that the time is set to UTC, so be careful when operating in a different timezone.

!!! note

	If the computer is in a sleep state, housekeeping will not be performed.
	Then, when the computer is reawakened, it will check if it has exceeded the time limit.
	If not, then housekeeping will be published. If it has exceeded it, it simply informs the user and sets the housekeeping time for the next day.
	
	Note that this only limits the time when the housekeeping can start.
	If the housekeeping event triggers a procedure that takes a long time to finish, it will not be terminated when the time limit is reached.

## Reference:

::: asab.pubsub.PubSub

::: asab.pubsub.Subscriber

::: asab.pubsub.subscribe
