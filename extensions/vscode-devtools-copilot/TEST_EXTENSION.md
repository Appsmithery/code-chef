# Testing @devtools Extension

## Issue: Command Not Found

The error "command 'devtools.configure' not found" suggests the extension hasn't fully activated.

## Root Cause

VS Code extensions with `chatParticipants` and `activationEvents: ["onStartupFinished"]` may not immediately register all commands until:

1. The extension host fully starts
2. The chat participant is first invoked
3. Or a command is explicitly triggered

## Solution: Test in Copilot Chat First

Instead of using `F1` → "Dev-Tools: Configure", test the extension by:

### Step 1: Open Copilot Chat

Press `Ctrl+I` to open GitHub Copilot Chat

### Step 2: Type @ to see participants

Type `@` in the chat and you should see:

- `@workspace`
- `@vscode`
- `@devtools` ← **Our extension**

### Step 3: Submit a test task

```
@devtools test connection
```

This will:

1. Activate the extension fully
2. Register all commands
3. Establish connection to orchestrator
4. Show status bar indicator

### Step 4: Commands should work after activation

Once the chat participant runs once, all commands become available:

- `F1` → "Dev-Tools: Configure"
- `F1` → "Dev-Tools: Submit Task"
- `F1` → "Dev-Tools: Check Status"
- etc.

## Alternative: Force Activation

If `@devtools` doesn't appear in the participant list, the extension may not be properly installed.

**Full reinstall:**

```powershell
cd D:\INFRA\Dev-Tools\Dev-Tools\extensions\vscode-devtools-copilot

# Uninstall completely
code --uninstall-extension appsmithery.vscode-devtools-copilot

# Wait for uninstall to complete
Start-Sleep -Seconds 3

# Reinstall fresh
code --install-extension .\vscode-devtools-copilot-0.1.0.vsix

# Reload VS Code
# Ctrl+Shift+P → "Developer: Reload Window"
```

## Verification Steps

1. **Check extension installed**:

   ```powershell
   code --list-extensions | Select-String "devtools"
   ```

   Should show: `appsmithery.vscode-devtools-copilot`

2. **Check extension activated**:

   - Look for status bar item (bottom-right)
   - Should show: "✓ Dev-Tools" or "⚠ Dev-Tools"

3. **Check logs**:

   - `F1` → "Developer: Show Logs" → "Extension Host"
   - Look for: "Dev-Tools extension activating..."

4. **Test orchestrator directly**:
   ```powershell
   Invoke-RestMethod -Uri "http://45.55.173.72:8001/health"
   ```
   Should return: `status: ok, service: orchestrator`

## Expected Behavior

Once working, typing `@devtools Add auth to API` in Copilot Chat should:

1. Show participant icon (if we had added one)
2. Display "Analyzing workspace context..." progress
3. Show "Submitting to Dev-Tools orchestrator..." progress
4. Return task breakdown with:
   - Task ID
   - Subtasks list
   - Agent assignments
   - Estimated duration
   - Links to LangSmith traces

## If Still Not Working

The extension may require GitHub Copilot Chat API which is available in:

- VS Code Insiders (latest features)
- VS Code Stable 1.85.0+ (with Copilot subscription)

**Check your VS Code version**:

```powershell
code --version
```

**Check Copilot status**:

- Bottom-right corner should show Copilot icon
- Click icon → "Check Status"
- Should show: "GitHub Copilot is active"

If Copilot Chat isn't available, the `chatParticipants` contribution won't work and you'll need to use the Command Palette commands directly instead.
