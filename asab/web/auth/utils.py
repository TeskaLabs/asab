import typing
import aiohttp
import aiohttp.web
import jwcrypto.jwk
import jwcrypto.jwt
import json
import logging

from ...exceptions import NotAuthenticatedError


L = logging.getLogger(__name__)


def get_bearer_token_from_authorization_header(request: aiohttp.web.Request) -> typing.Tuple[str, str]:
	"""
	Validate the Authorization header and extract the authentication scheme and token value

	Args:
		request: The aiohttp request object containing the Authorization header.

	Returns:
		A tuple containing the authentication scheme and the token value.

	Raises:
		NotAuthenticatedError: If the Authorization header is missing, cannot be parsed,
			or uses an unsupported authentication scheme.
	"""
	authorization_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION)
	if authorization_header is None:
		L.debug("No Authorization header.")
		raise NotAuthenticatedError()

	try:
		auth_scheme, token_value = authorization_header.split(None, 1)
	except ValueError:
		L.warning(
			"Authorization header is present but malformed; expected 'Scheme <token>'.",
			struct_data={"path": request.path},
		)
		raise NotAuthenticatedError() from None

	if not token_value:
		L.warning(
			"Authorization header is present but contains no token value.",
			struct_data={"path": request.path},
		)
		raise NotAuthenticatedError()

	return auth_scheme.casefold(), token_value


def get_bearer_token_from_websocket_request(request: aiohttp.web.Request) -> typing.Tuple[str, str] | None:
	"""
	Extract the authentication scheme and token value from the WebSocket protocol header.
	This is a workaround used in ASAB to pass the access token to the WebSocket connection.

	Args:
		request: The aiohttp request object containing the WebSocket protocol header.

	Returns:
		A tuple containing the authentication scheme ("bearer") and the token value,
		or None if no access token protocol is found.
	"""
	protocol = request.headers.get('sec-websocket-protocol')
	if protocol is not None:
		for p in protocol.split(','):
			p = p.strip()
			if not p.startswith('access_token_'):
				continue
			return "bearer", p[len('access_token_'):]
	return None


def get_id_token_claims(bearer_token: str, auth_server_public_key: jwcrypto.jwk.JWKSet):
	"""
	Parse and validate JWT ID token and extract the claims (user info)

	Args:
		bearer_token: The JWT token string to parse and validate.
		auth_server_public_key: The JWKSet containing the public key used to verify the token signature.

	Returns:
		A dictionary containing the token claims (user information).

	Raises:
		NotAuthenticatedError: If the token is expired, cannot be parsed, or signature verification fails.
		JWTMissingKey: If the key required to verify the token is missing from the JWKSet.
		InvalidJWSSignature: If the token signature is invalid.
	"""
	assert jwcrypto is not None
	try:
		token = jwcrypto.jwt.JWT(jwt=bearer_token, key=auth_server_public_key)
	except jwcrypto.jwt.JWTExpired:
		L.warning("ID token has expired; request authentication rejected.")
		raise NotAuthenticatedError()
	except jwcrypto.jwt.JWTMissingKey as e:
		raise e
	except jwcrypto.jws.InvalidJWSSignature as e:
		raise e
	except ValueError:
		L.debug("Authentication failed: Bearer token is likely not a JWT ID token.")
		raise NotAuthenticatedError()
	except jwcrypto.jws.InvalidJWSObject:
		L.debug("Authentication failed: Bearer token contains an invalid JWT object.")
		raise NotAuthenticatedError()
	except Exception as e:
		L.debug(
			"Failed to parse JWT ID token ({}). Please check if the Authorization header contains ID token.".format(e))
		raise NotAuthenticatedError()

	try:
		token_claims = json.loads(token.claims)
	except Exception:
		L.error("ID token claims could not be decoded as JSON; token may be corrupted.")
		raise NotAuthenticatedError()

	return token_claims
