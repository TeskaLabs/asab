Publish-Subscribe {#pubsub_page}
=================

Publish--subscribe is a messaging pattern where senders of messages,
called publishers, send the messages to receivers, called subscribers,
via PubSub message bus. Publishers don\'t directly interact with
subscribers in any way. Similarly, subscribers express interest in one
or more message types and only receive messages that are of interest,
without knowledge of which publishers, if any, there are.

ASAB `PubSub` operates with a simple messages, defined by their *message
type*, which is a string. We recommend to add `!` (explamation mark) at
the end of the message type in order to distinguish this object from
other types such as Python class names or functions. Example of the
message type is e.g. `Application.run!`{.interpreted-text role="any"} or
`Application.tick/600!`{.interpreted-text role="any"}.

The message can carry an optional positional and keyword arguments. The
delivery of a message is implemented as a the standard Python function.

*Note:* There is an default, application-wide Publish-Subscribe message
bus at `Application.PubSub`{.interpreted-text role="any"} that can be
used to send messages. Alternatively, you can create your own instance
of :py`PubSub`{.interpreted-text role="class"} and enjoy isolated PubSub
delivery space.

Subscription
------------

Subscribe to a message type. Messages will be delivered to a `callback`
callable (function or method). The `callback` can be a standard callable
or an `async` coroutine. Asynchronous `callback` means that the delivery
of the message will happen in a `Future`, asynchronously.

`Callback` callable will be called with the first argument

Example of a subscription to an `Application.tick!`{.interpreted-text
role="any"} messages.

``` {.python}
class MyClass(object):
    def __init__(self, app):
        app.PubSub.subscribe("Application.tick!", self.on_tick)

    def on_tick(self, message_type):
        print(message_type)
```

Asynchronous version of the above:

``` {.python}
class MyClass(object):
    def __init__(self, app):
        app.PubSub.subscribe("Application.tick!", self.on_tick)

    async def on_tick(self, message_type):
        await asyncio.sleep(5)
        print(message_type)
```

To simplify the process of subscription to `PubSub`{.interpreted-text
role="any"}, ASAB offers the decorator-based *\"subscribe all\"*
functionality.

In the followin example, both `on_tick()` and `on_exit()` methods are
subscribed to `Application.PubSub`{.interpreted-text role="any"} message
bus.

``` {.python}
class MyClass(object):
    def __init__(self, app):
        app.PubSub.subscribe_all(self)

    @asab.subscribe("Application.tick!")
    async def on_tick(self, message_type):
        print(message_type)

    @asab.subscribe("Application.exit!")
    def on_exit(self, message_type):
        print(message_type)
```

Unsubscribe from a message delivery.

# TODO: autoclass members="" undoc-members=""}
asab.Subscriber
xxx

The subscriber object can be also used as [an asynchonous
generator]{.title-ref}. The example of the subscriber object usage in
[async for]{.title-ref} statement:

``` {.python}
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

Publishing
----------

Publish a message to the PubSub message bus. It will be delivered to
each subscriber synchronously. It means that the method returns after
each subscribed `callback` is called.

The example of a message publish to the
`Application.PubSub`{.interpreted-text role="any"} message bus:

``` {.python}
def my_function(app):
    app.PubSub.publish("mymessage!")
```

Asynchronous publishing of a message is requested by
`asynchronously=True` argument. The `publish()` method returns
immediatelly and the delivery of the message to subscribers happens,
when control returns to the event loop.

The example of a **asynchronous version** of a message publish to the
`Application.PubSub`{.interpreted-text role="any"} message bus:

``` {.python}
def my_function(app):
    app.PubSub.publish("mymessage!", asynchronously=True)
```

Synchronous vs. asynchronous messaging
--------------------------------------

ASAB PubSub supports both modes of a message delivery: synchronous and
asynchronous. Moreover, PubSub also deals with modes, when asynchronous
code (coroutine) does publish to synchronous code and vice versa.

  -------------- ---------------------- ------------------------------------
                 Sync publish           Async publish

  Sync subscribe Called immediately     `call_soon(...)`

  Async          `ensure_future(...)`   `call_soon(...)` &
  subscribe                             `ensure_future(...)`
  -------------- ---------------------- ------------------------------------

Application-wide PubSub
-----------------------

The ASAB provides the application-wide Publish-Subscribe message bus.

### Well-Known Messages

This is a list of well-known messages, that are published on a
`Application.PubSub` by ASAB itself.

%TODO: option%
Application.init!
xxx

This message is published when application is in the init-time. It is
actually one of the last things done in init-time, so the application
environment is almost ready for use. It means that configuration is
loaded, logging is setup, the event loop is constructed etc.

%TODO: option%
Application.run!
xxx

This message is emitted when application enters the run-time.

%TODO: option%
Application.stop!
xxx

This message is emitted when application wants to stop the run-time. It
can be sent multiple times because of a process of graceful run-time
termination. The first argument of the message is a counter that
increases with every `Application.stop!` event.

%TODO: option%
Application.exit!
xxx

This message is emitted when application enter the exit-time.

%TODO: option%
Application.tick!
xxx

%TODO: option%
Application.tick/10!
xxx

%TODO: option%
Application.tick/60!
xxx

%TODO: option%
Application.tick/300!
xxx

%TODO: option%
Application.tick/600!
xxx

%TODO: option%
Application.tick/1800!
xxx

%TODO: option%
Application.tick/3600!
xxx

%TODO: option%
Application.tick/43200!
xxx

%TODO: option%
Application.tick/86400!
xxx

The application publish periodically \"tick\" messages. The default tick
frequency is 1 second but you can change it by configuration
`[general] tick_period`. `Application.tick!`{.interpreted-text
role="any"} is published every tick.
`Application.tick/10!`{.interpreted-text role="any"} is published every
10th tick and so on.

%TODO: option%
Application.hup!
xxx

This message is emitted when application receives UNIX signal `SIGHUP`
or equivalent.

%TODO: option%
Application.housekeeping!
xxx

This message is published when application is on the time for
housekeeping. The time for housekeeping is set to 03:00 AM UTC by
default.

The app listens every ten minutes to see if it\'s time for housekeeping.
If the UTC time reaches the value for housekeeping, the app will publish
it and set the time for the next housekeeping for the next day at the
same time. There is also a time limit, which is set to 05:00 AM UTC by
default. If the computer is in a sleep state, housekeeping will not be
performed. Then, when the computer is reawakened again, it will check if
it has exceeded the time limit. If not, then housekeeping will be
published. If it has exceeded it, it simply informs the user and sets
the housekeeping time for the next day. Note that this only limits the
time when the housekeeping can start. If the housekeeping event triggers
a procedure that takes a long time to finish, it will not be terminated
when the time limit is reached.

Both housekeeping time and time limit can be changed in the
configuration file:

``` {.ini}
[housekeeping]
at=19:30
limit=21:00
```

This sets the housekeeping time to 7:30 PM UTC and the time limit to
9:00 PM UTC. The time must be written in the format \'HH:MM\'. Remind
yourself that the time is set to UTC, so you should be careful when
operating in a different timezone.
