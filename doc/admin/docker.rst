ASAB in Docker
=================

.. py:currentmodule:: asab

ASAB-based applications can be run inside a Docker container based
on various operation systems (Debian, Ubuntu, Alpine ...).

The sample `Dockerfile` based on Alpine is located in the repository.

Docker Remote API
------------

In order for ASAB applications to read the Docker container name
as well as other information related to the container to be used in logs, metrics and other analysis,
the Docker Remote API must be enabled.

To do so:

- Open the docker service file: `vi /lib/systemd/system/docker.service`
- Find the line which starts with ExecStart and add `-H=tcp://0.0.0.0:2375`
- Save the file
- Reload the docker daemon and restart the Docker service: `systemctl daemon-reload && sudo service docker restart`

Then in the ASAB application's configuration, provide
the Docker Remote API URL in `docker_remote_api` configuration option:

.. code-block:: bash

	[general]
	docker_remote_api=http://<YOUR_HOST_COMPUTER>:2375

Thus, the metric service as well as log manager can use the container
name as hostname instead of container ID, which provides better readability
when analyzing the logs and metrics, typically using InfluxDB and Grafana.
