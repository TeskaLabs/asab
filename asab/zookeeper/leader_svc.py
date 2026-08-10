import os
import logging
import threading

import kazoo.protocol.states

from ..abc.service import Service

#

L = logging.getLogger(__name__)

#


class LeaderService(Service):
	"""
	ZooKeeper-based leader election service.

	Creates an ephemeral znode under `{zkcontainer.Path}/election/{scope}`.
	The instance that successfully creates the node becomes the leader; others
	become followers. Leadership is released automatically when the ZooKeeper
	session ends (process stop, disconnect, or session expiry).

	Different `scope` values allow multiple LeaderService instances to run in
	parallel on the same ZooKeeper container, each electing a leader within its
	own election namespace.

	PubSub events:

	- `LeaderService.state/LEADER!` — this instance became the leader.
	- `LeaderService.state/FOLLOWER!` — this instance is (or became) a follower.

	Both events carry `scope` as the sole argument after the event name.
	`LeaderInfo` holds the current leader znode payload (bytes), typically
	lines with `instance_id`, `service_id`, and/or `node_id` from the environment.

	Participation can be controlled with `StepDown()` / `SetUp()`:

	- `StepDown()` leaves the election. If this instance is the leader, the
		ephemeral election znode is deleted so other participants can elect a
		new leader; this instance becomes a follower and will not re-contend
		until `SetUp()` is called.
	- `SetUp()` resumes participation and runs an election attempt.

	Examples:

	```python
	self.LeaderService = asab.zookeeper.LeaderService(
		self, self.ZkContainer, "example-leader"
	)
	self.PubSub.subscribe("LeaderService.state/LEADER!", self._on_leader)
	self.PubSub.subscribe("LeaderService.state/FOLLOWER!", self._on_follower)

	# Voluntarily resign and leave the election:
	self.LeaderService.StepDown()
	# Later rejoin and contend again:
	self.LeaderService.SetUp()
	```
	"""

	def __init__(self, app, zkcontainer, scope):
		"""
		Register the service and subscribe to ZooKeeper connectivity events.

		Args:
			app (asab.Application): Reference to the ASAB application.
			zkcontainer (asab.zookeeper.ZooKeeperContainer): ZooKeeper container
				used for the election path and client.
			scope (str): Election namespace; must be a non-empty string
				and must not contain `/`. Distinct scopes elect leaders
				independently.
				Registered as service name `asab.LeaderService:{scope}`.

		Raises:
			ValueError: If `scope` is not a non-empty string or contains `/`.
		"""
		if not isinstance(scope, str):
			raise ValueError("Scope must be a string")
		if not scope:
			raise ValueError("Scope must not be empty")
		if "/" in scope:
			raise ValueError("Scope must not contain '/' character")

		super().__init__(app, "asab.LeaderService:{}".format(scope))
		self.ZkContainer = zkcontainer
		self.ElectionPath = zkcontainer.Path + "/election"
		self.Scope = scope

		# Subscribe to the event that indicated the successful connection to the Zookeeper server(s)
		app.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_ready)
		app.PubSub.subscribe("ZooKeeperContainer.state/SUSPENDED!", self._on_zk_suspended)
		app.PubSub.subscribe("ZooKeeperContainer.state/LOST!", self._on_zk_lost)
		app.PubSub.subscribe("Application.tick/60!", self._on_tick60)

		self._leader_zxid = None
		self.LeaderInfo = None

		# When False, this instance does not contend for leadership (after StepDown).
		# Starts True so the first CONNECTED event joins the election automatically.
		self._participating = True

		# Serializes CONNECTED / watch / tick / StepDown / SetUp election work.
		# LOST (and SUSPENDED for in-flight attempts) invalidate `_election_key`
		# without acquiring this lock (avoids blocking the event loop on ZooKeeper
		# I/O); in-flight elections observe the stale key before publishing LEADER!.
		self._election_lock = threading.Lock()
		self._election_key = None


	def IsLeader(self):
		"""
		Return whether this instance currently holds leadership.

		Returns:
			bool: `True` if this instance is the leader, otherwise `False`
				(including while leadership is unknown after connect/loss).
		"""
		if self._leader_zxid is None:
			return False
		return True


	def StepDown(self):
		"""
		Leave the election and resign leadership if held.

		Schedules work on the ZooKeeper proactor thread: stops contending for
		leadership, deletes this instance's ephemeral election znode when it is
		the leader (so a new election can proceed among remaining participants),
		clears local leadership state, and publishes `LeaderService.state/FOLLOWER!`.

		This instance remains a non-participating follower until `SetUp()` is
		called. Safe to call when already a follower or already stepped down.

		If the election znode cannot be deleted (e.g. transient ZooKeeper error),
		local leadership is retained and `Application.tick60!` retries the release.
		"""
		self.ZkContainer.ProactorService.schedule(self._step_down_thread)


	def SetUp(self):
		"""
		Resume participation in the election.

		Schedules an election attempt on the ZooKeeper proactor thread. If no
		leader currently holds the election znode, this instance may become the
		leader; otherwise it becomes (or remains) a follower.

		Safe to call when already participating.
		"""
		self.ZkContainer.ProactorService.schedule(self._set_up_thread)


	def _capture_election_key(self):
		"""Return (session_id, last_zxid) for the current ZK connection, or None."""
		client = self.ZkContainer.ZooKeeper.Client
		client_id = client.client_id
		if client_id is None:
			return None
		return (client_id[0], client.last_zxid)


	def _election_node_path(self):
		return self.ElectionPath + "/" + self.Scope


	def _step_down_thread(self):
		with self._election_lock:
			self._participating = False
			# Invalidate any in-flight election so it cannot publish LEADER! after we resign.
			self._election_key = None

			leader_zxid = self._leader_zxid
			if leader_zxid is None:
				# Follower leaving the election: drop any cached leader payload.
				self.LeaderInfo = None
				self.App.PubSub.publish_threadsafe("LeaderService.state/FOLLOWER!", self.Scope)
				return

			released = False
			path = self._election_node_path()
			try:
				_, stats = self.ZkContainer.ZooKeeper.Client.get(path)
				if stats.czxid == leader_zxid:
					# Deleting the ephemeral node triggers watches on other
					# participants so they can elect a new leader.
					self.ZkContainer.ZooKeeper.Client.delete(path)
					released = True
				else:
					# Another instance holds the node; our leadership claim is obsolete.
					released = True
			except kazoo.exceptions.NoNodeError:
				released = True
			except kazoo.exceptions.KazooException as e:
				# Keep `_leader_zxid` so tick60 can retry the release.
				L.warning("Failed to delete election node during StepDown: {}", e)

			if not released:
				return

			self._leader_zxid = None
			self.LeaderInfo = None
			self.App.PubSub.publish_threadsafe("LeaderService.state/FOLLOWER!", self.Scope)


	def _set_up_thread(self):
		with self._election_lock:
			self._participating = True
		self._election_thread()


	async def _on_zk_ready(self, event_name, zkcontainer):
		# If there is more than one ZooKeeper Container being initialized, this method is called at every Container initialization.
		# Then you need to check whether the specific ZK Container has been initialized.
		if zkcontainer != self.ZkContainer:
			return

		def setup():
			zkcontainer.ZooKeeper.Client.ensure_path(self.ElectionPath)
			zkcontainer.ZooKeeper.Client.add_watch(
				self.ElectionPath,
				self._on_change_zookeeper_thread,
				kazoo.protocol.states.AddWatchMode.PERSISTENT_RECURSIVE
			)

			# Start the election thread to become leader or follower
			if self._participating:
				self._election_thread()

		# Keep `_leader_zxid` / LeaderInfo across reconnect: a still-valid
		# session retains the ephemeral election node, and NodeExistsError
		# handling must compare stats.czxid with the prior zxid.
		zkcontainer.ProactorService.schedule(setup)


	def _on_zk_suspended(self, event_name, zkcontainer):
		if zkcontainer != self.ZkContainer:
			return

		# Connection is down but the session may still be valid; do not clear
		# leadership identity. Only invalidate in-flight elections.
		self._election_key = None
		L.warning("ZooKeeper connection suspended; leadership state preserved until session is lost.")


	async def _on_zk_lost(self, event_name, zkcontainer):
		# If there is more than one ZooKeeper Container being initialized, this method is called at every Container initialization.
		# Then you need to check whether the specific ZK Container has been initialized.
		if zkcontainer != self.ZkContainer:
			return

		# Confirmed session loss: invalidate in-flight elections and clear leadership.
		self._election_key = None
		self._leader_zxid = None
		self.LeaderInfo = None
		self.App.PubSub.publish("LeaderService.state/FOLLOWER!", self.Scope)


	def _on_change_zookeeper_thread(self, event):
		if not self._participating:
			return
		if not self.IsLeader():
			self._election_thread()


	def _on_tick60(self, event_name):
		if not self._participating:
			if self.IsLeader():
				# Stepped down but still hold leadership (e.g. prior delete failed); finish resigning.
				return self.ZkContainer.ProactorService.schedule(self._step_down_thread)
			return
		if not self.IsLeader():
			# Speculatively run the election thread to become leader - this is a last resort recovery mechanism
			return self.ZkContainer.ProactorService.schedule(self._election_thread)


	def _election_thread(self):
		with self._election_lock:
			if not self._participating:
				return

			election_key = self._capture_election_key()
			if election_key is None:
				return
			self._election_key = election_key

			instance_id = os.environ.get("INSTANCE_ID")
			service_id = os.environ.get("SERVICE_ID")
			node_id = os.environ.get("NODE_ID")

			leader_data = b""
			if instance_id is not None:
				leader_data += (f"instance_id: {instance_id}\n").encode("utf-8")
			if service_id is not None:
				leader_data += (f"service_id: {service_id}\n").encode("utf-8")
			if node_id is not None:
				leader_data += (f"node_id: {node_id}\n").encode("utf-8")

			# Try to become leader
			try:
				_, stats = self.ZkContainer.ZooKeeper.Client.create(
					self._election_node_path(),
					leader_data,
					ephemeral=True,  # We want this to disappear when the instance is stopped
					include_data=True,
				)
			except kazoo.exceptions.NodeExistsError:
				leader_data, stats = self.ZkContainer.ZooKeeper.Client.get(self._election_node_path())
				if self._election_key != election_key:
					# Session was lost/invalidated while we ran; do not overwrite state.
					return
				if stats.czxid == self._leader_zxid:
					# I'm still the leader, no need to become leader again.
					return
				self._leader_zxid = None
				self.LeaderInfo = leader_data
				self.App.PubSub.publish_threadsafe("LeaderService.state/FOLLOWER!", self.Scope)
			else:
				if self._election_key != election_key:
					# Stale election result (e.g. session lost): become follower without
					# overwriting LeaderInfo / _leader_zxid already cleared by LOST.
					self.App.PubSub.publish_threadsafe("LeaderService.state/FOLLOWER!", self.Scope)
					return
				self._leader_zxid = stats.czxid
				self.LeaderInfo = leader_data
				# Re-check after writing: LOST may have invalidated concurrently.
				if self._election_key != election_key:
					self._leader_zxid = None
					self.LeaderInfo = None
					return
				self.App.PubSub.publish_threadsafe("LeaderService.state/LEADER!", self.Scope)
