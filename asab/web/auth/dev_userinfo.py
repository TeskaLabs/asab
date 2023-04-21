EXAMPLE = {
  "iss": "auth.test.loc",
  "iat": 1682077901,
  "exp": 1682092289,
  "azp": "my-asab-app",
  "aud": "my-asab-app",
  "sub": "mongodb:default:799b539029d1442d9064990d52908cca",
  "preferred_username": "little.capybara",
  "email": "capybara1999@example.com",
  "resources": {
    "*": ["wisdom:access"],
    "test-tenant": [
      "wisdom:access",
      "cake:access",
      "cake:eat"
    ]
  },
  "tenants": [
    "test-tenant"
  ]
}