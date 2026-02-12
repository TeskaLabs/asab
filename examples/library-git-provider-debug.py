#!/usr/bin/env python3
"""
Simple git provider debug script with timing measurements.
"""
import asab
import asab.library
import logging
import sys
import time
import socket
import re

# Very verbose logging
logging.basicConfig(
	level=logging.DEBUG,
	format='%(asctime)s.%(msecs)03d [%(levelname)-7s] %(name)s: %(message)s',
	datefmt='%H:%M:%S',
	stream=sys.stdout
)


def test_network_connectivity(url, timeout=5):
	"""Test if we can connect to the git server."""
	print("\n🌐 Testing network connectivity...")
	
	# Extract host and port from URL
	host = None
	port = None
	protocol = None
	
	# Try HTTP/HTTPS
	http_match = re.search(r'git\+(https?)://[^@]*@?([^:/]+)(?::(\d+))?', url)
	if http_match:
		protocol = http_match.group(1).upper()
		host = http_match.group(2)
		port = int(http_match.group(3)) if http_match.group(3) else (443 if protocol == 'HTTPS' else 80)
	else:
		# Try SSH
		ssh_match = re.search(r'git\+(?:ssh://)?(?:[^@]+@)?([^:/]+)(?::(\d+))?', url)
		if ssh_match:
			protocol = "SSH"
			host = ssh_match.group(1)
			port = int(ssh_match.group(2)) if ssh_match.group(2) else 22
	
	if not host:
		print("  ⚠️  Could not extract host from URL")
		return False
	
	print("  Host: {}".format(host))
	print("  Port: {}".format(port))
	print("  Protocol: {}".format(protocol))
	
	# Test DNS resolution
	print("\n🔍 DNS resolution...")
	dns_start = time.time()
	try:
		ip = socket.gethostbyname(host)
		dns_duration = (time.time() - dns_start) * 1000
		print("  ✅ DNS OK: {} → {} ({:.0f}ms)".format(host, ip, dns_duration))
	except socket.gaierror as e:
		dns_duration = (time.time() - dns_start) * 1000
		print("  ❌ DNS FAILED: {} ({:.0f}ms)".format(e, dns_duration))
		return False
	
	# Test TCP connection
	print("\n🔌 TCP connection test...")
	connect_start = time.time()
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(timeout)
		result = sock.connect_ex((host, port))
		sock.close()
		connect_duration = (time.time() - connect_start) * 1000
		
		if result == 0:
			print("  ✅ Connection OK to {}:{} ({:.0f}ms)".format(host, port, connect_duration))
			return True
		else:
			print("  ❌ Connection FAILED to {}:{} - error code {} ({:.0f}ms)".format(
				host, port, result, connect_duration))
			return False
	except socket.timeout:
		connect_duration = (time.time() - connect_start) * 1000
		print("  ❌ Connection TIMEOUT to {}:{} after {:.0f}ms".format(host, port, connect_duration))
		return False
	except Exception as e:
		connect_duration = (time.time() - connect_start) * 1000
		print("  ❌ Connection ERROR: {} ({:.0f}ms)".format(e, connect_duration))
		return False


class DebugApp(asab.Application):
	def __init__(self):
		super().__init__()
		
		self.StartTime = time.time()
		
		print("\n" + "=" * 80)
		print("🔍 GIT PROVIDER DEBUG - Timing Measurements")
		print("=" * 80)
		print()
		
		# Get the configured URL and test network
		git_url = asab.Config.get("library", "providers")
		print("📋 Configured URL: {}".format(git_url))
		
		# Test network connectivity before initializing library
		network_ok = test_network_connectivity(git_url)
		if network_ok:
			print("\n✅ Network checks passed - proceeding with git clone\n")
		else:
			print("\n⚠️  Network checks failed - git clone may fail\n")
		
		self.LibraryService = asab.library.LibraryService(self, "LibraryService")
		self.PubSub.subscribe("Library.ready!", self.on_ready)
		
		# Show progress
		self.PubSub.subscribe("Application.tick/5!", self.on_tick)
		self.Ticks = 0
	
	async def on_tick(self, event_name):
		self.Ticks += 1
		elapsed = time.time() - self.StartTime
		print("⏱️  [{:.1f}s] Waiting for library... (tick {})".format(elapsed, self.Ticks))
	
	async def on_ready(self, event_name, library):
		total_ms = (time.time() - self.StartTime) * 1000
		
		print("\n" + "=" * 80)
		print("✨ READY! Total time: {:.1f}ms ({:.2f}s)".format(total_ms, total_ms / 1000))
		print("=" * 80)
		
		# Show repository info
		if self.LibraryService.Libraries:
			provider = self.LibraryService.Libraries[0]
			print("\n📦 Repository:")
			print("  URL: {}".format(provider.URLPath))
			print("  Path: {}".format(provider.RepoPath))
			print("  Branch: {}".format(provider.Branch or "(default)"))
			
			if hasattr(provider, 'GitRepository') and provider.GitRepository:
				try:
					head = provider.GitRepository.head.peel()
					print("\n📝 Current commit:")
					print("  SHA: {}".format(head.id))
					print("  Message: {}".format(head.message.strip()))
				except:
					pass
		
		print("\n" + "=" * 80)
		print("📊 Check logs above for detailed timing of each operation")
		print("=" * 80)
		
		self.stop()


if __name__ == '__main__':
	print("Python: {}".format(sys.version.split()[0]))
	
	try:
		import pygit2
		print("pygit2: {}".format(pygit2.__version__))
		if hasattr(pygit2, 'LIBGIT2_VERSION'):
			print("libgit2: {}".format(pygit2.LIBGIT2_VERSION))
	except:
		pass
	
	app = DebugApp()
	app.run()
