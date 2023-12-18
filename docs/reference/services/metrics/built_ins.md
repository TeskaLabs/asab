# Built-in Metrics

## Web Requests Metrics

ASAB `WebService` class automatically
provides metrics counting web requests. There are 5 metrics quantifying
requests to all ASAB endpoints. They use dynamic tags to provide information about the method, path and status of the response.

-   `web_requests` - Counts requests to ASAB endpoints as
    events per minute.
-   `web_requests_duration` - Counts total requests
    duration to ASAB endpoints per minute.
-   `web_requests_duration_min` - Counts minimal request
    duration to ASAB endpoints per minute.
-   `web_requests_duration_max` - Counts maximum request
    duration to ASAB endpoints per minute.
-   `web_requests_duration_hist` - Cumulative histogram
    counting requests in buckets defined by the request duration.

Web Requests Metrics are switched off by default. Use configuration to allow them.
Be aware that both the Web module and Metrics module must be initialized for these metrics.

!!! example "Configuration example"
    ``` {.}
    [asab:metrics]
    web_requests_metrics=true
    ```

## Native Metrics

You can opt out of Native Metrics through configuration by setting
`native_metrics` to `false`. Default is `true`.

!!! example "Configuration example"
    ``` {.}
    [asab:metrics]
    native_metrics=true
    ```

### Memory Metrics

A gauge with the name `os.stat` gathers information about memory usage
by your application.

You can find several metric values there:

-   VmPeak - Peak virtual memory size
-   VmLck - Locked memory size
-   VmPin - Pinned memory size
-   VmHWM - Peak resident set size (\"high water mark\")
-   VmRSS - Resident set size
-   VmData, VmStk, VmExe - Size of data, stack, and text segments
-   VmLib - Shared library code size
-   VmPTE - Page table entries size
-   VmPMD - Size of second-level page tables
-   VmSwap - Swapped-out virtual memory size by anonymous private pages; shmem swap usage is not included

### Logs Counter

There is a default Counter named `logs` with values `warnings`,
`errors`, and `critical`, counting logs with respective levels. It is a
humble tool for application health monitoring.