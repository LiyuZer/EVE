''' This will be our context tree, it will be a tree that stores the context of the conversation, including user messages, agent responses, and any relevant metadata. Each node in the tree will represent a turn in the conversation, with child nodes representing follow-up messages or actions. We can prune entire subtrees by pruning the parent node. We will hash each node's content to create a unique identifier for it. '''

import hashlib

class ContextNode:
    def __init__(self, user_message: str, agent_response: str, system_response: str, metadata: dict):
        self.user_message = user_message
        self.agent_response = agent_response
        self.system_response = system_response
        self.metadata = metadata
        self.content_hash = self._generate_hash()
        self.children = []
    
    def _generate_hash(self):
        content = f"{self.user_message}{self.agent_response}{self.system_response}{str(self.metadata)}"
        return hashlib.sha256(content.encode()).hexdigest()[:8]

    def add_child(self, child_node: 'ContextNode'):
        self.children.append(child_node)

    def prune(self):
        self.children = []

    def __repr__(self):
        # Check if this is a user_message or agent_response
        return f"ContextNode(Content_hash: {self.content_hash}, Agent: {self.agent_response}, System: {self.system_response}, User: {self.user_message}, Metadata: {self.metadata})"

class ContextTree:
    def __init__(self, root: ContextNode):
        self.root = root
        self.head = root

    def _find_node(self, node: ContextNode, target_hash: str):
        if node.content_hash == target_hash:
            return node
        for child in node.children:
            found = self._find_node(child, target_hash)
            if found:
                return found
        return None

    def add_node(self, new_node: ContextNode, parent_hash: str = None):
        if parent_hash is None:
            parent_hash = self.head.content_hash
        parent_node = self._find_node(self.root, parent_hash)
        if parent_node:
            parent_node.add_child(new_node)
        else:
            raise ValueError("Parent node not found")
        self.head = new_node

    def prune(self, node_hash: str, replacement_val: str):
        # Recursively find the correct node hash
        def _prune(node: ContextNode):
            if node.content_hash == node_hash:
                # Disconnect the node
                node.user_message = replacement_val
                node.agent_response = replacement_val
                node.metadata = {'pruned': True}
                node.children = []
            else:
                for child in node.children:
                    _prune(child)

        _prune(self.root)

    def _tree_to_string(self, node: ContextNode, indent: int = 0):
        """Recursively build string representation of tree"""
        prefix = "  " * indent
        result = f"{prefix}{node}\n"
        for child in node.children:
            result += self._tree_to_string(child, indent + 1)
        return result

    def __str__(self):
        tree_str = "=== CONTEXT TREE ===\n"
        tree_str += self._tree_to_string(self.root)
        tree_str += f"\n=== HEAD ===\n{self.head}"
        return tree_str

    def __repr__(self):
        return f"ContextTree(Root: {self.root})"