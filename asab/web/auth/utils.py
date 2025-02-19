import aiohttp
import aiohttp.web
import jwcrypto.jwk
import jwcrypto.jwt
import json
import logging

from ...exceptions import NotAuthenticatedError


L = logging.getLogger(__name__)


def get_bearer_token_from_authorization_header(request: aiohttp.web.Request) -> str:
	"""
	Validate the Authorization header and extract the Bearer token value
	"""
	authorization_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION)
	if authorization_header is None:
		L.debug("No Authorization header.")
		raise NotAuthenticatedError()

	try:
		auth_type, token_value = authorization_header.split(" ", 1)
	except ValueError:
		L.warning("Cannot parse Authorization header.")
		raise NotAuthenticatedError()

	if auth_type != "Bearer":
		L.warning("Unsupported Authorization header type: {!r}".format(auth_type))
		raise NotAuthenticatedError()

	return token_value


def get_id_token_claims(bearer_token: str, auth_server_public_key: jwcrypto.jwk.JWKSet):
	"""
	Parse and validate JWT ID token and extract the claims (user info)
	"""
	assert jwcrypto is not None
	try:
		token = jwcrypto.jwt.JWT(jwt=bearer_token, key=auth_server_public_key)
	except jwcrypto.jwt.JWTExpired:
		L.warning("ID token expired.")
		raise NotAuthenticatedError()
	except jwcrypto.jwt.JWTMissingKey as e:
		raise e
	except jwcrypto.jws.InvalidJWSSignature as e:
		raise e
	except ValueError as e:
		L.error(
			"Failed to parse JWT ID token ({}). Please check if the Authorization header contains ID token.".format(e))
		raise aiohttp.web.HTTPBadRequest()
	except jwcrypto.jws.InvalidJWSObject as e:
		L.error(
			"Failed to parse JWT ID token ({}). Please check if the Authorization header contains ID token.".format(e))
		raise aiohttp.web.HTTPBadRequest()
	except Exception:
		L.exception("Failed to parse JWT ID token. Please check if the Authorization header contains ID token.")
		raise aiohttp.web.HTTPBadRequest()

	try:
		token_claims = json.loads(token.claims)
	except Exception:
		L.exception("Failed to parse JWT token claims.")
		raise aiohttp.web.HTTPBadRequest()

	return token_claims
