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
import os

# Very verbose logging
logging.basicConfig(
	level=logging.DEBUG,
	format='%(asctime)s.%(msecs)03d [%(levelname)-7s] %(name)s: %(message)s',
	datefmt='%H:%M:%S',
	stream=sys.stdout
)


def read_system_tcp_settings():
	"""Read system TCP timeout settings."""
	print("\n🔧 System TCP Settings:")

	settings_files = [
		("/proc/sys/net/ipv4/tcp_syn_retries", "TCP SYN retries (connection timeout)"),
		("/proc/sys/net/ipv4/tcp_retries2", "TCP data retries (established connection)"),
		("/proc/sys/net/ipv4/tcp_keepalive_time", "TCP keepalive time (seconds)"),
		("/proc/sys/net/ipv4/tcp_keepalive_intvl", "TCP keepalive interval (seconds)"),
		("/proc/sys/net/ipv4/tcp_keepalive_probes", "TCP keepalive probes"),
	]

	for filepath, description in settings_files:
		try:
			with open(filepath, 'r') as f:
				value = f.read().strip()
				print("  {} = {}".format(description, value))
				print("    File: {}".format(filepath))
		except Exception as e:
			print("  {} - Could not read: {}".format(description, e))

	# Calculate approximate connection timeout from tcp_syn_retries
	try:
		with open("/proc/sys/net/ipv4/tcp_syn_retries", 'r') as f:
			syn_retries = int(f.read().strip())
			# TCP connection timeout with exponential backoff:
			# 0s + 1s + 2s + 4s + 8s + 16s + 32s... = roughly (2^(n+1) - 1) seconds
			approx_timeout = (2 ** (syn_retries + 1)) - 1
			print("\n  ℹ️  Approximate TCP connection timeout: ~{}s (with {} SYN retries)".format(approx_timeout, syn_retries))
			print("      Formula: exponential backoff with {} retries".format(syn_retries))
	except Exception:
		pass
	print()


def test_ssh_timing(host, port=22, ssh_key_path=None, username='git'):
	"""Test SSH handshake timing using ssh command."""
	print("\n" + "=" * 60)
	print("📊 MEASUREMENT 3/4: SSH HANDSHAKE")
	print("=" * 60)
	print("Host: {}:{}".format(host, port))
	print("User: {}".format(username))
	if ssh_key_path:
		print("Key: {}".format(ssh_key_path))

	import subprocess

	# Build SSH command with reasonable timeout
	ssh_cmd = ['ssh', '-v', '-T', '-o', 'ConnectTimeout=30', '-o', 'StrictHostKeyChecking=no']

	# Add SSH key if specified
	if ssh_key_path:
		ssh_key_expanded = os.path.expanduser(ssh_key_path)
		if os.path.exists(ssh_key_expanded):
			ssh_cmd.extend(['-i', ssh_key_expanded])
			print("Using SSH key: {}".format(ssh_key_expanded))
		else:
			print("⚠️  SSH key not found: {} - using default key".format(ssh_key_expanded))

	ssh_cmd.extend(['-p', str(port), '{}@{}'.format(username, host), 'exit'])

	ssh_start = time.time()
	try:
		# Run ssh with verbose output
		result = subprocess.run(
			ssh_cmd,
			capture_output=True,
			timeout=35,  # 30s SSH timeout + 5s buffer
			text=True
		)
		ssh_duration = (time.time() - ssh_start) * 1000

		print("✅ SSH handshake completed")
		print("⏱️  Duration: {:.0f}ms".format(ssh_duration))

		# Parse SSH debug output for timing info
		if result.stderr:
			print("\nSSH debug output:")
			for line in result.stderr.split('\n'):
				if 'debug1:' in line and ('Connected' in line or 'Authentication' in line or 'kex:' in line or 'Offering public key' in line):
					print("  {}".format(line.strip()))

		return True, ssh_duration

	except subprocess.TimeoutExpired:
		ssh_duration = (time.time() - ssh_start) * 1000
		print("❌ SSH handshake TIMEOUT")
		print("⏱️  Duration: {:.0f}ms".format(ssh_duration))
		return False, ssh_duration
	except Exception as e:
		ssh_duration = (time.time() - ssh_start) * 1000
		print("❌ SSH test error: {}".format(e))
		print("⏱️  Duration: {:.0f}ms".format(ssh_duration))
		return False, ssh_duration


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
		print("⚠️  Could not extract host from URL")
		return False

	print("Host: {}".format(host))
	print("Port: {}".format(port))
	print("Protocol: {}".format(protocol))

	# Test DNS resolution
	print("\n" + "=" * 60)
	print("📊 MEASUREMENT 1/4: DNS RESOLUTION")
	print("=" * 60)
	dns_start = time.time()
	try:
		ip = socket.gethostbyname(host)
		dns_duration = (time.time() - dns_start) * 1000
		print("✅ DNS OK: {} → {}".format(host, ip))
		print("⏱️  Duration: {:.0f}ms".format(dns_duration))
	except socket.gaierror as e:
		dns_duration = (time.time() - dns_start) * 1000
		print("❌ DNS FAILED: {}".format(e))
		print("⏱️  Duration: {:.0f}ms".format(dns_duration))
		return False

	# Test TCP connection
	print("\n" + "=" * 60)
	print("📊 MEASUREMENT 2/4: TCP CONNECTION")
	print("=" * 60)
	connect_start = time.time()
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(timeout)
		result = sock.connect_ex((host, port))
		sock.close()
		connect_duration = (time.time() - connect_start) * 1000

		if result == 0:
			print("✅ Connection OK to {}:{}".format(host, port))
			print("⏱️  Duration: {:.0f}ms".format(connect_duration))
			return True
		else:
			print("❌ Connection FAILED to {}:{} - error code {}".format(host, port, result))
			print("⏱️  Duration: {:.0f}ms".format(connect_duration))
			return False
	except socket.timeout:
		connect_duration = (time.time() - connect_start) * 1000
		print("❌ Connection TIMEOUT to {}:{}".format(host, port))
		print("⏱️  Duration: {:.0f}ms".format(connect_duration))
		return False
	except Exception as e:
		connect_duration = (time.time() - connect_start) * 1000
		print("❌ Connection ERROR: {}".format(e))
		print("⏱️  Duration: {:.0f}ms".format(connect_duration))
		return False


class DebugApp(asab.Application):
	def __init__(self):
		super().__init__()

		print("\n" + "=" * 80)
		print("🔍 GIT PROVIDER DEBUG - Timing Measurements")
		print("=" * 80)
		print()

		# Read system TCP timeout settings
		read_system_tcp_settings()

		# Get the configured URL and test network
		git_url = asab.Config.get("library", "providers")
		print("📋 Configured URL: {}".format(git_url))

		# Test network connectivity before initializing library
		network_ok = test_network_connectivity(git_url)

		# If SSH, also test SSH handshake timing
		if 'ssh' in git_url or 'git@' in git_url:
			import re
			# Extract host and port
			ssh_match = re.search(r'(?:ssh://)?(?:[^@]+@)?([^:/]+)(?::(\d+))?', git_url)
			if ssh_match:
				host = ssh_match.group(1)
				port = int(ssh_match.group(2)) if ssh_match.group(2) else 22

				# Get SSH key from config
				ssh_key = asab.Config.get("library:git", "ssh_key_path", fallback=None)

				# Extract username from URL
				user_match = re.search(r'(?:ssh://)?([^@]+)@', git_url)
				username = user_match.group(1) if user_match else 'git'

				ssh_ok, ssh_duration = test_ssh_timing(host, port, ssh_key, username)

		if network_ok:
			print("\n✅ Network checks passed - proceeding with git clone\n")
		else:
			print("\n⚠️  Network checks failed - git clone may fail\n")

		print("\n" + "=" * 60)
		print("📊 MEASUREMENT 4/4: GIT CLONE/FETCH")
		print("=" * 60)
		print("Starting LibraryService (git operations will be logged by provider)...")
		print()

		self.LibraryService = asab.library.LibraryService(self, "LibraryService")
		self.PubSub.subscribe("Library.ready!", self.on_ready)

	async def on_ready(self, event_name, library):
		print("\n" + "=" * 80)
		print("✨ LIBRARY READY!")
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
				except Exception:
					pass

		self.stop()


if __name__ == '__main__':
	print("Python: {}".format(sys.version.split()[0]))

	try:
		import pygit2
		print("pygit2: {}".format(pygit2.__version__))
		if hasattr(pygit2, 'LIBGIT2_VERSION'):
			print("libgit2: {}".format(pygit2.LIBGIT2_VERSION))
	except Exception:
		pass

	app = DebugApp()
	app.run()
