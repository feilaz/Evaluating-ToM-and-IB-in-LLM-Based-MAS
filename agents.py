from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from typing import Sequence, TypedDict, Annotated, List, Dict
from tools import generate_asp_representation
from agent_knowledgebase import AgentKnowledgeBase
from tools import LogicalConsistencyChecker
from disaster_response_integration import DisasterResponseIntegration
from game import AgentType
from prompts import get_update_prompt

from config_loader import load_config, get_all_config_values

config = load_config()
config_values = get_all_config_values(config)
USE_BELIEFS_ON_OTHERS_SECTION = config_values["USE_BELIEFS_ON_OTHERS_SECTION"]
USE_MY_BELIEF_SECTION = config_values["USE_MY_BELIEF_SECTION"]


def create_agent(llm: ChatOpenAI, system_prompt: str):
    messages = [
        (
            "system",
            system_prompt,
        ),
    ]
    
    if USE_BELIEFS_ON_OTHERS_SECTION:
        messages.append(MessagesPlaceholder(variable_name="beliefs_on_others"))
    
    if USE_MY_BELIEF_SECTION:
        messages.append(MessagesPlaceholder(variable_name="my_beliefs"))
    
    messages.extend([
        MessagesPlaceholder(variable_name="response"),
        MessagesPlaceholder(variable_name="actions"),
    ])
    
    prompt = ChatPromptTemplate.from_messages(messages)
    return prompt | llm

def agent_node(state, agent, knowledge_base, name, disaster_response: DisasterResponseIntegration):
    update_prompt = get_update_prompt(disaster_response.get_agent_info(AgentType[name.upper()]), AgentType[name.upper()])

    logically_consistent = False
    action_valid = False
    tries = 0
    max_tries = 3
    logic_explanation = ""
    action_explanation = ""
    action_result = ""
    consistency_explanation = ""  # Initialize consistency_explanation here

    while (not logically_consistent or not action_valid) and tries < max_tries:
        agent_input = {}
        if USE_BELIEFS_ON_OTHERS_SECTION:
            agent_input["beliefs_on_others"] = knowledge_base.get_agent_knowledge(name, "beliefs_on_others")
        
        if USE_MY_BELIEF_SECTION:
            agent_input["my_beliefs"] = knowledge_base.get_agent_knowledge(name, "my_beliefs") + [logic_explanation]
        
        agent_input.update({
            "response": state["response"] + [update_prompt],
            "actions": knowledge_base.get_agent_knowledge(name, "actions") + [action_explanation],
        })

        result = agent.invoke(agent_input)
        output = result.content
        # print("\033[90m" + output + "\033[0m")
        
        beliefs_on_others, my_beliefs, response, action = parse_agent_response(output)
        # print("\033[91m" + "Action: " + action + "\033[0m")

        # Check logical consistency
        if USE_MY_BELIEF_SECTION:
            my_beliefs_asp = generate_asp_representation(my_beliefs, max_attempts=3)
            if my_beliefs_asp == "":
                disaster_response.increment_invalid_translation()
                print("\033[91m" + "Failed to generate valid ASP representation" + "\033[0m")
                logic_explanation = f"\nFailed to generate a valid ASP representation for your beliefs. Please rephrase your beliefs."
                logically_consistent = False
            else:
                checker = LogicalConsistencyChecker()
                logically_consistent, consistency_explanation = checker.check_logical_consistency(my_beliefs_asp)

                if not logically_consistent:
                    disaster_response.increment_invalid_logic()
                    print("\033[91m" + "Not logically consistent: " + consistency_explanation + "\033[0m")
                    logic_explanation = f"\nPrevious beliefs are not logically consistent. Reason: {consistency_explanation}\nPrevious beliefs: {my_beliefs}"
                else:
                    action_result = disaster_response.execute_command(AgentType[name.upper()], action)
                    # print("\033[92m" + action_result + "\033[0m")

                    if "Invalid" in action_result:
                        action_valid = False
                        action_explanation += f"\nPrevious action was invalid. Reason: {action_result}\nPrevious action: {action}"
                    else:
                        action_valid = True
        else:
            action_result = disaster_response.execute_command(AgentType[name.upper()], action)
            # print("\033[92m" + action_result + "\033[0m")

            if "Invalid" in action_result:
                action_valid = False
                action_explanation += f"\nPrevious action was invalid. Reason: {action_result}\nPrevious action: {action}"
            else:
                action_valid = True

        if action_valid:
            if USE_MY_BELIEF_SECTION and logically_consistent:
                break
            elif not USE_MY_BELIEF_SECTION:
                break
        tries += 1

    # Update knowledge base
    if tries < max_tries:
        if USE_MY_BELIEF_SECTION:
            knowledge_base.add_knowledge(name, "my_beliefs", my_beliefs)
        if USE_BELIEFS_ON_OTHERS_SECTION:
            knowledge_base.add_knowledge(name, "beliefs_on_others", beliefs_on_others)
    
        knowledge_base.add_knowledge(name, "actions", action + " -> " + action_result)
    else:
        print(f"\033[91mAgent {name} failed to produce a valid and consistent response after {max_tries} attempts.\033[0m")

    result = {
        "response": AIMessage(content=response),
        "actions": action + " -> " + action_result,
        "turn": state.get("turn", 0) + 1,
    }
    
    if USE_BELIEFS_ON_OTHERS_SECTION:
        result["beliefs_on_others"] = beliefs_on_others
    
    if USE_MY_BELIEF_SECTION:
        result["my_beliefs"] = my_beliefs
    
    return result

import re

def parse_agent_response(text):
    sections = ["response", "action"]
    if USE_BELIEFS_ON_OTHERS_SECTION:
        sections.append("beliefs_on_others")
    if USE_MY_BELIEF_SECTION:
        sections.append("my_beliefs")
    
    pattern = r'(?:^|\n)(?:\d+\.?\s*)?(?:[#*:]*\s*)({})[#*:]*\s*:?\s*(.+?)(?=(?:\n(?:\d+\.?\s*)?[#*:]*\s*(?:{})[#*:]*\s*:?|\Z))'.format(
        '|'.join(sections), '|'.join(sections))
    
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    result = {section: "" for section in sections}
    
    for section, content in matches:
        section = section.lower().strip()
        if section in result:
            result[section] = content.strip()
    
    return result.get("beliefs_on_others", ""), result.get("my_beliefs", ""), result["response"], result["action"]


class AgentState(TypedDict):
    beliefs_on_others: str
    my_beliefs: str
    response: Annotated[Sequence[BaseMessage], add_messages]
    actions: str
    turn: int
    # finish_vote: int