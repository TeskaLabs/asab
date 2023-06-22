systemd
=======

1.  Create a new Systemd unit file in /etc/systemd/system/:

``` {.bash}
$ sudo vi /etc/systemd/system/asab.service
```

Adjust the example of [SystemD unit
file](https://github.com/TeskaLabs/asab/blob/master/doc/asab.service).

2.  Let systemd know that there is a new service:

``` {.bash}
$ sudo systemctl enable asab
```

To reload existing unit file after changing, use this:

``` {.bash}
$ sudo systemctl daemon-reload
```

3.  ASAB Application Server service for systemd is now ready.

Start of ASAB Server
--------------------

``` {.bash}
$ sudo service asab start
```

Stop of ASAB Server
-------------------

``` {.bash}
$ sudo service asab stop
```
