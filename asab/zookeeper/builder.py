from urllib.parse import urlparse
import aiozk

"""
This module builds ZooKeeper clients from Configs and urls
"""

async def build_client(Config, z_url):
    # Parse URL
	url_pieces = urlparse(z_url)
	url_netloc = url_pieces.netloc

	#If there is no location, use implied
	if not url_netloc:
		url_netloc = Config["asab:zookeper"]["servers"]

	#Create and return the client
	client = aiozk.ZKClient(url_netloc)
	return client
