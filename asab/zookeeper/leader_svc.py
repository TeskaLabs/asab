import os
import logging

import kazoo.protocol.states

from ..abc.service import Service

#

L = logging.getLogger(__name__)

#


class LeaderService(Service):

	def __init__(self, app, zkcontainer, leader_name):
		super().__init__(app, "asab.LeaderService:{}".format(leader_name))
		self.ZkContainer = zkcontainer
		self.ElectionPath = zkcontainer.Path + "/election"

		assert "/" not in leader_name, "Leader name must not contain '/' character"
		self.LeaderName = leader_name

		# Subscribe to the event that indicated the successful connection to the Zookeeper server(s)
		app.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_ready)
		app.PubSub.subscribe("ZooKeeperContainer.state/LOST!", self._on_zk_lost)
		app.PubSub.subscribe("Application.tick60!", self._on_tick60)

		self._leader_zxid = None  # Can be True, False or None (for initialization)
		self.LeaderInfo = None


	def IsLeader(self):
		if self._leader_zxid is None:
			return False
		return True


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
			self._election_thread()

		if self._leader_zxid is not None:
			self._leader_zxid = None
			self.LeaderInfo = None
			self.App.PubSub.publish_threadsafe("LeaderService.state/FOLLOWER!", self.LeaderName)

		zkcontainer.ProactorService.schedule(setup)


	async def _on_zk_lost(self, event_name, zkcontainer):
		# If there is more than one ZooKeeper Container being initialized, this method is called at every Container initialization.
		# Then you need to check whether the specific ZK Container has been initialized.
		if zkcontainer != self.ZkContainer:
			return

		self._leader_zxid = None
		self.LeaderInfo = None
		self.App.PubSub.publish("LeaderService.state/FOLLOWER!", self.LeaderName)


	def _on_change_zookeeper_thread(self, event):
		if not self.IsLeader():
			self._election_thread()


	def _on_tick60(self, event_name):
		if not self.IsLeader():
			# Speculatively run the election thread to become leader - this is a last resort recovery mechanism
			return self.ZkContainer.ProactorService.schedule(self._election_thread)


	def _election_thread(self):
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
				self.ElectionPath + "/" + self.LeaderName,
				leader_data,
				ephemeral=True,  # We want this to disappear when the instance is stopped
				include_data=True,
			)
		except kazoo.exceptions.NodeExistsError:
			leader_data, stats = self.ZkContainer.ZooKeeper.Client.get(self.ElectionPath + "/" + self.LeaderName)
			if stats.czxid == self._leader_zxid:
				# I'm still the leader, no need to become leader again.
				return
			self._leader_zxid = None
			self.LeaderInfo = leader_data
			self.App.PubSub.publish_threadsafe("LeaderService.state/FOLLOWER!", self.LeaderName)
		else:
			self._leader_zxid = stats.czxid
			self.LeaderInfo = leader_data
			self.App.PubSub.publish_threadsafe("LeaderService.state/LEADER!", self.LeaderName)
