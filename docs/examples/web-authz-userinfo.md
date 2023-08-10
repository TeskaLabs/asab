---
author: robin.hruska@teskalabs.com
commit: eae5fe4fbef9254e11e87165e1d34d2bc1db2809
date: 2023-02-15 18:58:47+01:00
title: Web authz userinfo

---

!!! example

	```python title='web-authz-userinfo.py' linenums="1"
	import logging
	
	import asab
	import asab.web
	import asab.web.authz
	import asab.web.rest
	import asab.web.tenant
	
	#
	
	L = logging.getLogger(__name__)
	
	#
	
	
	class MyApplication(asab.Application):
		"""
		MyApplication serves endpoints which use user info obtained from ID tokens issued by the authorization server.
	
		Test by:
		1) Run NGINX server with Seacat Auth (at localhost:8081)
		2) Run this example app with config file:
			```sh
			python3 examples/web-authz-userinfo.py -c examples/web-authz-userinfo.conf
			```
		1) In Seacat Admin UI, register a public web client for this app, with client_id="example-app"
		3) Set up a NGINX location with intropection for this example app:
			```nginx
			location /example {
				rewrite ^/example/(.*)? /$1 break;
				proxy_pass http://localhost:8089;
	
				auth_request /_example_cookie_introspect;
				error_page 401 /auth/api/openidconnect/authorize?response_type=code&scope=openid%20cookie%20profile&client_id=example-app&redirect_uri=$request_uri;
	
				auth_request_set      $authorization $upstream_http_authorization;
				proxy_set_header      Authorization $authorization;
	
				auth_request_set      $cookie $upstream_http_cookie;
				proxy_set_header      Cookie $cookie;
	
				auth_request_set   $set_cookie $upstream_http_set_cookie;
				add_header	Set-Cookie $set_cookie;
			}
	
			location = /_example_cookie_introspect {
				internal;
				proxy_method          POST;
				proxy_set_body        "$http_authorization";
				proxy_pass            http://auth_api/cookie/nginx?client_id=example-app;
				proxy_ignore_headers  Cache-Control Expires Set-Cookie;
			}
			```
		4) Access "https://YOUR_DOMAIN/example/user" in your browser
		"""
	
		async def initialize(self):
			# Loading the web service module
			self.add_module(asab.web.Module)
	
			# Locate web service
			websvc = self.get_service("asab.WebService")
	
			# Create a dedicated web container
			container = asab.web.WebContainer(websvc, "web")
	
			# Add authz service
			# It is required by asab.web.authz.required decorator
			authz_service = asab.web.authz.AuthzService(self)
			container.WebApp.middlewares.append(
				asab.web.authz.authz_middleware_factory(self, authz_service)
			)
	
			# Enable exception to JSON exception middleware
			container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)
	
			# Add a route
			container.WebApp.router.add_get('/user', self.get_userinfo)
	
		@asab.web.authz.userinfo_handler
		async def get_userinfo(self, request, *, userinfo):
			message = "Hi {}, your email is {}".format(
				userinfo.get("preferred_username"),
				userinfo.get("email")
			)
			return asab.web.rest.json_response(request=request, data={"message": message})
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
