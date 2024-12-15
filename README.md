# Multi-Agent System with LLM and Logic-Based Reasoning

## Project Overview

This research project introduces an innovative Multi-Agent System (MAS) framework that integrates Large Language Models (LLMs) with advanced reasoning techniques, focusing on enhancing collaboration, decision-making, and logical consistency.

## Key Features

- **Hybrid LLM-Logic Reasoning Approach**
- **Theory of Mind (ToM) Integration**
- **Logical Consistency Verification**
- **Adaptive Agent Collaboration**

## Project Structure

```
project_root/
│
├── main.py                     # Entry point for the multi-agent system
├── agents.py                   # Agent definitions and implementations
├── agent_knowledgebase.py      # Knowledge management for agents
├── config_loader.py            # System configuration management
├── config.ini                  # Configuration settings
├── disaster_response_integration.py  # Crisis management scenario module
├── game.py                     # Simulation environment
├── prompts.py                  # Prompt engineering and management
└── tools.py                    # Logic verification and reasoning tools
```

## Requirements

- Python 3.8+
- Clingo Answer Set Programming (ASP) solver
- OpenAI API or OperRouter access (recommended)

## Installation

1. Clone the repository
   ```
   git clone https://github.com/your-repo/multi-agent-system.git
   cd multi-agent-system
   ```

2. Install dependencies
   ```
   pip install -r requirements.txt
   ```

3. Configure your system
   - Copy `config.ini.example` to `config.ini`
   - Add your API keys and configuration details


## Research Highlights

### Architectural Components

- **Internal Belief Mechanism**
  - Separate belief spaces: "Beliefs on Others", "My Beliefs", "Response"
  - Selective information sharing
  - Logical consistency verification

- **Logic Verification Pipeline**
  - Translates agent beliefs to Answer Set Programming (ASP)
  - Iterative inconsistency checking
  - Aims to detect and prevent hallucinations
