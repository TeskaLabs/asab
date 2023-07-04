# Containerisation

ASAB is designed for deployment into containers such as LXC/LXD or
Docker. It allows to build e.g. microservices that provides REST
interface or consume MQ messages while being deployed into a container
for a sake of the infrastructure flexibility.

## Running ASAB in a LXC/LXD container

1.  Prepare LXC/LXD container based on Alpine Linux

    ``` bash
    lxc launch images:alpine/3.10 asab
    ```

2.  Swich into a container

    ``` bash
    lxc exec asab -- /bin/ash
    ```

3.  Prepare Python3 environment

    ``` bash
    apk update
    apk upgrade
    apk add --no-cache python3

    python3 -m ensurepip
    ```

4.  Deploy ASAB

    ``` bash
    apk add --virtual .buildenv python3-dev gcc musl-dev git
    pip3 install git+https://github.com/TeskaLabs/asab
    apk del .buildenv
    ```

5.  Deploy dependencies

    ``` bash
    pip3 install python-daemon
    ```

6.  Use OpenRC to automatically start/stop ASAB application

    ``` bash
    vi /etc/init.d/asab-app
    ```

    Adjust the example of [OpenRC init
    file](https://github.com/TeskaLabs/asab/blob/master/doc/asab-openrc).

    ``` bash
    chmod a+x /etc/init.d/asab-app
    rc-update add asab-app
    ```

    !!! note
        If you need to install python packages that require compilation
        using C compiler, you have to add following dependencies:

        ``` bash
        apk add --virtual .buildenv python3-dev
        apk add --virtual .buildenv gcc
        apk add --virtual .buildenv musl-dev
        ```

        And removal of the build tools after pip install:

        ``` bash
        apk del .buildenv
        ```

## Docker Remote API

In order for ASAB applications to read the Docker container name as well
as other information related to the container to be used in logs,
metrics and other analysis, the Docker Remote API must be enabled. To do so:

1.  Open the docker service file:

    ``` bash
    vi /lib/systemd/system/docker.service
    ```

2.  Find the line which starts with `ExecStart` and add `-H=tcp://0.0.0.0:2375`.
3.  Save the file.
4.  Reload the docker daemon and restart the Docker service:

    ``` bash
    sudo systemctl daemon-reload && sudo service docker restart
    ```

    Then in the ASAB application's configuration, provide the Docker Socket
    path in `docker_socket` configuration option:

    ``` bash
    [general]
    docker_socket=<YOUR_DOCKER_SOCKET_FILE>
    ```

Thus, the metric service as well as log manager can use the container
name as hostname instead of container ID, which provides better
readability when analyzing the logs and metrics, typically using
InfluxDB and Grafana.
