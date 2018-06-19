import aiohttp

class RaftWebApi(object):


	def __init__(self, app, rpc):
		self.App = app
		self.Root = '/raft'

		# Locate web service
		websvc = app.get_service("asab.WebService")	

		websvc.WebApp.router.add_get('{}/status'.format(self.Root), self.status)


	async def status(self, request):
		raftsvc = self.App.get_service("asab.RaftService")
		status = "Raft server state: {} {}\n".format(raftsvc.Server.State, raftsvc.Server.State.CurrentTerm)

		for peer in raftsvc.Server.Peers:
			status += ' - {} {} {}\n'.format(peer.Id, peer.Address, peer.RPCdue)

		status += '\n'
		return aiohttp.web.Response(text=status)
