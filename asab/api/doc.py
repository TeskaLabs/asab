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


    def build_new(self) -> dict[str]:
        specification = {}
        add_dict = None
        
        additional_info_dict = {}
        
        description = self.add_app_description()
        additional_info_dict.update(self.add_additional_app_info())
        
        specification.update(self.add_info(description))
        
        L.warning(f"specification: {specification}")
        L.warning(f"description: {description}")
        L.warning(f"add_dict: {additional_info_dict}")
        
        return specification

    def add_info(self, description: str) -> dict[str]:
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

    def add_app_description(self) -> str:
        """Return the app description if exists.
        """

        doc_str = self.App.__doc__

        if doc_str is not None:
            doc_str = inspect.cleandoc(doc_str)
            dashes_index = doc_str.find("\n---\n") # find the index of the first three dashes
            if dashes_index >= 0:
                description = doc_str[:dashes_index] # everything before --- goes to description
            else:
                description = doc_str
        else:
            description = ""
        return description
        
    def add_additional_app_info(self) -> dict:
        """Search for '---' and add everything that comes after into add_dict.
        """

        doc_string = self.App.__doc__
        additional_info_dict = {}
        
        if doc_string is not None:
            doc_string = inspect.cleandoc(doc_string)
            dashes_index = doc_string.find("\n---\n") # find the index of the first three dashes
            if dashes_index >= 0:
                try:
                    additional_info_dict = yaml.load(doc_string[dashes_index:], Loader=yaml.SafeLoader) # everything after --- goes to add_dict
                except yaml.YAMLError as e:
                    L.error(
                        "Failed to parse '{}' doc string {}".format(
                            self.App.__class__.__name__, e
                        ))
        return additional_info_dict


    def build_swagger_specification(self) -> dict[str]:
        """Take a docstring of a class and a docstring of methods and merge them
        into a Swagger specification.

        Returns:
                dict[str]: OpenAPI definitions for the Swagger documentation.
        """

        self.specs = {}
        self.description = self.create_description()
        self.prepare_specs()
        self.add_security_schemes()
        self.extract_scopes()
        self.add_version_from_manifest()
        self.add_server_and_container_info()

        if self.add_dict is not None:
            self.specs.update(self.add_dict)
            
        self.asab_routers = []
        self.service_routers = []
        self.doc_routers = []
        
        for route in self.WebContainer.WebApp.router.routes():
            if route.method == "HEAD":
                # Skip HEAD methods
                # TODO: once/if there is graphql, its method name is probably `*`
                continue
            self.parameters = []
            
            self.get_path(route)
            self.determine_router_type(route)
        
        L.warning(f"asab routers: {self.asab_routers}")
        L.warning(f"service routers: {self.service_routers}")
        L.warning(f"doc routers: {self.doc_routers}")

        for route in self.service_routers:
            if route.method == "HEAD":
                # Skip HEAD methods
                # TODO: once/if there is graphql, its method name is probably `*`
                continue
            
            self.get_path(route)
            
            self.parameters = []
            self.method_dict = {}

            self.create_handle_name_and_docstring(route)
            self.update_methods(route)
            
            
            path_object = self.specs["paths"].get(self.path)
            if path_object is None:
                self.specs["paths"][self.path] = path_object = {}
            path_object[route.method.lower()] = self.method_dict

        for route in self.asab_routers:
            if route.method == "HEAD":
                # Skip HEAD methods
                # TODO: once/if there is graphql, its method name is probably `*`
                continue

            self.get_path(route)
            
            self.parameters = []
            self.method_dict = {}

            self.create_handle_name_and_docstring(route)
            self.update_methods(route)
            
            path_object = self.specs["paths"].get(self.path)
            if path_object is None:
                self.specs["paths"][self.path] = path_object = {}
            path_object[route.method.lower()] = self.method_dict
            
        for route in self.doc_routers:
            if route.method == "HEAD":
                # Skip HEAD methods
                # TODO: once/if there is graphql, its method name is probably `*`
                continue

            self.get_path(route)
            
            self.parameters = []
            self.method_dict = {}

            self.create_handle_name_and_docstring(route)
            self.update_methods(route)
            
            path_object = self.specs["paths"].get(self.path)
            if path_object is None:
                self.specs["paths"][self.path] = path_object = {}
            path_object[route.method.lower()] = self.method_dict

        return self.specs


    def create_description(self) -> str:

        self.add_dict = None
        doc_str = self.App.__doc__

        if doc_str is not None:
            doc_str = inspect.cleandoc(doc_str)
            i = doc_str.find("\n---\n")
            if i >= 0:
                description = doc_str[:i]
                try:
                    self.add_dict = yaml.load(doc_str[i:], Loader=yaml.SafeLoader)
                except yaml.YAMLError as e:
                    L.error(
                        "Failed to parse '{}' doc string {}".format(
                            self.App.__class__.__name__, e
                        )
                    )
            else:
                description = doc_str
        else:
            description = ""
        return description

    def prepare_specs(self):
        """
        Prepare basic structure of the specification. Add metadata and info section.
        """

        self.specs = {
            "openapi": "3.0.1",
            "info": {
                "title": "{}".format(self.App.__class__.__name__),
                "description": self.description,
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
        
    
    def add_security_schemes(self):
        """Add security schemes if authorizationUrl and tokenUrl exist."""

        if self.AuthorizationUrl and self.TokenUrl:
            self.specs["components"].update(
                {
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
            )

    def extract_scopes(self):
        """Get all the scopes from config and put them into scopes."""
        if self.Scopes and self.AuthorizationUrl and self.TokenUrl:
            for scope in self.Scopes.split(","):
                self.specs["components"]["securitySchemes"]["oAuth"]["flows"][
                    "authorizationCode"
                ]["scopes"].update(
                    {scope: "{} scope.".format(scope.strip().capitalize())}
                )

    def add_version_from_manifest(self):
        """Add version from MANIFEST.json if exists."""
        if self.Manifest:
            self.specs["info"]["version"] = self.Manifest["version"]

    def add_server_and_container_info(self):
        """Add on which server and web container the user operates into description."""
        self.specs["info"][
            "description"
        ] = "Running on: <strong>{}</strong> on: <strong>{}</strong>".format(
            self.App.ServerName, self.WebContainer.Addresses
        ) + "<p>{}</p>".format(
            self.description
        )


    def get_path(self, route):
        self.route_info = route.get_info()
        if "path" in self.route_info:
            self.path = self.route_info["path"]
        elif "formatter" in self.route_info:
            # Extract URL parameters from formatter string
            self.path = self.route_info["formatter"]

            for params in re.findall(r"\{.*\}", self.path):
                if "/" in params:
                    for parameter in params.split("/"):
                        self.parameters.append(
                            {
                                "in": "path",
                                "name": parameter[1:-1],
                                "required": True,
                            }
                        )
                else:
                    self.parameters.append(
                        {
                            "in": "path",
                            "name": params[1:-1],
                            "required": True,
                        }
                    )
        else:
            L.warning("Cannot obtain path info from route", struct_data=self.route_info)

    def create_handle_name_and_docstring(self, route):
        if inspect.ismethod(route.handler):
            if route.handler.__name__ == "validator":
                json_schema = route.handler.__getattribute__("json_schema")
                self.doc_str = route.handler.__getattribute__("func").__doc__

                self.method_dict["requestBody"] = {
                    "content": {"application/json": {"schema": json_schema}},
                }
                self.handler_name = "{}.{}()".format(
                    route.handler.__self__.__class__.__name__,
                    route.handler.__getattribute__("func").__name__,
                )

            else:
                self.handler_name = "{}.{}()".format(
                    route.handler.__self__.__class__.__name__, route.handler.__name__
                )
                self.doc_str = route.handler.__doc__

        else:
            self.handler_name = str(route.handler)
            self.doc_str = route.handler.__doc__

    def update_methods(self, route):
        self.add_dict = None

        if self.doc_str is not None:
            self.doc_str = inspect.cleandoc(self.doc_str)
            i = self.doc_str.find("\n---\n")
            if i >= 0:
                self.description = self.doc_str[:i]
                try:
                    self.add_dict = yaml.load(self.doc_str[i:], Loader=yaml.SafeLoader)
                except yaml.YAMLError as e:
                    L.error(
                        "Failed to parse '{}' doc string {}".format(
                            self.handler_name, e
                        )
                    )
            else:
                self.description = self.doc_str
        else:
            self.description = ""

        self.description += "\n\nHandler: `{}`".format(self.handler_name)

        self.method_dict.update(
            {
                "summary": self.description.split("\n")[0],
                "description": self.description,
                "tags": ["general"],
                "responses": {"200": {"description": "Success"}},
            }
        )

        if len(self.parameters) > 0:
            self.method_dict["parameters"] = self.parameters

        if self.add_dict is not None:
            self.method_dict.update(self.add_dict)

    def determine_router_type(self, route):
        if re.search("/doc", self.path) or re.search(
            "/oauth2-redirect.html", self.path
        ):
            self.doc_routers.append(route)
        elif re.search("asab", self.path):
            L.warning("asab in path: {}".format(self.path))
            self.asab_routers.append(route)
        else:
            L.warning("asab NOT in path: {}".format(self.path))
            self.service_routers.append(route)

    def add_methods_to_path(self, route):
        path_object = self.specs["paths"].get(self.path)
        if path_object is None:
            self.specs["paths"][self.path] = path_object = {}
        path_object[route.method.lower()] = self.method_dict

    

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
            text=(yaml.dump(self.build_new(), sort_keys=False)),
            content_type="text/yaml",
        )
