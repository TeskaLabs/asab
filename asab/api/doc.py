import re
import logging
import inspect

import asab
import aiohttp
import aiohttp.web
import yaml

from .doc_templates import SWAGGER_OAUTH_PAGE, SWAGGER_DOC_PAGE

##

L = logging.getLogger(__name__)

##


class DocWebHandler(object):
    def __init__(self, api_service, app, web_container, config_section_name="asab:doc"):
        self.App = app
        self.WebContainer = web_container
        self.WebContainer.WebApp.router.add_get("/doc", self.doc)
        self.WebContainer.WebApp.router.add_get(
            "/oauth2-redirect.html", self.oauth2_redirect
        )
        self.WebContainer.WebApp.router.add_get("/asab/v1/openapi", self.openapi)

        self.AuthorizationUrl = asab.Config.get(
            config_section_name, "authorizationUrl", fallback=None
        )
        self.TokenUrl = asab.Config.get(config_section_name, "tokenUrl", fallback=None)
        self.Scopes = asab.Config.get(config_section_name, "scopes", fallback=None)

        self.Manifest = api_service.Manifest

    def build_swagger_documentation(self) -> dict:
        specification: dict = {}
        # TODO: check for the add_dict in the primary code
        app_doc_string: str = self.App.__doc__
        additional_info_dict: dict = {}

        description: str = self.add_description(app_doc_string)
        additional_info_dict.update(self.add_additional_info(app_doc_string))
        
        specification.update(self.create_base_info(description))
        specification["components"] = self.create_security_schemes()
        specification["info"]["version"] = self.add_manifest()
        specification["info"]["description"] = self.add_server_and_container_info2(
            description
        )

        if additional_info_dict is not None:
            specification.update(additional_info_dict)

        router_types_dict = {
            "asab-routers": {},
            "doc-routers": {},
            "microservice-routers": {},
        }

        for route in self.WebContainer.WebApp.router.routes():
            if route.method == "HEAD":
                # Skip HEAD methods
                # TODO: once/if there is graphql, its method name is probably `*`
                continue
            specification["paths"].update(self.create_route_info(route))        

        return specification
    
    def create_route_info(self, route) -> dict:
        """
        Example return: 
            /asab/v1/manifest:
            get:
                summary: It returns the manifest of the ASAB service.
                description:
                    "It returns the manifest of the ASAB service.\n\nTHe manifest is\
                    \ a JSON object loaded from `MANIFEST.json` file.\nThe manifest contains the\
                    \ creation (build) time and the version of the ASAB service.\nThe `MANIFEST.json`\
                    \ is produced during the creation of docker image by `asab-manifest.py` script.\n\
                    \nExample of `MANIFEST.json`:\n\n```\n{\n        'created_at': 2022-03-21T15:49:37.14000,\n\
                    \        'version' :v22.9-4\n}\n```\n\n\nHandler: `APIWebHandler.manifest()`"
                tags:
                    - asab.api
                responses:
                    "200":
                        description: Success
        """
        
        route_path = self.get_path_from_route_info(route)
        route_dict: dict = {}
        route_name: str = route.method.lower()
        
        path_object = route_dict.get(route_path)
        if path_object is None:
            route_dict[route_path] = path_object = {}
        path_object[route_name] = self.add_method_description(route)
        
        L.warning(f"route dict: {route_dict}")
        
        return route_dict
        
        
        
    

    def create_base_info(self, description: str) -> dict:
        return {
            "openapi": "3.0.1",
            "info": {
                "title": "{}".format(self.App.__class__.__name__),
                "description": description,
                "contact": {
                    "name": "ASAB microservice",
                    "url": "https://www.github.com/teskalabs/asab",
                },
                "version": "1.0.0",
            },
            "servers": [{"url": "../../"}],  # Base path relative to openapi endpoint
            "paths": {},
            # Authorization
            # TODO: Authorization must not be always of OAuth type
            "components": {},
        }

    def add_description(self, docstring: str | None) -> str:
        """Return the app description if exists."""
        if docstring is not None:
            docstring = inspect.cleandoc(docstring)
            dashes_index = docstring.find(
                "\n---\n"
            )  # find the index of the first three dashes
            
            # everything before --- goes to description
            if dashes_index >= 0:
                description = docstring[
                    :dashes_index
                ]  
            else:
                description = docstring
        else:
            description = ""
        return description

    def add_additional_info(self, docstring: str | None) -> dict:
        """Search for '---' and add everything that comes after into add_dict."""

        additional_info_dict = {}

        if docstring is not None:
            docstring = inspect.cleandoc(docstring)
            dashes_index = docstring.find(
                "\n---\n"
            )  
            if dashes_index >= 0:
                try:
                    additional_info_dict = yaml.load(
                        docstring[dashes_index:], Loader=yaml.SafeLoader
                    )  # everything after --- goes to add_dict
                except yaml.YAMLError as e:
                    L.error(
                        "Failed to parse '{}' doc string {}".format(
                            self.App.__class__.__name__, e
                        )
                    )
        return additional_info_dict

    def create_security_schemes(self) -> dict:
        """Create security schemes if tokenUrl, authorizationUrl and Scopes exist."""
        security_schemes_dict = {}
        if self.AuthorizationUrl and self.TokenUrl:
            security_schemes_dict = {
                "securitySchemes": {
                    "oAuth": {
                        "type": "oauth2",
                        "description": "",
                        "flows": {
                            "authorizationCode": {
                                "authorizationUrl": self.AuthorizationUrl,  # "http://localhost/seacat/api/openidconnect/authorize"
                                "tokenUrl": self.TokenUrl,  # "http://localhost/seacat/api/openidconnect/token"
                                "scopes": {
                                    "openid": "Required Scope for OpenIDConnect!",
                                },
                            }
                        },
                    }
                },
            }
            if self.Scopes:
                for scope in self.Scopes.split(","):
                    security_schemes_dict["securitySchemes"]["oAuth"]["flows"][
                        "authorizationCode"
                    ]["scopes"].update(
                        {"scope": "{} scope.".format(scope.strip().capitalize())}
                    )
        return security_schemes_dict

    def add_manifest(self) -> dict[str]:
        """Add version from MANIFEST.json if exists."""
        version = {}
        if self.Manifest:
            version = self.Manifest["version"]
        return version

    def add_server_and_container_info2(self, description) -> str:
        """Add on which server and web container the user operates into description."""
        return "Running on: <strong>{}</strong> on: <strong>{}</strong>".format(
            self.App.ServerName, self.WebContainer.Addresses
        ) + "<p>{}</p>".format(description)

    def get_path_from_route_info(self, route) -> str:
        route_info = route.get_info()
        if "path" in route_info:
            path = route_info["path"]
        elif "formatter" in route_info:
            # Extract URL parameters from formatter string
            path = route_info["formatter"]
        else:
            L.warning("Cannot obtain path info from route", struct_data=self.route_info)
        return path

    def extract_parameters(self, route) -> list[dict]:
        parameters = []
        route_info = route.get_info()
        if "formatter" in route_info:
            path = route_info["formatter"]
            for params in re.findall(r"\{.*\}", path):
                if "/" in params:
                    for parameter in params.split("/"):
                        parameters.append(
                            {
                                "in": "path",
                                "name": parameter[1:-1],
                                "required": True,
                            }
                        )
                else:
                    parameters.append(
                        {
                            "in": "path",
                            "name": params[1:-1],
                            "required": True,
                        }
                    )
        L.warning(f"parameters: {parameters}")
        return parameters

    def determine_router_types(self) -> dict[list]:
        # TODO: maybe dict with lists is not the right option for storing such data?
        router_types_dict = {
            "asab-routers": [],
            "doc-routers": [],
            "microservice-routers": [],
        }

        for route in self.WebContainer.WebApp.router.routes():
            if route.method == "HEAD":
                # Skip HEAD methods
                # TODO: once/if there is graphql, its method name is probably `*`
                continue
            path = self.get_path_from_route_info(route)
            if re.search("/doc", path) or re.search("/oauth2-redirect.html", path):
                router_types_dict["doc-routers"].append(route)
            elif re.search("asab", path):
                router_types_dict["asab-routers"].append(route)
            else:
                router_types_dict["microservice-routers"].append(route)
        return router_types_dict



    def create_handle_name(self, route) -> str:
        if inspect.ismethod(route.handler):
            if route.handler.__name__ == "validator":
                handler_name = "{}.{}()".format(
                    route.handler.__self__.__class__.__name__,
                    route.handler.__getattribute__("func").__name__,
                )

            else:
                handler_name = "{}.{}()".format(
                    route.handler.__self__.__class__.__name__, route.handler.__name__
                )
        else:
            handler_name = str(route.handler)

        return handler_name

    def create_docstring(self, route) -> str:
        if inspect.ismethod(route.handler):
            if route.handler.__name__ == "validator":
                doc_str = route.handler.__getattribute__("func").__doc__
            else:
                doc_str = route.handler.__doc__
        else:
            doc_str = route.handler.__doc__

        return doc_str

    def create_method_dict(self, route) -> dict:
        method_dict = {}
        if inspect.ismethod(route.handler) and route.handler.__name__ == "validator":
            json_schema = route.handler.__getattribute__("json_schema")
            method_dict["requestBody"] = {
                "content": {"application/json": {"schema": json_schema}},
            }
        return method_dict

    def add_methods(
        self, docstring: str | None, add_dict: dict | None, handler_name: str, parameters: list
    ):

        new_methods: dict = {}

        description: str = self.add_description(docstring)

        description += "\n\nHandler: `{}`".format(handler_name)

        new_methods.update(
            {
                "summary": description.split("\n")[0],
                "description": description,
                "tags": ["general"],
                "responses": {"200": {"description": "Success"}},
            }
        )

        if len(parameters) > 0:
            new_methods["parameters"] = parameters

        if add_dict is not None:
            new_methods.update(add_dict)

        return new_methods

    def add_method_description(self, route) -> dict:
        """Return summary, description, tags and responses for the specified route.
        """
        parameters = self.extract_parameters(route)

        handle_name: str = self.create_handle_name(route)
        doc_string: str = self.create_docstring(route)
        method_dict: dict = self.create_method_dict(route)

        add_dict = self.add_additional_info(doc_string)
        method_dict.update(
            self.add_methods(doc_string, add_dict, handle_name, parameters)
        )
        
        return method_dict
        
        


    def extract_methods_from_route(self, specification: dict, route) -> None:
        path: str = self.get_path_from_route_info(route)
        parameters = self.extract_parameters(route)

        handle_name: str = self.create_handle_name(route)
        doc_string: str = self.create_docstring(route)
        method_dict: dict = self.create_method_dict(route)

        add_dict = self.add_additional_info(doc_string)
        method_dict.update(
            self.add_methods(doc_string, add_dict, handle_name, parameters)
        )

        path_object = specification["paths"].get(path)
        if path_object is None:
            specification["paths"][path] = path_object = {}
        path_object[route.method.lower()] = method_dict

    # This is the web request handler
    async def doc(self, request):
        """
        Access the API documentation using a browser.
        ---
        tags: ['asab.doc']
        """

        swagger_js_url: str = (
            "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js"
        )
        swagger_css_url: str = (
            "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css"
        )

        doc_page = SWAGGER_DOC_PAGE.format(
            title=self.App.__class__.__name__,
            swagger_css_url=swagger_css_url,
            swagger_js_url=swagger_js_url,
            openapi_url="./asab/v1/openapi",
        )

        return aiohttp.web.Response(text=doc_page, content_type="text/html")

    def oauth2_redirect(self, request):
        """
        Required for the authorization to work.
        ---
        tags: ['asab.doc']
        """

        return aiohttp.web.Response(text=SWAGGER_OAUTH_PAGE, content_type="text/html")

    async def openapi(self, request):
        """
        Download OpenAPI (version 3) API documentation (aka Swagger) in YAML.
        ---
        tags: ['asab.doc']
        externalDocs:
                description: OpenAPI Specification
                url: https://swagger.io/specification/

        """
        return aiohttp.web.Response(
            text=(yaml.dump(self.build_swagger_documentation(), sort_keys=False)),
            content_type="text/yaml",
        )
