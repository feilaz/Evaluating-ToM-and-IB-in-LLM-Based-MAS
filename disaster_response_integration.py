from game import Game, District, Agent, AgentType, ActionType, ResourceType, create_game
from typing import List, Dict, Any, Tuple

class DisasterResponseIntegration:
    def __init__(self, max_turns: int, consumption_rate: int = 10, replenish_amount: int = 100, max_carry: int = 100):
        self.game = create_game(max_turns, consumption_rate, replenish_amount, max_carry)
        self.invalid_command_count = 0
        self.invalid_translations = 0
        self.invalid_logic = 0

    def get_game_state(self) -> str:
        state = f"Turn {self.game.current_turn}:\n"
        for district in self.game.districts.values():
            if district.name != self.game.supply_node:
                state += f"{district}\n"
        for agent in self.game.agents:
            state += f"{agent.agent_type.name} is in District {agent.current_district.name}, carrying {agent.carrying_resource} resources\n"
        return state

    def parse_command(self, command: str) -> Tuple[ActionType, Dict[str, Any]]:
        command = command.strip().lstrip('-').strip()

        if command.upper() == "NONE":
            return None, {}  # Return None for ActionType when command is "NONE"

        # Split the command at the first closing parenthesis or space
        if '(' in command:
            valid_command_part = command.split(')', 1)[0] + ')'
        else:
            valid_command_part = command.split(' ', 1)[0]

        if '(' in valid_command_part:
            action_str, params_str = valid_command_part.split('(', 1)
            params_str = params_str.rstrip(')')
        else:
            action_str = valid_command_part
            params_str = ""

        try:
            action_type = ActionType[action_str.upper().strip()]
        except KeyError:
            raise ValueError(f"Invalid action type: {action_str}")

        if action_type == ActionType.MOVE:
            return action_type, {"district": params_str}
        elif action_type == ActionType.SUPPLY_RESOURCE:
            return action_type, {"amount": int(params_str)}

        return action_type, {}

    def execute_command(self, agent_type: AgentType, command: str) -> str:
        if command == "":
            self.invalid_command_count += 1
            return "No command provided, if you wish to skip your turn write NONE"

        agent = next(a for a in self.game.agents if a.agent_type == agent_type)
        action, params = self.parse_command(command)

        if action is None:
            return f"{agent.agent_type.name} skipped their turn"

        if action == ActionType.MOVE:
            if self.validate_move(agent, params['district']):
                district = self.game.districts[params['district']]
                if agent.move(district):
                    return f"{agent.agent_type.name} moved to District {district.name}"
            self.invalid_command_count += 1
            return f"Invalid move, District {params['district']} is not connected to District {agent.current_district.name}, you can move to: {', '.join(agent.current_district.connections)}. If you want to move to district {params['district']} move through other districts"

        elif action == ActionType.SUPPLY_RESOURCE:
            if self.game.supply_node == agent.current_district.name:
                self.invalid_command_count += 1
                return f"Invalid supply, agent cannot supply resources to the supply node"
            elif not self.validate_supply_amount(agent, params['amount']):
                self.invalid_command_count += 1
                return f"Invalid supply, agent does not have enough resources. Carrying: {agent.carrying_resource}, Supplying: {params['amount']}"
            else:
                agent.supply_resource(params['amount'])
                return f"{agent.agent_type.name} supplied {params['amount']} resources to District {agent.current_district.name}"


        self.invalid_command_count += 1
        return "Invalid action"

    def get_invalid_command_count(self) -> int:
        return self.invalid_command_count

    def validate_move(self, agent: Agent, to_district: str) -> bool:
        return to_district in agent.current_district.connections

    def validate_supply_amount(self, agent: Agent, amount: int) -> bool:
        return 0 < amount <= agent.carrying_resource 

    def update_game_state(self) -> None:
        self.game.run_turn()

    def is_game_over(self) -> bool:
        return self.game.is_game_over()

    def get_final_score(self) -> float:
        return self.game.calculate_score()

    def increment_invalid_translation(self):
        self.invalid_translations += 1

    def increment_invalid_logic(self):
        self.invalid_logic += 1

    def get_game_over_message(self) -> str:
        score = self.get_final_score()
        invalid_commands = self.get_invalid_command_count()
        return f"""The city crisis response has ended. 
Final average district health: {score:.2f}
Total invalid commands: {invalid_commands}
Total invalid translations: {self.invalid_translations}
Total logic inconsistencies: {self.invalid_logic}

{self.get_game_state()}"""


    def get_agent_info(self, agent_type: AgentType) -> Dict[str, Any]:
        agent = next((a for a in self.game.agents if a.agent_type == agent_type), None)
        if agent is None:
            raise ValueError(f"No agent found with type {agent_type}")
        
        connections = self.game.get_all_connections()
        connections_str = self.format_connections(connections)
        
        return {
            "current_district": agent.current_district.name,
            "carrying_resource": agent.carrying_resource,
            "district_resources": agent.current_district.resources,
            "district_health": agent.current_district.health,
            "all_connections": connections_str
        }
    
    def format_connections(self, connections: Dict[str, List[str]]) -> str:
        formatted = []
        for district, connected_districts in connections.items():
            connected = " and ".join(connected_districts)
            formatted.append(f"District {district} is connected to District {connected}.")
        return " ".join(formatted)
    
    def get_district_connections(self, district_name: str) -> List[str]:
        district = self.game.districts.get(district_name)
        if district is None:
            raise ValueError(f"No district found with name {district_name}")
        return self.game.get_all_connections()[district_name]

    def get_district_resources(self, district_name: str) -> Dict[ResourceType, int]:
        district = self.game.districts.get(district_name)
        if district is None:
            raise ValueError(f"No district found with name {district_name}")
        return district.resources

    def get_district_connections(self, district_name: str) -> List[str]:
        district = self.game.districts.get(district_name)
        if district is None:
            raise ValueError(f"No district found with name {district_name}")
        return district.connections