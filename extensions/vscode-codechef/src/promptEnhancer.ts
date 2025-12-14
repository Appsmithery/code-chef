import * as vscode from 'vscode';

/**
 * Enhancement templates based on vscode-prompt-tsx patterns:
 * - System message with high priority
 * - User message with task context
 * - Structured output format
 */
export class PromptEnhancer {
    private readonly enhancementTemplates = {
        detailed: {
            system: `You are a requirements analyst helping to clarify development tasks.

Given a user's brief request, expand it into a comprehensive specification.

Provide:
- **Objective**: Clear statement of what needs to be done
- **Affected Components**: Specific files/modules/services to modify
- **Acceptance Criteria**: Measurable success conditions (Given/When/Then format)
- **Technical Constraints**: Language, framework, architecture, performance requirements
- **Edge Cases**: Error handling, validation, boundary conditions
- **Testing Requirements**: Unit tests, integration tests, manual verification steps

Format your response as structured sections. Be specific about file paths and component names.`,
            maxTokens: 800
        },

        structured: {
            system: `You are a technical clarifier helping to structure development tasks.

Given a user's request, expand it into a clear, actionable specification.

Provide:
- **Goal**: What needs to be accomplished
- **Scope**: Which files/components are affected
- **Criteria**: How to verify success
- **Constraints**: Technical requirements or limitations

Be concise but specific. Include file paths if implied by context.`,
            maxTokens: 500
        },

        minimal: {
            system: `Given a development task, add any missing critical details while preserving the user's intent and style.

Focus only on:
- Which files/components are involved
- Expected behavior or outcome
- Any technical constraints

Keep it brief.`,
            maxTokens: 300
        }
    };

    async enhance(
        originalPrompt: string,
        model: vscode.LanguageModelChat,
        template: 'detailed' | 'structured' | 'minimal',
        token: vscode.CancellationToken
    ): Promise<{ enhanced: string; error?: string }> {
        const config = this.enhancementTemplates[template];

        try {
            // Build messages (vscode-prompt-tsx pattern: System + User)
            const messages = [
                vscode.LanguageModelChatMessage.User(config.system),
                vscode.LanguageModelChatMessage.User(
                    `Original request:\n"${originalPrompt}"\n\nExpanded specification:`
                )
            ];

            // Send request with token limits (vscode-prompt-tsx: PromptSizing concept)
            const request = await model.sendRequest(
                messages,
                {
                    justification: 'Enhancing task description for code-chef orchestrator'
                },
                token
            );

            let enhanced = '';
            let tokenCount = 0;
            const maxTokens = config.maxTokens;

            // Stream response (vscode-prompt-tsx: token-by-token)
            for await (const chunk of request.text) {
                // Rough token estimation (4 chars ≈ 1 token)
                tokenCount += Math.ceil(chunk.length / 4);

                if (tokenCount > maxTokens) {
                    // Budget exceeded, truncate gracefully
                    break;
                }

                enhanced += chunk;
            }

            // Validate enhancement quality
            if (enhanced.length < 50) {
                return {
                    enhanced: originalPrompt,
                    error: 'Enhancement too short, using original'
                };
            }

            return { enhanced: enhanced.trim() };

        } catch (error: any) {
            console.error('Prompt enhancement failed:', error);

            // Graceful degradation (vscode-prompt-tsx pattern)
            return {
                enhanced: originalPrompt,
                error: error.message
            };
        }
    }
}