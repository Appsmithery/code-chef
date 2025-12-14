#!/usr/bin/env node

/**
 * VS Code Extension Installer CLI
 *
 * Automatically installs the code-chef VS Code extension via npx.
 * Detects VS Code CLI and either installs bundled VSIX or downloads from GitHub releases.
 */

const { exec } = require("child_process");
const { promisify } = require("util");
const https = require("https");
const fs = require("fs");
const path = require("path");
const os = require("os");

const execAsync = promisify(exec);

// Configuration
const GITHUB_REPO = "Appsmithery/code-chef";
const EXTENSION_ID = "appsmithery.vscode-codechef";
const PACKAGE_VERSION = require("./package.json").version;

/**
 * Check if VS Code CLI is available
 */
async function checkVSCodeCLI() {
  try {
    await execAsync("code --version");
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Download file from URL
 */
function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);

    https
      .get(url, (response) => {
        // Handle redirects
        if (response.statusCode === 302 || response.statusCode === 301) {
          file.close();
          fs.unlinkSync(dest);
          return downloadFile(response.headers.location, dest)
            .then(resolve)
            .catch(reject);
        }

        if (response.statusCode !== 200) {
          file.close();
          fs.unlinkSync(dest);
          return reject(
            new Error(`Failed to download: ${response.statusCode}`)
          );
        }

        response.pipe(file);

        file.on("finish", () => {
          file.close();
          resolve(dest);
        });
      })
      .on("error", (err) => {
        file.close();
        fs.unlinkSync(dest);
        reject(err);
      });
  });
}

/**
 * Get VSIX path (bundled or download from GitHub)
 */
async function getVSIXPath() {
  // Check if VSIX is bundled with npm package
  const bundledVSIX = path.join(
    __dirname,
    `vscode-codechef-${PACKAGE_VERSION}.vsix`
  );

  if (fs.existsSync(bundledVSIX)) {
    console.log("📦 Using bundled VSIX...");
    return bundledVSIX;
  }

  // Download from GitHub releases
  console.log("⬇️  Downloading VSIX from GitHub releases...");
  const downloadURL = `https://github.com/${GITHUB_REPO}/releases/download/v${PACKAGE_VERSION}/vscode-codechef-${PACKAGE_VERSION}.vsix`;
  const tempDir = os.tmpdir();
  const dest = path.join(tempDir, `vscode-codechef-${PACKAGE_VERSION}.vsix`);

  try {
    await downloadFile(downloadURL, dest);
    console.log(`✅ Downloaded to ${dest}`);
    return dest;
  } catch (error) {
    throw new Error(
      `Failed to download VSIX: ${error.message}\nTried URL: ${downloadURL}`
    );
  }
}

/**
 * Install VS Code extension from VSIX
 */
async function installExtension(vsixPath) {
  console.log("📥 Installing VS Code extension...");

  try {
    const { stdout, stderr } = await execAsync(
      `code --install-extension "${vsixPath}"`
    );

    if (stderr && !stderr.includes("successfully installed")) {
      console.warn("⚠️  Warning:", stderr);
    }

    if (stdout) {
      console.log(stdout);
    }

    console.log("✅ Extension installed successfully!");
    console.log(
      "\n🎉 code/chef is now installed! Reload VS Code to activate it."
    );
    console.log("\nNext steps:");
    console.log("1. Press Ctrl+Shift+P (or Cmd+Shift+P on Mac)");
    console.log('2. Type "code/chef: Configure"');
    console.log("3. Enter your API key");

    return true;
  } catch (error) {
    throw new Error(`Failed to install extension: ${error.message}`);
  }
}

/**
 * Main installation flow
 */
async function main() {
  console.log("\n🍳 code/chef VS Code Extension Installer\n");

  // Skip installation in CI or if SKIP_INSTALL is set
  if (process.env.CI || process.env.SKIP_INSTALL) {
    console.log(
      "⏭️  Skipping installation (CI environment or SKIP_INSTALL set)"
    );
    process.exit(0);
  }

  // Check VS Code CLI
  const hasVSCode = await checkVSCodeCLI();

  if (!hasVSCode) {
    console.error("❌ VS Code CLI not found!");
    console.error('\nThe "code" command is not available in your PATH.');
    console.error("\nTo fix this:");
    console.error("1. Open VS Code");
    console.error("2. Press Ctrl+Shift+P (or Cmd+Shift+P on Mac)");
    console.error("3. Type \"Shell Command: Install 'code' command in PATH\"");
    console.error(
      "4. Run this installer again: npx @appsmithery/vscode-codechef"
    );
    console.error("\nAlternatively, install manually from:");
    console.error(`https://github.com/${GITHUB_REPO}/releases`);
    process.exit(1);
  }

  try {
    // Get VSIX file
    const vsixPath = await getVSIXPath();

    // Install extension
    await installExtension(vsixPath);

    // Cleanup temp file if downloaded
    if (vsixPath.includes(os.tmpdir())) {
      fs.unlinkSync(vsixPath);
    }

    process.exit(0);
  } catch (error) {
    console.error("\n❌ Installation failed:", error.message);
    console.error("\nPlease try manual installation:");
    console.error(
      `1. Download VSIX from: https://github.com/${GITHUB_REPO}/releases`
    );
    console.error(
      '2. In VS Code: Ctrl+Shift+P → "Extensions: Install from VSIX..."'
    );
    console.error("3. Select the downloaded .vsix file");
    process.exit(1);
  }
}

// Run installer if executed directly (not during npm install in development)
if (
  require.main === module ||
  process.env.npm_lifecycle_event === "postinstall"
) {
  main();
}

module.exports = { main };
