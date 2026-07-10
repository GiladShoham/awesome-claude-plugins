# Xquik X Research

Research public X data through Xquik's remote MCP server. The bundled skill
keeps source provenance, pagination, untrusted-content handling, and write
approval in the workflow.

## Install

```text
/plugin marketplace add GiladShoham/awesome-claude-plugins
/plugin install x-twitter-scraper@awesome-claude-plugins
```

Set `XQUIK_API_KEY` in the environment before starting Claude Code. The plugin
expands that value only into the MCP authentication header.

After installation, run `/reload-plugins`, then use `/mcp` to confirm that the
`xquik` server connected.

## Use

Ask Claude to research public posts, users, trends, or engagement evidence. The
skill first discovers the matching Xquik endpoint, then executes the request and
returns a source packet with identifiers, URLs, timestamps, and pagination
state.

Write-like actions require a separate, exact confirmation immediately before
the request. A research request never implies approval to publish or modify X
data.

## Links

- [Xquik](https://xquik.com)
- [Xquik documentation](https://docs.xquik.com)
- [x-twitter-scraper source](https://github.com/Xquik-dev/x-twitter-scraper)
