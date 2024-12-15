import unittest
from game import Game, District, Agent, AgentType, ResourceType, create_game
from disaster_response_integration import DisasterResponseIntegration

class TestCityCrisisGame(unittest.TestCase):

    def setUp(self):
        self.game_integration = DisasterResponseIntegration(max_turns=10, consumption_rate=10, replenish_amount=50, max_carry=100)

    def test_game_initialization(self):
        self.assertEqual(len(self.game_integration.game.districts), 6)  # Including supply node
        self.assertEqual(len(self.game_integration.game.agents), 3)
        self.assertEqual(self.game_integration.game.supply_node, "6")

    def test_district_connections(self):
        connections = self.game_integration.get_district_connections("1")
        self.assertIn("2", connections)
        self.assertIn("3", connections)

    def test_agent_movement(self):
        food_agent = next(a for a in self.game_integration.game.agents if a.agent_type == AgentType.FOOD_AGENT)
        initial_district = food_agent.current_district.name
        
        # Valid move
        result = self.game_integration.execute_command(AgentType.FOOD_AGENT, "MOVE(2)")
        self.assertIn("moved to District 2", result)
        self.assertEqual(food_agent.current_district.name, "2")

        # Invalid move
        result = self.game_integration.execute_command(AgentType.FOOD_AGENT, "MOVE(5)")
        self.assertIn("Invalid move", result)
        self.assertEqual(food_agent.current_district.name, "2")

    def test_resource_supply(self):
        food_agent = next(a for a in self.game_integration.game.agents if a.agent_type == AgentType.FOOD_AGENT)
        food_agent.carrying_resource = 50

        initial_food = food_agent.current_district.resources[ResourceType.FOOD]

        # Valid supply
        result = self.game_integration.execute_command(AgentType.FOOD_AGENT, "SUPPLY_RESOURCE(30)")
        self.assertIn("supplied 30 resources", result)
        self.assertEqual(food_agent.carrying_resource, 20)
        self.assertEqual(food_agent.current_district.resources[ResourceType.FOOD], initial_food + 30)

        # Invalid supply (too much)
        result = self.game_integration.execute_command(AgentType.FOOD_AGENT, "SUPPLY_RESOURCE(30)")
        self.assertIn("Invalid supply", result)
        self.assertEqual(food_agent.carrying_resource, 20)

    def test_resource_collection(self):
        food_agent = next(a for a in self.game_integration.game.agents if a.agent_type == AgentType.FOOD_AGENT)
        # district_6 = next(d for d in self.game_integration.game.districts if d == "6")
        print(self.game_integration.game.districts["6"])   
        food_agent.move(self.game_integration.game.districts["6"])  # Move to supply node
        self.assertEqual(food_agent.current_district.name, "6")
        initial_carrying = food_agent.carrying_resource

        self.game_integration.update_game_state()
        self.assertEqual(food_agent.carrying_resource, min(initial_carrying + 50, food_agent.max_carry))

    def test_game_over(self):
        for _ in range(10):
            self.game_integration.update_game_state()
        
        self.assertTrue(self.game_integration.is_game_over())
        game_over_message = self.game_integration.get_game_over_message()
        self.assertIn("city crisis response has ended", game_over_message)

    def test_get_agent_info(self):
        food_agent = next(a for a in self.game_integration.game.agents if a.agent_type == AgentType.FOOD_AGENT)
        food_agent.carrying_resource = 75

        info = self.game_integration.get_agent_info(AgentType.FOOD_AGENT)
        self.assertIn("current_district", info)
        self.assertIn("carrying_resource", info)
        self.assertIn("district_resources", info)
        self.assertIn("district_connections", info)
        self.assertEqual(info["carrying_resource"], 75)

    def test_get_district_resources(self):
        resources = self.game_integration.get_district_resources("1")
        self.assertIn(ResourceType.FOOD, resources)
        self.assertIn(ResourceType.MEDICAL, resources)
        self.assertIn(ResourceType.SECURITY, resources)

    def test_supply_node(self):
        supply_node_resources = self.game_integration.get_district_resources("6")
        self.assertEqual(supply_node_resources[ResourceType.FOOD], 0)
        self.assertEqual(supply_node_resources[ResourceType.MEDICAL], 0)
        self.assertEqual(supply_node_resources[ResourceType.MEDICAL], 0)

if __name__ == '__main__':
    unittest.main()