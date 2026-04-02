from typing import TypedDict, Optional


class EurekaState(TypedDict):
    run_id: str
    repo_url: str
    repo_name: str
    memory_file: str
    # Explorer output
    repo_structure: Optional[str]
    stack_detected: Optional[dict]
    # Agent outputs
    architecture_overview: Optional[str]
    claude_md: Optional[str]
    hooks: Optional[str]
    skills_file: Optional[str]
    # Status
    current_node: str
    error: Optional[str]
