# Plugin Definitions

This directory contains plugin definitions for all plugins available in the Awesome Claude Plugins marketplace.

**Note:** The plugin structure follows the [official Claude Code plugin format](https://github.com/anthropics/claude-code/tree/main/plugins).

## Plugin Structure

Each plugin is organized as a directory with the following structure:

```
plugin-name/
├── .claude-plugin/         # Plugin configuration directory
│   └── plugin.json         # Plugin metadata (JSON)
├── skills/                 # Model-invoked skills (optional)
├── .mcp.json               # MCP server configuration (optional)
├── hooks/                  # Lifecycle hooks
├── agents/                 # Agent definitions
└── commands/               # Custom commands
```

## Plugin Metadata (.claude-plugin/plugin.json)

The `.claude-plugin` directory contains a `plugin.json` file with the plugin metadata in JSON format with the following structure:

### Required Fields

- `name` (string): Unique identifier for the plugin (lowercase, hyphens allowed)
- `version` (string): Semantic version (e.g., "1.0.0")
- `description` (string): Brief description of plugin functionality
- `author` (object): Plugin author information
  - `name` (string): Author's name
  - `email` (string): Contact email

## Example

```json
{
  "name": "example-plugin",
  "version": "1.0.0",
  "description": "An example plugin demonstrating the schema",
  "author": {
    "name": "Plugin Author",
    "email": "author@example.com"
  }
}
```

For more examples, see the [official Claude Code plugins](https://github.com/anthropics/claude-code/tree/main/plugins).

## Plugin Components

### Skills

The optional `skills/` directory contains model-invoked skills as
`skills/<name>/SKILL.md`. Use skills for reusable instructions and workflows.

### MCP Servers

The optional `.mcp.json` file declares MCP servers bundled with the plugin.
Remote servers must declare an explicit transport type and keep credentials in
environment-variable expansion rather than committed values.

### Hooks

The `hooks/` directory contains event-based hooks that run at specific points during Claude Code execution. Hooks are defined in a `hooks.json` file and can be triggered by events such as:
- **PreToolUse** - Before a tool is executed
- **PostToolUse** - After a tool completes
- **SessionEnd** - When a session ends
- **Stop** - When Claude stops execution
- And more

For detailed information, see the [official hooks documentation](https://docs.claude.com/en/docs/claude-code/hooks).

### Agents

The `agents/` directory contains agent definitions. Agents are specialized AI assistants that can be invoked to perform specific tasks.

### Commands

The `commands/` directory contains custom commands that users can invoke to perform plugin-specific operations.

## Naming Convention

Plugin directories should be named using the plugin's unique identifier:
- Format: `{name}/`
- Example: `example-calculator/` for a plugin named "example-calculator"
- The `plugin.json` file inside `.claude-plugin/` should contain the same name

## Validation

Before submitting, ensure your plugin:
1. Has a valid `.claude-plugin/` directory with a `plugin.json` file containing proper JSON syntax
2. Contains all required fields in the metadata
3. Uses semantic versioning
4. Has a unique name (not already in use)
5. Includes clear, accurate descriptions
6. Has the proper directory structure with hooks/, agents/, and commands/ folders
7. Is registered in `.claude-plugin/marketplace.json`

## Submission Process

1. Create a new directory in this folder with your plugin name
2. Add the `.claude-plugin/` directory with a `plugin.json` metadata file
3. Create the hooks/, agents/, and commands/ subdirectories
4. Follow the schema and naming conventions
5. Register the plugin in `.claude-plugin/marketplace.json`
6. Test your plugin structure
7. Submit via pull request to the main repository
8. Wait for review and approval

## Questions?

For help with plugin definitions, see the main README or open an issue in the repository.
