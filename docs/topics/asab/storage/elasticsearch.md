
Storing data in ElasticSearch
-----------------------------

When using ElasticSearch, add configurations for URL, username and
password.

``` {.ini}
[asab:storage]
type=elasticsearch
elasticsearch_url=http://localhost:9200/
elasticsearch_username=JohnDoe
elasticsearch_password=lorem_ipsum_dolor?sit_amet!2023
```

You can also specify the [refreshing
parameter](https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-refresh.html#docs-refresh)
and scroll timeout for [ElasticSearch Scroll
API](https://www.elastic.co/guide/en/elasticsearch//reference/current/scroll-api.html).

``` {.ini}
[asab:storage]
refresh=true
scroll_timeout=1m
```

ElasticSearch Storage provides in addition other methods for creating
index templates, mappings etc (see the Reference section).