import os
import argparse
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END, StateGraph, START
from agent_knowledgebase import AgentKnowledgeBase
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from disaster_response_integration import DisasterResponseIntegration
from langgraph.graph.message import add_messages
from agents import create_agent, agent_node, AgentState
from config_loader import load_config, get_all_config_values
from prompts import get_initial_message_base, FOOD_AGENT_PERSONALITY, MEDICAL_AGENT_PERSONALITY, SECURITY_AGENT_PERSONALITY
import re

class WorkflowManager:
    def __init__(self, config):
        self.config = config
        self.llm = self._setup_llm()
        self.knowledge_base = AgentKnowledgeBase()
        self.agent_names = ["FOOD_AGENT", "MEDICAL_AGENT", "SECURITY_AGENT"]
        self.max_turns = config.get('MAX_TURNS', 7)
        self.workflow = self._setup_workflow()
        self.disaster_integration = DisasterResponseIntegration(max_turns=self.max_turns * len(self.agent_names), consumption_rate=10)
        self.use_my_belief_section = config.get('USE_MY_BELIEF_SECTION', True)
        self.use_beliefs_on_others_section = config.get('USE_BELIEFS_ON_OTHERS_SECTION', True)

    def _setup_llm(self):
        return ChatOpenAI(model=self.config['OPENAI_MODEL'], api_key=self.config['OPENAI_API_KEY'], base_url=self.config['API_BASE_URL'])

    def _setup_workflow(self):
        workflow = StateGraph(AgentState)

        # Create agent nodes
        for name, personality in zip(self.agent_names, [FOOD_AGENT_PERSONALITY, MEDICAL_AGENT_PERSONALITY, SECURITY_AGENT_PERSONALITY]):
            workflow.add_node(name, self._create_agent_node(name, personality))
        workflow.add_node("append_game_state", self._append_game_state())
        # Add conditional edges for each agent
        workflow.add_edge(START, "append_game_state")
        workflow.add_edge("append_game_state", self.agent_names[0])
        workflow.add_edge(self.agent_names[0], self.agent_names[1])
        workflow.add_edge(self.agent_names[1], self.agent_names[2])
        workflow.add_conditional_edges(
            self.agent_names[2],
            self._should_continue,
            {
                True: "append_game_state",
                False: END
            }
        )

        return workflow.compile()

    def _create_agent_node(self, name: str, personality: str):
        def agent_with_knowledge_and_vocabulary(state):
            agent = create_agent(
                self.llm, 
                personality
            )
            result = agent_node(state, agent, self.knowledge_base, name, self.disaster_integration)

            return result

        return agent_with_knowledge_and_vocabulary


    def _should_continue(self, state: AgentState) -> bool:
        if state["turn"] >= self.max_turns * len(self.agent_names):
            return False
        elif self.disaster_integration.is_game_over():
            return False
        return True

    def _append_game_state(self):
            def append_game_state(state: AgentState):
                # current_game_state = self.disaster_integration.get_game_state()
                
                # # Append the game state to the response messages
                # temp = add_messages(state["response"], [SystemMessage(content=f"Current Game State:\n{current_game_state}")])
                # print("\033[92m" + "Current Game State:\n" + str(temp) + "\033[0m")
                # state["response"] = temp

                # game_state = self.disaster_integration.get_game_state()
                # if self.disaster_integration.get_current_events():
                #     game_state += "\n\nEvents in the city" + self.disaster_integration.get_current_events()

                # if self.disaster_integration.game.current_turn > 0:
                #     game_state += f"\n\nCurrent Turn: {self.disaster_integration.game.current_turn}"
                
                if state["turn"] != 0 and state["turn"] % len(self.agent_names) == 0:
                    self.disaster_integration.game.run_turn()
                    print("\033[92m" + "Game turn updated" "\033[0m")
                    print("\033[92m" + self.disaster_integration.get_game_state() + "\033[0m")
                    # Append the game state to the response messages

                # return {"response": SystemMessage(content=self.disaster_integration.get_game_state())}
                return {"response": SystemMessage(content="")}
            return append_game_state

    def run_phase(self, problem: str):
        initial_state = {
            "response": [HumanMessage(content=problem)],
            "turn": 0
            # "finish_vote": 0
        }
        
        # turn_counter = 0
        for s in self.workflow.stream(initial_state, {"recursion_limit": 50}):
            if "__end__" not in s:
                # turn_counter += 1
                # current_agent = self.agent_names[(turn_counter - 1) % len(self.agent_names)]
                # print(f"Turn: {(turn_counter - 1) // len(self.agent_names) + 1}, Agent: {current_agent}")
                print(s)
                print("----")
            else:
                print(self.disaster_integration.get_game_over_message())
        print(self.disaster_integration.get_game_over_message())

def main():
    parser = argparse.ArgumentParser(description="Run multi-agent system for product development phases.")
    # parser.add_argument("problem", help="The problem statement for the phase")
    # args = parser.parse_args()
    
    config = load_config()
    config_values = get_all_config_values(config)

    # Set environment variables
    os.environ["OPENAI_API_KEY"] = config_values['OPENAI_API_KEY']
    if config_values['LANGCHAIN_TRACING_V2']:
        os.environ["LANGCHAIN_API_KEY"] = config_values['LANGCHAIN_API_KEY']
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = config_values['LANGCHAIN_PROJECT']
    else:
        # Remove LangChain environment variables if tracing is disabled
        for var in ["LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"]:
            os.environ.pop(var, None)

    workflow_manager = WorkflowManager(config_values)
    # workflow_manager.run_phase(args.problem)
    workflow_manager.run_phase("")

if __name__ == "__main__":
    main()