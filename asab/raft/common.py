import enum
import socket
import fcntl
import struct
import platform


class StatusCode(enum.IntEnum):
	NOT_LEADER = 1001


def guess_my_ip_address(rpc):
	addresses = set()

	# Use socket.getaddrinfo() & socket.gethostname() to guess IP addresses
	addresses |= set([
		(family, sockaddr[0]) 
		for family, socktype, proto, canonname, sockaddr in socket.getaddrinfo(socket.gethostname(), None)
		if not sockaddr[0].startswith("127.")
	])

	# Use ioctl SIOCGIFADDR call (Linux only)
	if platform.system() == "Linux":
		for ix in socket.if_nameindex():
				d = struct.pack('256s', ix[1][:15].encode("utf-8"))
				try:
					r = fcntl.ioctl(
						rpc.PrimarySocket.fileno(),
						0x8915,  # SIOCGIFADDR
						d
					)
				except OSError:
					continue
				a = socket.inet_ntoa(r[20:24])
				if a.startswith("127."): continue
				addresses.add((socket.AF_INET, a))

	return addresses

