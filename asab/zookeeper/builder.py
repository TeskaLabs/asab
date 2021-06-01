from urllib.parse import urlparse
import aiozk
import logging

L = logging.getLogger(__name__)


"""
This module builds ZooKeeper clients from Configs and urls
urls supported :
1. Absolute url.
Example: zookeeper://zookeeper:12181/etc/configs/file1
2. Relative ur1 with full path
	Example: zookeeper:///etc/configs/file1
	In this case the relative url is expanded as follows:
	zookeeper://{default_server}/etc/configs/file1
	Where {default_server} is substituted with the server entry of the [asab:zookeeper] configuration file section.
3. Relative url with relative path
Example: zookeeper:./etc/configs/file1
	In this case, the relative url is expanded as follows:
	zookeper://{default_server}/{default_path}/etc/configs/file1
	Where {default_server} is substituted with the "server" entry of the [asab:zookeeper] configuration file section and
	{default_path} is substituted with the "path" entry of the [asab:zookeeper] configuration file section.
Sample config file:

[asab.zookeeper]
server=server1 server2 server3      <-- Default server
path=/myfolder                      <-- Default path
"""


def build_client(Config, z_url):
	# Parse URL
	url_pieces = urlparse(z_url)
	url_netloc = url_pieces.netloc
	url_path = url_pieces.path

	# If there is no location, use implied
	if not url_netloc:
		# if server entry is missing exit
		if Config.has_option("asab:zookeeper", "servers"):
			L.error("Servers entry not passes")
			return
		url_netloc = Config["asab:zookeeper"]["servers"]

	if url_path.startswith("./"):
		# if path entry is missing exit
		if Config.has_option("asab:zookeeper", "path"):
			L.error("Path entry not passes")
			return
		url_path = Config["asab:zookeeper"]["path"] + url_path[1:]

	# Create and return the client and the url-path
	client = aiozk.ZKClient(url_netloc)
	return client, url_path
