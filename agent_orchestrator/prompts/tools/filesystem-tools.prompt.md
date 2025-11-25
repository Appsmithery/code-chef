# Filesystem Tools Usage Guide

## When to Use

- Reading/writing files and directories
- Searching for files by pattern
- Creating project structures
- File operations (copy, move, delete)

## Available Tools (filesystem MCP server)

### `read_file`

```json
{
  "path": "src/main.py",
  "encoding": "utf-8"
}
```

**Use when**: Need to read file contents for analysis or modification.

### `write_file`

```json
{
  "path": "src/new_feature.py",
  "content": "def new_function():\n    pass",
  "create_dirs": true
}
```

**Use when**: Creating new files or overwriting existing ones.

### `list_directory`

```json
{
  "path": "src/",
  "recursive": false,
  "pattern": "*.py"
}
```

**Use when**: Discovering project structure or finding specific file types.

### `search_files`

```json
{
  "path": "src/",
  "pattern": "TODO|FIXME",
  "regex": true
}
```

**Use when**: Finding specific code patterns or comments across files.

### `create_directory`

```json
{
  "path": "src/new_module",
  "recursive": true
}
```

**Use when**: Setting up new package structure.

## Common Patterns

**Pattern 1: Read-Modify-Write**

1. `read_file` → get current content
2. Modify content in memory
3. `write_file` → save changes

**Pattern 2: Project Scaffolding**

1. `create_directory` → create package structure
2. `write_file` → create **init**.py files
3. `write_file` → create module files

**Pattern 3: Code Search**

1. `list_directory` → find Python files
2. `search_files` → grep for specific patterns
3. `read_file` → examine matching files

## Safety Rules

- Always use absolute paths or project-relative paths
- Check if file exists before overwriting (unless intentional)
- Use `create_dirs: true` when creating nested structures
- Backup important files before large refactors
