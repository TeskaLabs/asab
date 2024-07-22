# Transport Layer Security

!!! warning
    :material-excavator: This part of ASAB is currently under construction. :material-excavator:

**Transport Layer Security** protocol (*TLS*, also known as *"Secure Sockets Layer"*) is a cryptographic protocol that provides communication security over a computer network, so that the web servers can use **HTTPS**.

For adding the HTTPS to ASAB web applications, there is a `asab.tls.SSLContextBuilder` class that is connected to [`asab.web.WebContainer`](../web/web-server/#asab.web.WebContainer).

## Configuration options

| Option | Meaning |
| --- | --- |
| `cert` | Path to a PEM file containing the certificate as well as any number of CA certificates needed to establish the certificate’s authenticity |
| `key` | Path to a file containing the private key. If not provided, the private key will be taken from the file specified in `cert`.|
| `cafile` | Path to a file containing the CA |
| `capath` | Path to a directory containing CA certificates |
| `cadata` | String containing CA certificates in PEM format |
| `ciphers` |  String specifying the allowed SSL/TLS ciphers for the connection |
| `dh_params` | Path to a file containing Diffie-Hellman parameters for key exchange |
| `verify_mode` | Control the verification mode for peer certificates. Possible values are `'CERT_NONE'` (no certificate verification), `'CERT_OPTIONAL'` (verification but not required), and `'CERT_REQUIRED'` (verification required) |
| `check_hostname` | :material-excavator: |
| `options` | :material-excavator: |

::: asab.tls.SSLContextBuilder
