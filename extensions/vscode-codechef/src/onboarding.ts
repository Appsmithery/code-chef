import * as vscode from 'vscode';

/**
 * Shows a first-run onboarding wizard to help users get started with code/chef
 */
export async function showFirstRunWizard(context: vscode.ExtensionContext): Promise<void> {
  const hasSeenWizard = context.globalState.get('hasSeenOnboardingWizard');
  
  if (hasSeenWizard) {
    return;
  }
  
  const choice = await vscode.window.showInformationMessage(
    '🎩 Welcome to code/chef! This extension is currently in private beta testing. ' +
    'To use the cloud orchestrator, you need an API key.',
    'Configure API Key',
    'Learn More',
    'Dismiss'
  );
  
  switch (choice) {
    case 'Configure API Key':
      await vscode.commands.executeCommand('workbench.action.openSettings', 'codechef.apiKey');
      break;
    case 'Learn More':
      vscode.env.openExternal(vscode.Uri.parse('https://github.com/Appsmithery/code-chef#readme'));
      break;
  }
  
  context.globalState.update('hasSeenOnboardingWizard', true);
}

/**
 * Shows guidance when API key is not configured
 */
export async function showApiKeyRequiredMessage(): Promise<void> {
  const choice = await vscode.window.showWarningMessage(
    '🔑 code/chef requires an API key to connect to the orchestrator. ' +
    'The extension is in private beta - contact the maintainer for access.',
    'Configure API Key',
    'Self-Host Guide',
    'Learn More'
  );
  
  switch (choice) {
    case 'Configure API Key':
      await vscode.commands.executeCommand('workbench.action.openSettings', 'codechef.apiKey');
      break;
    case 'Self-Host Guide':
      vscode.env.openExternal(
        vscode.Uri.parse('https://github.com/Appsmithery/code-chef/blob/main/support/docs/getting-started/DEPLOYMENT.md')
      );
      break;
    case 'Learn More':
      vscode.env.openExternal(vscode.Uri.parse('https://github.com/Appsmithery/code-chef#readme'));
      break;
  }
}

/**
 * Shows a message when transitioning to paid plans (for future use)
 */
export async function showPricingTransitionMessage(context: vscode.ExtensionContext): Promise<void> {
  const hasSeenPricingMessage = context.globalState.get('hasSeenPricingMessage');
  
  if (hasSeenPricingMessage) {
    return;
  }
  
  const choice = await vscode.window.showInformationMessage(
    '💰 code/chef will transition to paid plans in 2025. ' +
    'As a beta tester, you\'ll receive special early-adopter pricing. ' +
    'A free tier will always be available for personal projects.',
    'View Pricing Plans',
    'Remind Me Later',
    'Don\'t Show Again'
  );
  
  switch (choice) {
    case 'View Pricing Plans':
      vscode.env.openExternal(vscode.Uri.parse('https://codechef.appsmithery.co/pricing'));
      context.globalState.update('hasSeenPricingMessage', true);
      break;
    case 'Don\'t Show Again':
      context.globalState.update('hasSeenPricingMessage', true);
      break;
    // 'Remind Me Later' - don't update state
  }
}
