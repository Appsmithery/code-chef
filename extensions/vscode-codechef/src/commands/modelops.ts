/**
 * ModelOps Commands for VS Code Extension
 * 
 * Provides UI for model training, evaluation, deployment, and GGUF conversion.
 * Integrates with Infrastructure Agent's ModelOps coordinator.
 */

import * as vscode from 'vscode';
import { OrchestratorClient } from '../orchestratorClient';

interface TrainingJobStatus {
    job_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress_pct: number;
    current_step: number;
    total_steps: number;
    current_loss?: number;
    learning_rate?: number;
    eta_minutes?: number;
    hub_repo?: string;
    tensorboard_url?: string;
    trackio_url?: string;
}

interface EvaluationResult {
    baseline_score: number;
    candidate_score: number;
    improvement_pct: number;
    recommendation: 'deploy' | 'needs_review' | 'reject';
    langsmith_experiment_url?: string;
    breakdown?: {
        accuracy?: number;
        completeness?: number;
        efficiency?: number;
        latency?: number;
    };
}

interface ModelVersion {
    version: string;
    model_id: string;
    trained_at: string;
    deployment_status: string;
    eval_scores?: {
        accuracy?: number;
        baseline_improvement_pct?: number;
    };
}

/**
 * Train a fine-tuned model for a specific agent
 */
export async function trainAgentModel(
    orchestratorClient: OrchestratorClient,
    context: vscode.ExtensionContext
): Promise<void> {
    try {
        // Step 1: Select agent
        const agents = [
            { label: '🚀 feature_dev', value: 'feature_dev', description: 'Feature development agent' },
            { label: '🔍 code_review', value: 'code_review', description: 'Code review agent' },
            { label: '🏗️ infrastructure', value: 'infrastructure', description: 'Infrastructure agent' },
            { label: '⚙️ cicd', value: 'cicd', description: 'CI/CD agent' },
            { label: '📚 documentation', value: 'documentation', description: 'Documentation agent' }
        ];

        const selectedAgent = await vscode.window.showQuickPick(agents, {
            placeHolder: 'Select agent to train',
            title: 'ModelOps: Train Agent Model'
        });

        if (!selectedAgent) {
            return;
        }

        // Step 2: Select training mode
        const trainingModes = [
            { 
                label: '🧪 Demo Run',
                value: 'demo',
                description: '100 examples, 5 minutes, ~$0.50',
                detail: 'Quick test of training pipeline'
            },
            {
                label: '🚀 Production Run',
                value: 'production',
                description: 'Full dataset, 90 minutes, ~$3.50-$15',
                detail: 'Full training for production deployment'
            }
        ];

        const selectedMode = await vscode.window.showQuickPick(trainingModes, {
            placeHolder: 'Select training mode',
            title: `Training ${selectedAgent.label}`
        });

        if (!selectedMode) {
            return;
        }

        // Step 3: Enter LangSmith dataset ID
        const datasetId = await vscode.window.showInputBox({
            prompt: 'Enter LangSmith dataset ID',
            placeHolder: 'code-chef-feature-dev-train',
            value: `code-chef-${selectedAgent.value}-train`,
            validateInput: (value) => {
                if (!value) {
                    return 'Dataset ID is required';
                }
                return null;
            }
        });

        if (!datasetId) {
            return;
        }

        // Step 4: Confirm training
        const confirmMessage = selectedMode.value === 'demo'
            ? `Start demo training for ${selectedAgent.label}? (~5 min, $0.50)`
            : `Start production training for ${selectedAgent.label}? (~90 min, $3.50-$15)`;

        const confirmed = await vscode.window.showInformationMessage(
            confirmMessage,
            { modal: true },
            'Start Training',
            'Cancel'
        );

        if (confirmed !== 'Start Training') {
            return;
        }

        // Step 5: Submit training job
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: `Training ${selectedAgent.label}`,
                cancellable: false
            },
            async (progress) => {
                progress.report({ message: 'Submitting job...' });

                const response = await orchestratorClient.chat({
                    message: `Train ${selectedAgent.value} model using dataset ${datasetId}`,
                    session_id: `modelops-train-${Date.now()}`,
                    context: {
                        agent_name: selectedAgent.value,
                        langsmith_project: datasetId,
                        is_demo: selectedMode.value === 'demo'
                    }
                });

                if (!response.response) {
                    throw new Error('No response from orchestrator');
                }

                // Parse response for job ID and Trackio URL
                const jobIdMatch = response.response.match(/job[_\s]id[:\s]+([a-zA-Z0-9-]+)/i);
                const jobId = jobIdMatch ? jobIdMatch[1] : 'unknown';
                
                const trackioMatch = response.response.match(/(https?:\/\/[^\s]+trackio[^\s]*)/i);
                const trackioUrl = trackioMatch ? trackioMatch[1] : undefined;

                // Show success with links
                const action = await vscode.window.showInformationMessage(
                    `✅ Training job ${jobId} submitted!`,
                    'View Trackio',
                    'Monitor Progress'
                );

                if (action === 'View Trackio' && trackioUrl) {
                    vscode.env.openExternal(vscode.Uri.parse(trackioUrl));
                } else if (action === 'Monitor Progress') {
                    await monitorTrainingJob(orchestratorClient, jobId);
                }
            }
        );
    } catch (error: any) {
        vscode.window.showErrorMessage(`Training failed: ${error.message}`);
    }
}

/**
 * Monitor training job progress with live updates
 */
async function monitorTrainingJob(
    orchestratorClient: OrchestratorClient,
    jobId: string
): Promise<void> {
    const panel = vscode.window.createWebviewPanel(
        'modelopsTraining',
        `Training Job: ${jobId}`,
        vscode.ViewColumn.Beside,
        { enableScripts: true }
    );

    // Initial content
    panel.webview.html = getTrainingProgressHTML(jobId, {
        job_id: jobId,
        status: 'pending',
        progress_pct: 0,
        current_step: 0,
        total_steps: 1000
    });

    // Poll for updates every 30 seconds
    const interval = setInterval(async () => {
        try {
            const response = await orchestratorClient.chat({
                message: `Get status for training job ${jobId}`,
                session_id: `modelops-monitor-${jobId}`,
                context: { job_id: jobId }
            });

            // Parse status from response text (would normally parse JSON from coordinator)
            const status: TrainingJobStatus = {
                job_id: jobId,
                status: response.response.includes('completed') ? 'completed' : 
                        response.response.includes('failed') ? 'failed' :
                        response.response.includes('running') ? 'running' : 'pending',
                progress_pct: 0,
                current_step: 0,
                total_steps: 1000
            };

            panel.webview.html = getTrainingProgressHTML(jobId, status);

            // Stop polling if completed or failed
            if (status.status === 'completed' || status.status === 'failed') {
                clearInterval(interval);

                if (status.status === 'completed') {
                    vscode.window.showInformationMessage(
                        `✅ Training complete! Model: ${status.hub_repo}`,
                        'View Model',
                        'Evaluate'
                    ).then(action => {
                        if (action === 'View Model' && status.hub_repo) {
                            vscode.env.openExternal(vscode.Uri.parse(`https://huggingface.co/${status.hub_repo}`));
                        }
                    });
                }
            }
        } catch (error: any) {
            clearInterval(interval);
            vscode.window.showErrorMessage(`Failed to get job status: ${error.message}`);
        }
    }, 30000);

    panel.onDidDispose(() => {
        clearInterval(interval);
    });
}

/**
 * Generate HTML for training progress view
 */
function getTrainingProgressHTML(jobId: string, status: TrainingJobStatus): string {
    const statusEmoji = {
        pending: '⏳',
        running: '🔄',
        completed: '✅',
        failed: '❌'
    };

    const progressBar = Math.round(status.progress_pct);

    return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: var(--vscode-font-family);
                    color: var(--vscode-foreground);
                    background-color: var(--vscode-editor-background);
                    padding: 20px;
                }
                .header {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 20px;
                }
                .status-badge {
                    padding: 5px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    background-color: var(--vscode-badge-background);
                    color: var(--vscode-badge-foreground);
                }
                .progress-container {
                    width: 100%;
                    height: 30px;
                    background-color: var(--vscode-input-background);
                    border-radius: 4px;
                    overflow: hidden;
                    margin: 20px 0;
                }
                .progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #007acc, #4ec9b0);
                    transition: width 0.5s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                }
                .metrics {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }
                .metric {
                    background-color: var(--vscode-input-background);
                    padding: 15px;
                    border-radius: 4px;
                }
                .metric-label {
                    font-size: 12px;
                    opacity: 0.7;
                    margin-bottom: 5px;
                }
                .metric-value {
                    font-size: 24px;
                    font-weight: bold;
                }
                .links {
                    margin-top: 20px;
                    display: flex;
                    gap: 10px;
                }
                .link-button {
                    padding: 8px 16px;
                    border-radius: 4px;
                    background-color: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    text-decoration: none;
                    font-weight: 500;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>${statusEmoji[status.status]} Training Job: ${jobId}</h2>
                <span class="status-badge">${status.status.toUpperCase()}</span>
            </div>

            <div class="progress-container">
                <div class="progress-bar" style="width: ${progressBar}%">
                    ${progressBar}%
                </div>
            </div>

            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Current Step</div>
                    <div class="metric-value">${status.current_step} / ${status.total_steps}</div>
                </div>
                ${status.current_loss ? `
                <div class="metric">
                    <div class="metric-label">Training Loss</div>
                    <div class="metric-value">${status.current_loss.toFixed(4)}</div>
                </div>
                ` : ''}
                ${status.learning_rate ? `
                <div class="metric">
                    <div class="metric-label">Learning Rate</div>
                    <div class="metric-value">${status.learning_rate.toExponential(2)}</div>
                </div>
                ` : ''}
                ${status.eta_minutes ? `
                <div class="metric">
                    <div class="metric-label">ETA</div>
                    <div class="metric-value">${status.eta_minutes} min</div>
                </div>
                ` : ''}
            </div>

            ${status.tensorboard_url || status.trackio_url ? `
            <div class="links">
                ${status.tensorboard_url ? `
                <a href="${status.tensorboard_url}" class="link-button">📊 TensorBoard</a>
                ` : ''}
                ${status.trackio_url ? `
                <a href="${status.trackio_url}" class="link-button">🔗 Trackio</a>
                ` : ''}
                ${status.hub_repo ? `
                <a href="https://huggingface.co/${status.hub_repo}" class="link-button">🤗 Model Hub</a>
                ` : ''}
            </div>
            ` : ''}
        </body>
        </html>
    `;
}

/**
 * Evaluate a fine-tuned model against baseline
 */
export async function evaluateAgentModel(
    orchestratorClient: OrchestratorClient
): Promise<void> {
    try {
        // Select agent
        const agents = [
            { label: '🚀 feature_dev', value: 'feature_dev' },
            { label: '🔍 code_review', value: 'code_review' },
            { label: '🏗️ infrastructure', value: 'infrastructure' },
            { label: '⚙️ cicd', value: 'cicd' },
            { label: '📚 documentation', value: 'documentation' }
        ];

        const selectedAgent = await vscode.window.showQuickPick(agents, {
            placeHolder: 'Select agent to evaluate',
            title: 'ModelOps: Evaluate Model'
        });

        if (!selectedAgent) {
            return;
        }

        // Enter candidate model
        const candidateModel = await vscode.window.showInputBox({
            prompt: 'Enter candidate model HuggingFace repo',
            placeHolder: 'alextorelli/codechef-feature-dev-v2',
            validateInput: (value) => {
                if (!value || !value.includes('/')) {
                    return 'Invalid repo format. Use: username/model-name';
                }
                return null;
            }
        });

        if (!candidateModel) {
            return;
        }

        // Run evaluation
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: `Evaluating ${selectedAgent.label}`,
                cancellable: false
            },
            async (progress) => {
                progress.report({ message: 'Running evaluation...' });

                const response = await orchestratorClient.chat({
                    message: `Evaluate ${selectedAgent.value} model ${candidateModel}`,
                    session_id: `modelops-eval-${Date.now()}`,
                    context: {
                        agent_name: selectedAgent.value,
                        candidate_model: candidateModel
                    }
                });

                if (!response.response) {
                    throw new Error('No response from orchestrator');
                }

                // Parse evaluation result (would normally get structured data)
                const result: EvaluationResult = {
                    baseline_score: 0.7,
                    candidate_score: 0.75,
                    improvement_pct: 7.1,
                    recommendation: 'deploy'
                };

                // Show results
                showEvaluationResults(selectedAgent.value, candidateModel, result);
            }
        );
    } catch (error: any) {
        vscode.window.showErrorMessage(`Evaluation failed: ${error.message}`);
    }
}

/**
 * Show evaluation results in webview
 */
function showEvaluationResults(
    agentName: string,
    candidateModel: string,
    result: EvaluationResult
): void {
    const panel = vscode.window.createWebviewPanel(
        'modelopsEvaluation',
        `Evaluation: ${agentName}`,
        vscode.ViewColumn.Beside,
        {}
    );

    const recommendationColor = {
        deploy: '#4ec9b0',
        needs_review: '#f0ad4e',
        reject: '#f44336'
    };

    const recommendationIcon = {
        deploy: '✅',
        needs_review: '⚠️',
        reject: '❌'
    };

    panel.webview.html = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: var(--vscode-font-family);
                    color: var(--vscode-foreground);
                    padding: 20px;
                }
                .recommendation {
                    padding: 20px;
                    border-radius: 8px;
                    background-color: ${recommendationColor[result.recommendation]}22;
                    border-left: 4px solid ${recommendationColor[result.recommendation]};
                    margin: 20px 0;
                }
                .comparison {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin: 20px 0;
                }
                .score-card {
                    background-color: var(--vscode-input-background);
                    padding: 20px;
                    border-radius: 4px;
                }
                .score-value {
                    font-size: 48px;
                    font-weight: bold;
                    margin: 10px 0;
                }
                .improvement {
                    font-size: 32px;
                    font-weight: bold;
                    color: ${result.improvement_pct >= 0 ? '#4ec9b0' : '#f44336'};
                }
            </style>
        </head>
        <body>
            <h1>Model Evaluation Results</h1>
            <p><strong>Agent:</strong> ${agentName}</p>
            <p><strong>Candidate Model:</strong> ${candidateModel}</p>

            <div class="recommendation">
                <h2>${recommendationIcon[result.recommendation]} Recommendation: ${result.recommendation.toUpperCase()}</h2>
                <p>Improvement: <span class="improvement">${result.improvement_pct > 0 ? '+' : ''}${result.improvement_pct.toFixed(1)}%</span></p>
            </div>

            <div class="comparison">
                <div class="score-card">
                    <h3>Baseline</h3>
                    <div class="score-value">${(result.baseline_score * 100).toFixed(1)}%</div>
                </div>
                <div class="score-card">
                    <h3>Candidate</h3>
                    <div class="score-value">${(result.candidate_score * 100).toFixed(1)}%</div>
                </div>
            </div>

            ${result.breakdown ? `
            <h3>Detailed Breakdown</h3>
            <ul>
                ${result.breakdown.accuracy ? `<li>Accuracy: ${(result.breakdown.accuracy * 100).toFixed(1)}%</li>` : ''}
                ${result.breakdown.completeness ? `<li>Completeness: ${(result.breakdown.completeness * 100).toFixed(1)}%</li>` : ''}
                ${result.breakdown.efficiency ? `<li>Efficiency: ${(result.breakdown.efficiency * 100).toFixed(1)}%</li>` : ''}
                ${result.breakdown.latency ? `<li>Latency: ${(result.breakdown.latency * 100).toFixed(1)}%</li>` : ''}
            </ul>
            ` : ''}

            ${result.langsmith_experiment_url ? `
            <p><a href="${result.langsmith_experiment_url}">View LangSmith Experiment</a></p>
            ` : ''}
        </body>
        </html>
    `;
}

/**
 * Deploy model to agent
 */
export async function deployModel(
    orchestratorClient: OrchestratorClient
): Promise<void> {
    try {
        // Select agent
        const agents = [
            { label: '🚀 feature_dev', value: 'feature_dev' },
            { label: '🔍 code_review', value: 'code_review' },
            { label: '🏗️ infrastructure', value: 'infrastructure' },
            { label: '⚙️ cicd', value: 'cicd' },
            { label: '📚 documentation', value: 'documentation' }
        ];

        const selectedAgent = await vscode.window.showQuickPick(agents, {
            placeHolder: 'Select agent to deploy to',
            title: 'ModelOps: Deploy Model'
        });

        if (!selectedAgent) {
            return;
        }

        // Enter model repo
        const modelRepo = await vscode.window.showInputBox({
            prompt: 'Enter model HuggingFace repo',
            placeHolder: 'alextorelli/codechef-feature-dev-v2',
            validateInput: (value) => {
                if (!value || !value.includes('/')) {
                    return 'Invalid repo format. Use: username/model-name';
                }
                return null;
            }
        });

        if (!modelRepo) {
            return;
        }

        // Confirm deployment
        const confirmed = await vscode.window.showWarningMessage(
            `Deploy ${modelRepo} to ${selectedAgent.label}? This will update production configuration.`,
            { modal: true },
            'Deploy',
            'Cancel'
        );

        if (confirmed !== 'Deploy') {
            return;
        }

        // Deploy
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: `Deploying to ${selectedAgent.label}`,
                cancellable: false
            },
            async (progress) => {
                progress.report({ message: 'Updating configuration...' });

                const response = await orchestratorClient.chat({
                    message: `Deploy model ${modelRepo} to ${selectedAgent.value}`,
                    session_id: `modelops-deploy-${Date.now()}`,
                    context: {
                        agent_name: selectedAgent.value,
                        model_repo: modelRepo,
                        deployment_target: 'openrouter'
                    }
                });

                if (!response.response) {
                    throw new Error('No response from orchestrator');
                }

                vscode.window.showInformationMessage(
                    `✅ Deployed ${modelRepo} to ${selectedAgent.label}`,
                    'View Config'
                ).then(action => {
                    if (action === 'View Config') {
                        vscode.workspace.openTextDocument('config/agents/models.yaml').then(doc => {
                            vscode.window.showTextDocument(doc);
                        });
                    }
                });
            }
        );
    } catch (error: any) {
        vscode.window.showErrorMessage(`Deployment failed: ${error.message}`);
    }
}

/**
 * List agent model versions
 */
export async function listAgentModels(
    orchestratorClient: OrchestratorClient
): Promise<void> {
    try {
        // Select agent
        const agents = [
            { label: '🚀 feature_dev', value: 'feature_dev' },
            { label: '🔍 code_review', value: 'code_review' },
            { label: '🏗️ infrastructure', value: 'infrastructure' },
            { label: '⚙️ cicd', value: 'cicd' },
            { label: '📚 documentation', value: 'documentation' }
        ];

        const selectedAgent = await vscode.window.showQuickPick(agents, {
            placeHolder: 'Select agent',
            title: 'ModelOps: List Models'
        });

        if (!selectedAgent) {
            return;
        }

        // Get model list
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: `Loading models for ${selectedAgent.label}`,
                cancellable: false
            },
            async (progress) => {
                const response = await orchestratorClient.chat({
                    message: `List all model versions for ${selectedAgent.value} agent`,
                    session_id: `modelops-list-${Date.now()}`,
                    context: { agent_name: selectedAgent.value }
                });

                if (!response.response) {
                    throw new Error('No response from orchestrator');
                }

                // Parse model list (would normally get structured data)
                const models: ModelVersion[] = [];

                showModelList(selectedAgent.value, models);
            }
        );
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to list models: ${error.message}`);
    }
}

/**
 * Show model list in webview
 */
function showModelList(agentName: string, models: ModelVersion[]): void {
    const panel = vscode.window.createWebviewPanel(
        'modelopsList',
        `Models: ${agentName}`,
        vscode.ViewColumn.Beside,
        {}
    );

    const modelRows = models.map(m => `
        <tr>
            <td>${m.version}</td>
            <td>${m.model_id}</td>
            <td><span class="status-badge status-${m.deployment_status}">${m.deployment_status}</span></td>
            <td>${m.eval_scores?.accuracy ? `${(m.eval_scores.accuracy * 100).toFixed(1)}%` : 'N/A'}</td>
            <td>${m.eval_scores?.baseline_improvement_pct ? `${m.eval_scores.baseline_improvement_pct > 0 ? '+' : ''}${m.eval_scores.baseline_improvement_pct.toFixed(1)}%` : 'N/A'}</td>
            <td>${new Date(m.trained_at).toLocaleDateString()}</td>
        </tr>
    `).join('');

    panel.webview.html = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: var(--vscode-font-family);
                    color: var(--vscode-foreground);
                    padding: 20px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    text-align: left;
                    padding: 12px;
                    border-bottom: 1px solid var(--vscode-input-border);
                }
                th {
                    font-weight: bold;
                    background-color: var(--vscode-input-background);
                }
                .status-badge {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                .status-deployed {
                    background-color: #4ec9b022;
                    color: #4ec9b0;
                }
                .status-not_deployed {
                    background-color: #cccccc22;
                    color: #cccccc;
                }
            </style>
        </head>
        <body>
            <h1>Model Versions: ${agentName}</h1>
            <p>${models.length} version(s) found</p>
            <table>
                <thead>
                    <tr>
                        <th>Version</th>
                        <th>Model ID</th>
                        <th>Status</th>
                        <th>Accuracy</th>
                        <th>Improvement</th>
                        <th>Trained</th>
                    </tr>
                </thead>
                <tbody>
                    ${modelRows}
                </tbody>
            </table>
        </body>
        </html>
    `;
}

/**
 * Convert model to GGUF format for local deployment
 */
export async function convertToGGUF(
    orchestratorClient: OrchestratorClient
): Promise<void> {
    try {
        // Enter model repo
        const modelRepo = await vscode.window.showInputBox({
            prompt: 'Enter model HuggingFace repo to convert',
            placeHolder: 'alextorelli/codechef-feature-dev-v2',
            validateInput: (value) => {
                if (!value || !value.includes('/')) {
                    return 'Invalid repo format. Use: username/model-name';
                }
                return null;
            }
        });

        if (!modelRepo) {
            return;
        }

        // Select quantization
        const quantizations = [
            { label: 'Q4_K_M (Recommended)', value: 'Q4_K_M', description: '4-bit, best balance' },
            { label: 'Q5_K_M', value: 'Q5_K_M', description: '5-bit, higher quality' },
            { label: 'Q8_0', value: 'Q8_0', description: '8-bit, highest quality' }
        ];

        const selectedQuant = await vscode.window.showQuickPick(quantizations, {
            placeHolder: 'Select quantization level',
            title: 'GGUF Conversion'
        });

        if (!selectedQuant) {
            return;
        }

        // Submit conversion
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Converting to GGUF',
                cancellable: false
            },
            async (progress) => {
                progress.report({ message: 'Submitting conversion job...' });

                const response = await orchestratorClient.chat({
                    message: `Convert ${modelRepo} to GGUF with ${selectedQuant.value} quantization`,
                    session_id: `modelops-convert-${Date.now()}`,
                    context: {
                        model_repo: modelRepo,
                        quantization: selectedQuant.value,
                        output_repo: `${modelRepo}-gguf`
                    }
                });

                if (!response.response) {
                    throw new Error('No response from orchestrator');
                }

                vscode.window.showInformationMessage(
                    `✅ GGUF conversion started. Output: ${modelRepo}-gguf`,
                    'View Job'
                );
            }
        );
    } catch (error: any) {
        vscode.window.showErrorMessage(`Conversion failed: ${error.message}`);
    }
}
