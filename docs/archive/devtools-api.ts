// Dev-Tools API Client for Frontend Integration
// Copy this to your frontend project: src/services/devtools-api.ts

const DEVTOOLS_BASE_URL = 'http://45.55.173.72:8001';

export interface Task {
  task_id: string;
  assigned_agents: string[];
  status: string;
}

export interface ExecutionResult {
  agent: string;
  status: string;
  result?: any;
}

export interface TaskExecution {
  task_id: string;
  status: string;
  execution_results: ExecutionResult[];
}

export class DevToolsAPI {
  private baseURL: string;

  constructor(baseURL: string = DEVTOOLS_BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Create a new development task
   * @param description - Natural language description of what to build
   * @param priority - Task priority: 'low' | 'medium' | 'high'
   */
  async createTask(
    description: string,
    priority: 'low' | 'medium' | 'high' = 'medium'
  ): Promise<Task> {
    const response = await fetch(`${this.baseURL}/orchestrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description, priority })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create task: ${response.statusText}`);
    }
    
    return response.json();
  }

  /**
   * Execute a task workflow (runs through all assigned agents)
   * @param taskId - The task ID returned from createTask()
   */
  async executeTask(taskId: string): Promise<TaskExecution> {
    const response = await fetch(`${this.baseURL}/execute/${taskId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to execute task: ${response.statusText}`);
    }
    
    return response.json();
  }

  /**
   * Get task status and results
   * @param taskId - The task ID to query
   */
  async getTaskStatus(taskId: string): Promise<any> {
    const response = await fetch(`${this.baseURL}/tasks/${taskId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get task status: ${response.statusText}`);
    }
    
    return response.json();
  }

  /**
   * Health check - verify the service is running
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      const data = await response.json();
      return data.status === 'ok';
    } catch {
      return false;
    }
  }

  /**
   * Direct agent call (bypass orchestrator)
   * Use this for specific agent functionality
   */
  async callAgent(
    agentType: 'feature-dev' | 'code-review' | 'infrastructure' | 'cicd' | 'documentation',
    endpoint: string,
    data: any
  ): Promise<any> {
    const portMap = {
      'feature-dev': 8002,
      'code-review': 8003,
      'infrastructure': 8004,
      'cicd': 8005,
      'documentation': 8006
    };
    
    const port = portMap[agentType];
    const response = await fetch(`http://45.55.173.72:${port}/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`Agent call failed: ${response.statusText}`);
    }
    
    return response.json();
  }
}

// Export singleton instance
export const devToolsAPI = new DevToolsAPI();

// Example usage:
/*
import { devToolsAPI } from './services/devtools-api';

// Create and execute a task
const task = await devToolsAPI.createTask('Build a user login page', 'high');
console.log('Task created:', task.task_id);

const result = await devToolsAPI.executeTask(task.task_id);
console.log('Execution complete:', result);

// Direct agent call
const codeReview = await devToolsAPI.callAgent('code-review', 'review', {
  code: 'function hello() { return "world"; }'
});
*/
