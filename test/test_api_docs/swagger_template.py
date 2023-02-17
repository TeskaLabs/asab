SWAGGER_TEMPLATE = {
    "openapi": "3.0.1",
    "info": {
        "title": "TestApp",
        "description": "Running on: <strong>ServerName</strong> on: <strong>[]</strong><p>This is a test app for TestDocWebHandler.</p>",
        "contact": {
            "name": "ASAB microservice",
            "url": "https://www.github.com/teskalabs/asab"
        },
        "version": {}
    },
    "servers": [
        {
            "url": "../../"
        }
    ],
    "paths": {
        "/path/to/endpoint": {
            "put": {
                "summary": "This is a test handler.",
                "description": "This is a test handler.\n\nReturns:\n        nothing special\n\nHandler: `MockedRouterObject.handler()`",
                "tags": [
                    "test_handler"
                ],
                "responses": {
                    "200": {
                        "description": "Success"
                    }
                }
            }
        }
    },
    "components": {
        "securitySchemes": {}
    }
}