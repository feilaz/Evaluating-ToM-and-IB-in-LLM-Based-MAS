import json
from typing import Dict, List, Set
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

class AgentKnowledgeBase:
    def __init__(self, kb_file: str = 'knowledge_base.json', vocab_file: str = 'vocabulary.json'):
        self.kb_file = kb_file
        self.vocab_file = vocab_file
        self._clear_knowledge_base()
        self.knowledge_base: Dict[str, Dict[str, List[str]]] = {}
        self.vocabulary: Dict[str, Set[str]] = self._load_vocabulary()
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        self.stop_words = set(stopwords.words('english'))

    def _clear_knowledge_base(self):
        with open(self.kb_file, 'w') as f:
            json.dump({}, f)

    def _save_knowledge_base(self):
        with open(self.kb_file, 'w') as f:
            json.dump(self.knowledge_base, f, indent=2)

    def _load_vocabulary(self) -> Dict[str, Set[str]]:
        try:
            with open(self.vocab_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"global": set(data)}
                elif isinstance(data, dict):
                    return {agent: set(words) for agent, words in data.items()}
                else:
                    print(f"Unexpected vocabulary data format. Using empty vocabulary.")
                    return {}
        except FileNotFoundError:
            return {}

    def _save_vocabulary(self):
        with open(self.vocab_file, 'w') as f:
            json.dump({agent: list(words) for agent, words in self.vocabulary.items()}, f, indent=2)

    def add_knowledge(self, agent_name: str, category: str, content: str):
        if agent_name not in self.knowledge_base:
            self.knowledge_base[agent_name] = {}
        if category not in self.knowledge_base[agent_name]:
            self.knowledge_base[agent_name][category] = []
        self.knowledge_base[agent_name][category].append(content)
        self._save_knowledge_base()

    def update_vocabulary(self, agent_name: str, text: str):
        if agent_name not in self.vocabulary:
            self.vocabulary[agent_name] = set()

        words = word_tokenize(text.lower())
        new_words = set(word for word in words if word.isalnum() and word not in self.stop_words)
        self.vocabulary[agent_name].update(new_words)
        self._save_vocabulary()

    def get_agent_knowledge(self, agent_name: str, category: str = None) -> Dict[str, List[str]]:
        if agent_name not in self.knowledge_base:
            return []
        if category:
            return self.knowledge_base[agent_name].get(category, [])
        return self.knowledge_base[agent_name]

    def get_agent_vocabulary(self, agent_name: str) -> Set[str]:
        if "global" in self.vocabulary:
            return self.vocabulary["global"]
        return self.vocabulary.get(agent_name, set())

    def get_all_knowledge(self) -> Dict[str, Dict[str, List[str]]]:
        return self.knowledge_base

    def get_all_vocabulary(self) -> Dict[str, Set[str]]:
        return self.vocabulary