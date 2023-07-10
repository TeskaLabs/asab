# How to create a RSS reader

## Contents:

1. Create a `ParserService` that sends requests to a certain RSS feed:
    1. **Config**: make source configurable and explain Config syntax
    2. **PubSub**: schedule the request every 1 minute
2. Create a web server that renders the RSS on a webpage.
   1. **LibraryService** - uses filesystem provider.
   2. 