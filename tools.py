# tools.py
from clingo import Control
import json
from langchain.tools import tool 
from typing import Annotated
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from nltk.stem import WordNetLemmatizer
import nltk
from typing import Dict, Union, Literal, List
import re
from clingo import Control, MessageCode
from langchain.output_parsers import PydanticOutputParser
from config_loader import load_config, get_all_config_values
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

class ASPInput(BaseModel):
    """Input for generating ASP representation."""
    asp_representation: List[str] = Field(description="List of facts and rules in ASP representation")

def validate_asp_syntax(asp_representation: str) -> bool:
    # Split the representation into individual statements
    statements = asp_representation.split('.')
    
    # Define regex patterns for different ASP constructs
    fact_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\([^()]*\)$'
    rule_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\([^()]*\)\s*:-\s*[a-zA-Z_][a-zA-Z0-9_]*\([^()]*\)(\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*\([^()]*\))*$'
    constraint_pattern = r'^:-\s*[a-zA-Z_][a-zA-Z0-9_]*\([^()]*\)(\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*\([^()]*\))*$'
    
    for statement in statements:
        statement = statement.strip()
        if statement:  # Skip empty statements
            if not (re.match(fact_pattern, statement) or 
                    re.match(rule_pattern, statement) or 
                    re.match(constraint_pattern, statement)):
                print(f"Invalid ASP statement: {statement}")
                return False
    
    return True

def generate_asp_representation(query: str, max_attempts: int = 3) -> str:
    if not query:
        return ""
        
    asp_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an ASP (Answer Set Programming) translator.
        Return ONLY ASP statements, one per line.
        Each statement must end with a period.
        Do not include any explanations or JSON formatting.
        Example output:
        at(agent, district_1).
        has_resource(agent, 10).
        needs(district_2, food)."""),
        ("human", "Convert to ASP statements: {query}")
    ])

    config = get_all_config_values(load_config())
    llm = ChatOpenAI(
        model=config["OPENAI_MODEL"],
        base_url=config["API_BASE_URL"],
        openai_api_key=config["OPENAI_API_KEY"],
    )

    for attempt in range(max_attempts):
        try:
            response = llm.invoke(asp_prompt.format(query=query))
            asp_statements = parse_llm_response(response)
            
            if not asp_statements:
                continue
                
            asp_string = ' '.join(asp_statements)
            
            if validate_asp_syntax(asp_string):
                return asp_string
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            continue
            
    return ""

def parse_llm_response(response) -> List[str]:
    # Handle different response formats
    if isinstance(response, (AIMessage, HumanMessage, SystemMessage)):
        text = response.content
    else:
        text = str(response)
        
    # Split into statements and clean
    statements = []
    for line in text.split('\n'):
        line = line.strip()
        if line and not line.startswith(('#', '//', '-')):
            # Remove any leading numbers or bullets
            line = re.sub(r'^\d+\.\s*', '', line)
            line = re.sub(r'^[-*•]\s*', '', line)
            # Ensure statement ends with period
            if not line.endswith('.'):
                line += '.'
            statements.append(line)
            
    return statements

asp_translation_prompt = """
Translate the agent's internal understanding of the game state into simplified ASP predicates. Focus on resource levels, district health, movement, and future plans. Only include the essential elements needed for checking consistency with the agent’s previous statements.

- Use predicates for key facts (e.g., resource levels, district health) and actions (e.g., movement, supplying).
- Avoid unnecessary details—prioritize clarity and correctness.
- Use simple ASP rules and maintain logical consistency across the agent’s reasoning.
- Example:
    - Input: "The agent is in district 2 and has no resources. He plans to move to district 1."
    - ASP: "location(agent, district_2).", "no_resources(agent).", "move(agent, district_1)."

Translate efficiently, focusing on key information needed for logical consistency.
"""


# asp_translation_prompt = """Translate the given sentences into ASP (Answer Set Programming) predicates following these strict rules:
# - Use lowercase for all predicate names and constants.
# - Use underscores (_) to separate words in multi-word predicates or constants.
# - Predicates must not contain spaces. Use underscores instead.
# - Each predicate must end with parentheses (), even if empty.
# - Arguments within predicates must be comma-separated.
# - Use 'not' for negation.
# - Use ':-' for rules and constraints.
# - Each statement must end with a period (.).
# - Avoid using more than 3 words in a single predicate name.

# Examples:
# - Input: Analyst specializes in breaking down complex problems.
#   ASP: specializes(analyst). breaks_down(analyst, complex_problems).
# - Input: Collaboration is essential for successful product development.
#   ASP: essential(collaboration). leads_to(collaboration, successful_product_development).
# - Input: Understanding market trends is crucial for product success.
#   ASP: crucial_for_success(understanding_market_trends).
  
#   Translate and validate ASP based on these rules."""

import clingo
from typing import List, Tuple, Set

class LogicalConsistencyChecker:
    def __init__(self):
        self.ctl = clingo.Control()

    def check_logical_consistency(self, asp_program: str) -> Tuple[bool, str]:
        """
        Check the logical consistency of ASP statements.
        """
        # Preprocess the ASP program
        preprocessed_program = self.preprocess_asp(asp_program)
        
        # Reset the control object and add the new program
        self.ctl = clingo.Control()
        
        try:
            self.ctl.add("base", [], preprocessed_program)
            self.ctl.ground([("base", [])])
        except RuntimeError as e:
            return False, f"Error in ASP program: {str(e)}"
        
        # Solve and analyze results
        try:
            with self.ctl.solve(yield_=True) as handle:
                models = []
                for model in handle:
                    models.append(model)
                
            if models:
                return True, "The beliefs are logically consistent."
            else:
                explanation = self.generate_inconsistency_explanation(preprocessed_program)
                return False, f"The beliefs are logically inconsistent. {explanation}"
        except RuntimeError as e:
            return False, f"Error during solving: {str(e)}"

    def preprocess_asp(self, asp_program: str) -> str:
        """
        Preprocess the ASP program to ensure correct formatting.
        """
        # Remove any leading/trailing whitespace
        lines = [line.strip() for line in asp_program.split('\n') if line.strip()]
        
        # Ensure each line ends with a period
        lines = [line if line.endswith('.') else f"{line}." for line in lines]
        
        # Remove any duplicate periods
        lines = [re.sub(r'\.+', '.', line) for line in lines]
        
        # Ensure proper spacing around ':-'
        lines = [re.sub(r'\s*:-\s*', ' :- ', line) for line in lines]
        
        return '\n'.join(lines)

    def generate_inconsistency_explanation(self, asp_program: str) -> str:
        """
        Generate an explanation for why the program is inconsistent.
        """
        try:
            # Find minimal unsatisfiable core
            assumptions = [(atom.symbol, True) for atom in self.ctl.symbolic_atoms]
            unsatisfiable_core = self.find_minimal_unsatisfiable_core(assumptions)

            if not unsatisfiable_core:
                return "Unable to determine the specific cause of inconsistency."

            # Map core back to original statements and rules
            core_statements = self.map_core_to_statements(unsatisfiable_core, asp_program)

            # Generate human-readable explanation
            explanation = "The following statements and rules are contradictory:\n"
            for stmt in core_statements:
                explanation += f"- {stmt}\n"

            # Attempt to provide more context
            explanation += self.provide_additional_context(core_statements, asp_program)

            return explanation
        except Exception as e:
            return f"Error during explanation generation: {str(e)}"

    def find_minimal_unsatisfiable_core(self, assumptions: List[Tuple[clingo.Symbol, bool]]) -> Set[clingo.Symbol]:
        """
        Find a minimal unsatisfiable core using a binary search approach.
        """
        unsatisfiable_core = set()
        
        def on_core(core):
            nonlocal unsatisfiable_core
            unsatisfiable_core = set(core)

        try:
            self.ctl.solve(assumptions=assumptions, on_core=on_core)
        except RuntimeError:
            return set()
        
        if not unsatisfiable_core:
            return set()

        # Binary search for minimal unsatisfiable core
        left, right = 0, len(unsatisfiable_core) - 1
        while left <= right:
            mid = (left + right) // 2
            subset = list(unsatisfiable_core)[:mid + 1]
            try:
                if self.ctl.solve(assumptions=[(atom, True) for atom in subset]).unsatisfiable:
                    right = mid - 1
                    unsatisfiable_core = set(subset)
                else:
                    left = mid + 1
            except RuntimeError:
                right = mid - 1

        return unsatisfiable_core

    def map_core_to_statements(self, core: Set[clingo.Symbol], asp_program: str) -> List[str]:
        """
        Map the unsatisfiable core back to the original ASP statements and rules.
        """
        core_statements = []
        for line in asp_program.split('\n'):
            line = line.strip()
            if any(str(atom) in line for atom in core):
                core_statements.append(line)
        return core_statements

    def provide_additional_context(self, core_statements: List[str], asp_program: str) -> str:
        """
        Attempt to provide additional context for the inconsistency.
        """
        context = "\nAdditional context:\n"

        # Check for direct contradictions
        facts = [stmt for stmt in core_statements if stmt.endswith('.') and not stmt.startswith(':-')]
        for fact in facts:
            negation = f":-{fact[:-1]}"  # Convert fact to constraint
            if negation in asp_program:
                context += f"- Direct contradiction found: {fact} conflicts with a constraint in the program.\n"

        # Check for conflicting rules
        rules = [stmt for stmt in core_statements if stmt.startswith(':-') or ':' in stmt]
        if len(rules) > 1:
            context += "- Multiple conflicting rules found. These rules together lead to an inconsistency.\n"

        # Check for unsafe variables
        unsafe_vars = self.detect_unsafe_variables(core_statements)
        if unsafe_vars:
            context += f"- Unsafe variables detected: {', '.join(unsafe_vars)}. These may contribute to the inconsistency.\n"

        # Check for cycles
        if self.detect_cycles(core_statements):
            context += "- Cyclic dependencies detected in the rules, which may contribute to the inconsistency.\n"

        return context if context != "\nAdditional context:\n" else ""

    def detect_unsafe_variables(self, statements: List[str]) -> Set[str]:
        """
        Detect potentially unsafe variables in ASP rules.
        """
        unsafe_vars = set()
        for stmt in statements:
            if ':-' in stmt:
                head, body = stmt.split(':-')
                head_vars = set(var for var in head.split() if var.isupper())
                body_vars = set(var for var in body.split() if var.isupper())
                unsafe_vars.update(head_vars - body_vars)
        return unsafe_vars

    def detect_cycles(self, statements: List[str]) -> bool:
        """
        Simple cycle detection in ASP rules.
        """
        deps = {}
        for stmt in statements:
            if ':-' in stmt:
                head, body = stmt.split(':-')
                head = head.strip()
                body_atoms = [atom.strip() for atom in body.split(',')]
                for atom in body_atoms:
                    if atom not in deps:
                        deps[atom] = set()
                    deps[atom].add(head)

        def has_cycle(node, visited, stack):
            visited.add(node)
            stack.add(node)
            for neighbor in deps.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, stack):
                        return True
                elif neighbor in stack:
                    return True
            stack.remove(node)
            return False

        visited = set()
        for node in deps:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    return True
        return False