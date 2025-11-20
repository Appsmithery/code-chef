"""Progressive tool loader using keyword-based filtering"""

from typing import Dict, List, Set


class ProgressiveLoader:
    """
    Progressive tool loader using keyword-based filtering
    Reduces token usage by 80-90% by loading only relevant tools
    """
    
    def __init__(self):
        self.keyword_map: Dict[str, List[str]] = {
            # Memory & State
            'memory': ['memory'],
            'remember': ['memory'],
            'recall': ['memory'],
            'save': ['memory', 'filesystem'],
            'store': ['memory', 'database'],
            
            # Filesystem operations
            'file': ['filesystem', 'context7'],
            'directory': ['filesystem'],
            'read': ['filesystem', 'memory', 'database'],
            'write': ['filesystem', 'memory', 'database'],
            'delete': ['filesystem', 'database'],
            
            # Git & Version Control
            'git': ['git', 'github'],
            'commit': ['git'],
            'branch': ['git'],
            'pull': ['git', 'github'],
            'push': ['git', 'github'],
            'repository': ['git', 'github'],
            
            # GitHub
            'github': ['github'],
            'issue': ['github', 'linear'],
            'pr': ['github'],
            'pull request': ['github'],
            
            # Linear Project Management
            'linear': ['linear'],
            'task': ['linear'],
            'project': ['linear', 'terraform'],
            
            # Notion
            'notion': ['notion'],
            'notes': ['notion', 'memory'],
            'wiki': ['notion'],
            
            # Infrastructure
            'deploy': ['terraform', 'docker', 'kubernetes'],
            'infrastructure': ['terraform', 'docker', 'kubernetes'],
            'terraform': ['terraform'],
            'cloud': ['terraform', 'aws'],
            'server': ['docker', 'kubernetes', 'terraform'],
            
            # Containers
            'docker': ['docker'],
            'container': ['docker', 'kubernetes'],
            'image': ['docker'],
            'kubernetes': ['kubernetes'],
            'k8s': ['kubernetes'],
            'pod': ['kubernetes'],
            
            # Database
            'database': ['database', 'postgres', 'sqlite'],
            'sql': ['database', 'postgres', 'sqlite'],
            'query': ['database', 'postgres', 'sqlite'],
            'postgres': ['postgres'],
            'postgresql': ['postgres'],
            'sqlite': ['sqlite'],
            
            # Search & Web
            'search': ['brave-search', 'exa', 'context7'],
            'web': ['brave-search', 'fetch', 'puppeteer'],
            'browse': ['puppeteer', 'fetch'],
            'scrape': ['puppeteer'],
            
            # Time & Calendar
            'time': ['time'],
            'date': ['time'],
            'calendar': ['time'],
            'schedule': ['time', 'linear'],
            
            # Analytics & Monitoring
            'metrics': ['prometheus'],
            'monitor': ['prometheus'],
            'alert': ['prometheus'],
            
            # Sequential Thinking
            'think': ['sequential-thinking'],
            'reason': ['sequential-thinking'],
            'analyze': ['sequential-thinking', 'context7'],
            
            # Code & Context
            'code': ['context7', 'filesystem', 'github'],
            'codebase': ['context7', 'github'],
            'context': ['context7'],
            
            # Fetch & HTTP
            'fetch': ['fetch'],
            'http': ['fetch'],
            'api': ['fetch'],
            'request': ['fetch'],
            
            # Testing
            'test': ['filesystem', 'github'],
            'mock': ['filesystem']
        }
    
    def filter_by_task(self, task_description: str, all_tools: List) -> List:
        """
        Filter tools based on task description
        
        Args:
            task_description: Natural language task description
            all_tools: Full tool catalog
            
        Returns:
            Filtered tools relevant to task
        """
        lower_task = task_description.lower()
        relevant_servers: Set[str] = set()
        
        # Match keywords to servers
        for keyword, servers in self.keyword_map.items():
            if keyword in lower_task:
                relevant_servers.update(servers)
        
        # If no keywords matched, return high-priority servers
        if not relevant_servers:
            relevant_servers = {'context7', 'memory', 'filesystem', 'sequential-thinking'}
        
        # Filter tools
        return [tool for tool in all_tools if tool.server in relevant_servers]
    
    def get_servers_for_keywords(self, keywords: List[str]) -> Set[str]:
        """
        Get servers for specific keywords
        
        Args:
            keywords: List of keywords
            
        Returns:
            Set of server names
        """
        servers: Set[str] = set()
        
        for keyword in keywords:
            lower_keyword = keyword.lower()
            mapped_servers = self.keyword_map.get(lower_keyword, [])
            servers.update(mapped_servers)
        
        return servers
    
    def add_keyword_mapping(self, keyword: str, servers: List[str]) -> None:
        """
        Add custom keyword mapping
        
        Args:
            keyword: Keyword to map
            servers: List of server names
        """
        self.keyword_map[keyword.lower()] = servers
    
    def get_keyword_mappings(self) -> Dict[str, List[str]]:
        """Get all keyword mappings"""
        return self.keyword_map.copy()
