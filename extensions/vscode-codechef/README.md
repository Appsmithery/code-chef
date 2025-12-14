# code/chef — Your AI Development Team

[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue?logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> **Talk to your code. Ship faster.**

code/chef is like having an experienced development team right in VS Code. Just chat naturally about what you want to build—new features, code reviews, documentation, deployment setups—and the AI handles the heavy lifting while you focus on the creative work.

---

## ✨ What Can code/chef Do?

### 🚀 Build Features

```
@chef Add user login with email and password reset
```

Get complete, working code for new features—no need to know all the technical details.

### 🔍 Review Your Code

```
@chef Check this code for issues
```

Get instant feedback on security problems, performance issues, or just general improvements.

### 🏗️ Set Up Your Project

```
@chef Set up Docker for my app with a database
```

Get all the configuration files you need without learning Docker syntax.

### ⚡ Automate Deployments

```
@chef Create a workflow to test and deploy my app
```

Automate your testing and deployment without wrestling with YAML files.

### 📚 Generate Documentation

```
@chef Write documentation for my API
```

Get professional docs written for you—README files, API guides, whatever you need.

---

## 🎯 Why code/chef?

| Without code/chef           | With code/chef              |
| --------------------------- | --------------------------- |
| Switch between many tools   | Everything in one chat      |
| Search for solutions        | Just describe what you want |
| Wait hours for code reviews | Get instant feedback        |
| Write docs manually         | Generated automatically     |
| Complex setup processes     | Plain English requests      |
| Solo development struggles  | AI team always available    |

### 🧠 Always Uses the Right AI

code/chef automatically picks the best AI for each task—you don't need to worry about which model to use. Different tasks get different specialists, just like a real team.

---

## 🚀 Get Started in 2 Minutes

### Step 1: Install the Extension

#### **Option 1: npx (Recommended)**

Install with one command (requires [GitHub Personal Access Token](https://github.com/settings/tokens/new?scopes=read:packages) with `read:packages` scope):

```bash
# First time only: Create .npmrc in your home directory
echo "@appsmithery:registry=https://npm.pkg.github.com" >> ~/.npmrc
echo "//npm.pkg.github.com/:_authToken=YOUR_GITHUB_TOKEN" >> ~/.npmrc

# Install extension
npx @appsmithery/vscode-codechef
```

**Windows PowerShell:**

```powershell
# First time only
Add-Content -Path "$env:USERPROFILE\.npmrc" -Value "@appsmithery:registry=https://npm.pkg.github.com"
Add-Content -Path "$env:USERPROFILE\.npmrc" -Value "//npm.pkg.github.com/:_authToken=YOUR_GITHUB_TOKEN"

# Install extension
npx @appsmithery/vscode-codechef
```

> **Why authentication?** We use GitHub Packages for future monetization support. Public availability via Open VSX (Option 2) doesn't require authentication.

#### **Option 2: Open VSX Registry** (No Authentication)

```bash
code --install-extension appsmithery.vscode-codechef
```

Or search "code/chef" in VS Code Extensions (`Ctrl+Shift+X`) if using VSCodium or other Open VSX-compatible editors.

#### **Option 3: GitHub Releases** (Manual)

**Bash/Linux/macOS:**

```bash
curl -L https://github.com/Appsmithery/code-chef/releases/latest/download/vscode-codechef-1.0.0.vsix -o codechef.vsix && code --install-extension codechef.vsix
```

**PowerShell/Windows:**

```powershell
curl -L https://github.com/Appsmithery/code-chef/releases/latest/download/vscode-codechef-1.0.0.vsix -o codechef.vsix; code --install-extension codechef.vsix
```

Or manually:

1. Go to [Releases](https://github.com/Appsmithery/code-chef/releases)
2. Download the latest `vscode-codechef-*.vsix` file
3. In VS Code: `Ctrl+Shift+P` → **Extensions: Install from VSIX...**
4. Select the downloaded file and reload VS Code

#### **Troubleshooting**

**"code command not found"**

1. Open VS Code
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Type "Shell Command: Install 'code' command in PATH"
4. Retry installation

**"Authentication required" (npx)**

- Generate token: https://github.com/settings/tokens/new?scopes=read:packages
- Add to `~/.npmrc` (Linux/macOS) or `%USERPROFILE%\.npmrc` (Windows)
- Or use Option 2 (Open VSX) - no authentication needed

**"VSIX not found in package" (npx)**

The npm package downloads the VSIX from GitHub releases automatically. If this fails:
- Check your internet connection
- Manually download from [Releases](https://github.com/Appsmithery/code-chef/releases) (Option 3)

**"Extension activation failed"**

1. Check VS Code version: Must be >= 1.85.0
2. Update VS Code: Help → Check for Updates
3. Restart VS Code after installation

### Step 2: Set Up Your API Key

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "code/chef: Configure" and press Enter
3. Enter your API key (ask your team admin, or [contact us](https://github.com/Appsmithery/code-chef) to get one)

### Step 3: Start Building

Open GitHub Copilot Chat and type:

```
@chef Build a user login page
```

That's it! Watch as code/chef creates the files, writes the code, and explains what it did.

---

## 💬 Real Conversations

### "I need to add a feature"

```
You: @chef I need users to be able to reset their passwords

Chef: I'll set up password reset for you. This will include:
- Email verification
- Secure reset tokens
- New password form
- All the security best practices

Creating the files now...
```

### "Is my code okay?"

```
You: @chef Can you check my login code?

Chef: I found a few things:
🔴 Important: Passwords aren't being encrypted (line 45)
🟡 Heads up: Login page needs rate limiting to prevent attacks
🟢 Nice to have: Add "remember me" functionality

Want me to fix these?
```

### "I'm stuck on deployment"

```
You: @chef How do I deploy this to production?

Chef: I'll create a deployment setup for you with:
- Automated testing before deploy
- Staging environment
- Easy rollback if something breaks
- Step-by-step deployment guide

Setting this up now...
```

---

## 🔧 Quick Commands

### In Chat

Just talk naturally! Here are some examples:

- `@chef <describe what you want>` — The main way to use code/chef
- `@chef /status` — See what code/chef is working on
- `@chef /tools` — See what integrations are available

### From the Command Menu

Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) and search:

| Command                   | What it does                     |
| ------------------------- | -------------------------------- |
| `code/chef: Submit Task`  | Send a task without using chat   |
| `code/chef: Health Check` | Make sure everything's working   |
| `code/chef: Configure`    | Change your settings             |
| `code/chef: Clear Cache`  | Start fresh if something's stuck |

---

## 🎓 Advanced: Teach code/chef Your Style

Want code/chef to write code exactly how your team likes it? You can train custom models on your codebase. This is completely optional—code/chef works great out of the box.

### How It Works

1. **Train**: Press `Ctrl+Shift+P` → "codechef.modelops.train"

   - Takes about an hour
   - Learns from your existing code
   - Costs a few dollars

2. **Test**: Press `Ctrl+Shift+P` → "codechef.modelops.evaluate"

   - See if the new model is better
   - Get a clear recommendation

3. **Deploy**: Press `Ctrl+Shift+P` → "codechef.modelops.deploy"
   - Switch to your custom model
   - Can always switch back

**Most users don't need this.** The default models are excellent. Custom training is for teams that want code/chef to match their specific coding style perfectly.

---

## ⚙️ Settings

You probably won't need to change these, but here they are:

| Setting                        | What it does                                |
| ------------------------------ | ------------------------------------------- |
| `codechef.apiKey`              | Your API key (required)                     |
| `codechef.orchestratorUrl`     | Server location (leave as default)          |
| `codechef.showWorkflowPreview` | Show what code/chef will do before doing it |
| `codechef.useStreaming`        | Show responses as they're being written     |

Access settings: `Ctrl+Shift+P` → "code/chef: Configure"

---

## 🔌 Works With Your Tools

code/chef integrates with the tools you already use:

- **GitHub** — Creates pull requests, manages issues
- **Linear** — Updates project tasks
- **Docker** — Manages containers
- **Databases** — PostgreSQL, Redis, and more

No extra setup needed—code/chef figures out what you're using and works with it.

---

## ❓ Something Not Working?

### code/chef isn't responding

1. Make sure you typed `@chef` at the start of your message
2. Try: `Ctrl+Shift+P` → "code/chef: Health Check"
3. Still stuck? Try: `Ctrl+Shift+P` → "code/chef: Clear Cache" and reload VS Code

### Connection issues

1. Check your API key: `Ctrl+Shift+P` → "code/chef: Configure"
2. Make sure you're connected to the internet
3. Try the health check: `Ctrl+Shift+P` → "code/chef: Health Check"

### Still having trouble?

Open an issue on [GitHub](https://github.com/Appsmithery/code-chef/issues) and we'll help you out!

---

## 📞 Get Help or Get Started

- **GitHub**: [github.com/Appsmithery/code-chef](https://github.com/Appsmithery/code-chef)
- **Issues**: Found a bug? [Open an issue](https://github.com/Appsmithery/code-chef/issues)
- **Questions**: Need help? Start a [discussion](https://github.com/Appsmithery/code-chef/discussions)

---

## 📄 License

MIT License — Free for personal and commercial use. See [LICENSE](LICENSE) for details.

---

**Made with ❤️ for developers who want to focus on building, not fighting with tools.**
