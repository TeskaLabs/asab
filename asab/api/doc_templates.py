SWAGGER_OAUTH_PAGE = """<!doctype html>
<html lang="en-US">
<head>
	<title>Swagger UI: OAuth2 Redirect</title>
</head>
<body>
<script>
	'use strict';
	function run () {
		var oauth2 = window.opener.swaggerUIRedirectOauth2;
		var sentState = oauth2.state;
		var redirectUrl = oauth2.redirectUrl;
		var isValid, qp, arr;

		if (/code|token|error/.test(window.location.hash)) {
			qp = window.location.hash.substring(1);
		} else {
			qp = location.search.substring(1);
		}

		arr = qp.split("&");
		arr.forEach(function (v,i,_arr) { _arr[i] = '"' + v.replace('=', '":"') + '"';});
		qp = qp ? JSON.parse('{' + arr.join() + '}',
				function (key, value) {
					return key === "" ? value : decodeURIComponent(value);
				}
		) : {};

		isValid = qp.state === sentState;

		if ((
			oauth2.auth.schema.get("flow") === "accessCode" ||
			oauth2.auth.schema.get("flow") === "authorizationCode" ||
			oauth2.auth.schema.get("flow") === "authorization_code"
		) && !oauth2.auth.code) {
			if (!isValid) {
				oauth2.errCb({
					authId: oauth2.auth.name,
					source: "auth",
					level: "warning",
					message: "Authorization may be unsafe, passed state was changed in server. The passed state wasn't returned from auth server."
				});
			}

			if (qp.code) {
				delete oauth2.state;
				oauth2.auth.code = qp.code;
				oauth2.callback({auth: oauth2.auth, redirectUrl: redirectUrl});
			} else {
				let oauthErrorMsg;
				if (qp.error) {
					oauthErrorMsg = "["+qp.error+"]: " +
						(qp.error_description ? qp.error_description+ ". " : "no accessCode received from the server. ") +
						(qp.error_uri ? "More info: "+qp.error_uri : "");
				}

				oauth2.errCb({
					authId: oauth2.auth.name,
					source: "auth",
					level: "error",
					message: oauthErrorMsg || "[Authorization failed]: no accessCode received from the server."
				});
			}
		} else {
			oauth2.callback({auth: oauth2.auth, token: qp, isValid: isValid, redirectUrl: redirectUrl});
		}
		window.close();
	}

	if (document.readyState !== 'loading') {
		run();
	} else {
		document.addEventListener('DOMContentLoaded', function () {
			run();
		});
	}
</script>
</body>
</html>"""

SWAGGER_DOC_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<link type="text/css" rel="stylesheet" href="{swagger_css_url}">
	<title>{title} API Documentation</title>
	<style>
		code {{ tab-size: 4; }}
		pre {{ tab-size: 4; }}
	</style>
</head>
<body>
<div id="swagger-ui"></div>
<script src="{swagger_js_url}"></script>
<script>
window.onload = () => {{
	window.ui = SwaggerUIBundle({{
		url: '{openapi_url}',
		dom_id: '#swagger-ui',
		presets: [
			SwaggerUIBundle.presets.apis,
			SwaggerUIBundle.SwaggerUIStandalonePreset
		]
	}})
}}
</script>
</body>
</html>"""
