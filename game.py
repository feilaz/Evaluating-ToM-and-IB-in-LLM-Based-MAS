from enum import Enum, auto
from typing import List, Dict, Tuple
import random

class ResourceType(Enum):
    FOOD = auto()
    MEDICAL = auto()
    SECURITY = auto()

class AgentType(Enum):
    FOOD_AGENT = auto()
    MEDICAL_AGENT = auto()
    SECURITY_AGENT = auto()

class ActionType(Enum):
    MOVE = auto()
    SUPPLY_RESOURCE = auto()

class District:
    def __init__(self, name: str, resources: Dict[ResourceType, int], connections: List[str]):
        self.name = name
        self.resources = resources
        self.connections = connections
        self.health = 100  # Initialize district health to 100

    def consume_resources(self, consumption_rate: int):
        for resource in ResourceType:
            self.resources[resource] = max(0, self.resources[resource] - consumption_rate)

    def __str__(self):
        return f"District {self.name}: Resources {self.resources}, Health {self.health}, Connections {self.connections}"


class Agent:
    def __init__(self, agent_type: AgentType, max_carry: int):
        self.agent_type = agent_type
        self.current_district = None
        self.carrying_resource = 0
        self.max_carry = max_carry

    def move(self, district: District) -> bool:
        if self.current_district is None or district.name in self.current_district.connections:
            self.current_district = district
            return True
        return False

    def supply_resource(self, amount: int) -> bool:
        if self.current_district and 0 < amount <= self.carrying_resource:
            resource_type = self.get_resource_type()
            self.current_district.resources[resource_type] += amount
            self.carrying_resource -= amount
            return True
        return False

    def collect_resource(self, amount: int):
        self.carrying_resource = min(self.max_carry, self.carrying_resource + amount)

    def get_resource_type(self) -> ResourceType:
        return {
            AgentType.FOOD_AGENT: ResourceType.FOOD,
            AgentType.MEDICAL_AGENT: ResourceType.MEDICAL,
            AgentType.SECURITY_AGENT: ResourceType.SECURITY
        }[self.agent_type]

    def get_carrying_resource(self) -> int:
        return self.carrying_resource

class Game:
    def __init__(self, districts: List[District], agents: List[Agent], supply_node: str, max_turns: int, consumption_rate: int, replenish_amount: int):
        self.districts = {district.name: district for district in districts}
        self.agents = agents
        self.supply_node = supply_node
        self.current_turn = 0
        self.max_turns = max_turns
        self.consumption_rate = consumption_rate
        self.replenish_amount = replenish_amount
        # self.ideal_distribution = self.calculate_ideal_distribution()
        self.game_over = False
        self.game_over_reason = ""
    # def calculate_ideal_distribution(self) -> Dict[ResourceType, float]:
    #     total_resources = {rt: sum(d.resources[rt] for d in self.districts.values() if d.name != self.supply_node) for rt in ResourceType}
    #     return {rt: total_resources[rt] / (len(self.districts) - 1) for rt in ResourceType}

    def run_turn(self):
        self.current_turn += 1
        for district in self.districts.values():
            if district.name != self.supply_node:
                district.consume_resources(self.consumption_rate)
                self.update_district_health(district)
                # if district.health <= 0:
                #     self.game_over = True
                #     self.game_over_reason = f"District {district.name}'s health reached 0"
                #     return
        
        for agent in self.agents:
            if agent.current_district.name == self.supply_node:
                agent.collect_resource(self.replenish_amount)

    def update_district_health(self, district: District):
        for resource_type in ResourceType:
            resource_level = district.resources[resource_type]
            
            if resource_level <= 20:
                health_decrease = 10 if resource_level < 10 else 5
                district.health = max(0, district.health - health_decrease)

    def is_game_over(self) -> bool:
        return self.game_over or self.current_turn >= self.max_turns

    def calculate_score(self) -> float:
        total_health = sum(district.health for district in self.districts.values() if district.name != self.supply_node)
        return total_health / (len(self.districts) - 1)  # Average health, excluding supply node

    def get_all_connections(self) -> Dict[str, List[str]]:
        return {district.name: district.connections for district in self.districts.values()}

    def get_game_over_reason(self) -> str:
        if self.game_over:
            return self.game_over_reason
        elif self.current_turn >= self.max_turns:
            return "Maximum number of turns reached"
        else:
            return "Game is not over"

def create_game(max_turns: int, consumption_rate: int, replenish_amount: int, max_carry: int) -> Game:
    districts = [
        District("1", {ResourceType.FOOD: 0, ResourceType.MEDICAL: 0, ResourceType.SECURITY: 0}, ["2", "3"]),
        District("2", {ResourceType.FOOD: 40, ResourceType.MEDICAL: 60, ResourceType.SECURITY: 70}, ["1", "3", "4"]),
        District("3", {ResourceType.FOOD: 60, ResourceType.MEDICAL: 50, ResourceType.SECURITY: 40}, ["1", "2", "4"]),
        District("4", {ResourceType.FOOD: 30, ResourceType.MEDICAL: 80, ResourceType.SECURITY: 60}, ["2", "3"]),
        # District("5", {ResourceType.FOOD: 70, ResourceType.MEDICAL: 40, ResourceType.SECURITY: 30}, ["3"]),
    ]

    # ensure connections are bidirectional
    for district in districts:
        for connected_district_name in district.connections:
            connected_district = next(d for d in districts if d.name == connected_district_name)
            if district.name not in connected_district.connections:
                connected_district.connections.append(district.name)

    agents = [
        Agent(AgentType.FOOD_AGENT, max_carry),
        Agent(AgentType.MEDICAL_AGENT, max_carry),
        Agent(AgentType.SECURITY_AGENT, max_carry),
    ]
    supply_node = "1"

    # Initialize agents' current district
    for agent in agents:
        agent.move(districts[0])
        agent.collect_resource(replenish_amount)
    
    return Game(districts, agents, supply_node, max_turns, consumption_rate, replenish_amount)