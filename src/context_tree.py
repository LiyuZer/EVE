''' This will be our context tree, it will be a tree that stores the context of the conversation, including user messages, agent responses, and any relevant metadata. Each node in the tree will represent a turn in the conversation, with child nodes representing follow-up messages or actions. We can prune entire subtrees by pruning the parent node. We will hash each node's content to create a unique identifier for it. '''


import hashlib
import os




class ContextNode:
   def __init__(self, user_message: str, agent_response: str, system_response: str, metadata: dict):
       self.user_message = user_message
       self.agent_response = agent_response
       self.system_response = system_response
       self.metadata = metadata
       self.content_hash = self._generate_hash()
       self.children = []
       self.previous_node = None  # Optional link to previous node for easier traversal


   def _generate_hash(self):
       content = f"{self.user_message}{self.agent_response}{self.system_response}{str(self.metadata)}"
       return hashlib.sha256(content.encode()).hexdigest()[:8]
   def set_previous(self, prev_node):
       self.previous_node = prev_node


   def add_child(self, child_node: 'ContextNode'):
       self.children.append(child_node)


   def prune(self):
       self.children = []


   def __repr__(self):
       # Check if this is a user_message or agent_response
       return f"ContextNode(Content_hash: {self.content_hash}, Agent: {self.agent_response}, System: {self.system_response}, User: {self.user_message}, Metadata: {self.metadata})"


   def serialize(self):
       return {
           "user_message": self.user_message,
           "agent_response": self.agent_response,
           "system_response": self.system_response,
           "metadata": self.metadata,
           "content_hash": self.content_hash,
           "children": [child.serialize() for child in self.children],
       }
   def deserialize(data):
       node = ContextNode(
           user_message=data["user_message"],
           agent_response=data["agent_response"],
           system_response=data["system_response"],
           metadata=data["metadata"],
       )
       node.content_hash = data["content_hash"]
       node.children = [ContextNode.deserialize(child) for child in data.get("children", [])]
       # Re-establish previous_node links for children
       for child in node.children:
           child.set_previous(node)
       return node
class ContextTree:
   def __init__(self, root: ContextNode):
       self.root = root
       self.head = root
       # Optionally print initial structure when logging is enabled
       if os.getenv("EVE_LOG_CONTEXT_TREE"):
           print(self.structure_string())


   def serialize(self):
       return {
           "root": self.root.serialize(),
           "head_hash": self.head.content_hash,
       }
   def deserialize(data):
       root = ContextNode.deserialize(data["root"])
       tree = ContextTree(root)
       head_hash = data.get("head_hash")
       if head_hash:
           head_node = tree._find_node_by_hash(head_hash)
           if head_node:
               tree.head = head_node
       return tree
   def _find_node_by_hash(self, target_hash: str):
       """Recursively find a node by its content hash"""
       def _find(node: ContextNode):
           if node.content_hash == target_hash:
               return node
           for child in node.children:
               found = _find(child)
               if found:
                   return found
           return None


       return _find(self.root)


   def _find_node(self, node: ContextNode, target_hash: str):
       if node.content_hash == target_hash:
           return node
       for child in node.children:
           found = self._find_node(child, target_hash)
           if found:
               return found
       return None


   def add_node(self, new_node: ContextNode, parent_hash: str = None, advance_head: bool = True):
       if parent_hash is None:
           parent_hash = self.head.content_hash
       parent_node = self._find_node(self.root, parent_hash)
       if parent_node:
           parent_node.add_child(new_node)
           new_node.set_previous(parent_node)
       else:
           print(f"Warning: Parent node with hash {parent_hash} not found. Cannot add new node.")
           raise ValueError("Parent node not found")
       # Optional auto-print after each node addition when logging is enabled
       if os.getenv("EVE_LOG_CONTEXT_TREE"):
           print(self.structure_string())


      
       if advance_head:
           # Update HEAD to point to the new node
           self.head = new_node


   def rename(self, node_hash: str, new_label: str) -> bool:
       """Rename a node's label in metadata while preserving other contents.


       - Updates metadata["label"] with new_label
       - Preserves user_message, agent_response, system_response, children, and content_hash
       - Marks node metadata with {"renamed": True}
       - Returns True if node found and updated; False otherwise
       """
       target = self._find_node(self.root, node_hash)
       if not target:
           return False


       try:
           label = (new_label or "").strip()
       except Exception:
           label = str(new_label)


       if not isinstance(target.metadata, dict):
           target.metadata = {}
       target.metadata["label"] = label
       target.metadata["renamed"] = True
       return True
   def prune(self, node_hash: str, replacement_val: str):
       # Find target node first and check if HEAD lies in its subtree
       target = self._find_node(self.root, node_hash)
       if not target:
           return


       def _contains(parent: ContextNode, needle: ContextNode) -> bool:
           if parent is needle:
               return True
           for ch in parent.children:
               if _contains(ch, needle):
                   return True
           return False


       head_in_subtree = _contains(target, self.head)


       # Replace contents and drop children (collapse subtree)
       target.user_message = replacement_val
       target.agent_response = replacement_val
       target.metadata = {'pruned': True}
       target.children = []


       # If HEAD was inside the pruned subtree, re-anchor it to the pruned node
       if head_in_subtree:
           self.head = target


   def replace(self, node_hash: str, replacement_val: str, node_label: str | None = None) -> bool:
       """Replace a node's summary/label while preserving children and identity.


       - Updates user_message and agent_response with replacement_val (a compact summary)
       - Preserves children and system_response
       - Keeps the same content_hash (identity)
       - Optionally updates a short label via metadata["label"]
       - Marks node metadata with {"replaced": True}
       - Returns True if node found and updated; False otherwise
       """
       target = self._find_node(self.root, node_hash)
       if not target:
           return False


       try:
           summary = (replacement_val or "").strip()
       except Exception:
           summary = str(replacement_val)


       # Update summary fields; keep system_response as-is
       target.user_message = ""
       target.agent_response = summary


       target.metadata = {"replaced": True}
       return True
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


   # --- Short label derivation for structure view ---
   def _short_label(self, node: ContextNode, max_words: int = 4, max_len: int = 32) -> str:
       # 1) Prefer explicit metadata keys
       label = None
       if isinstance(node.metadata, dict):
           for key in ("label", "node_label"):
               if key in node.metadata and node.metadata[key]:
                   label = str(node.metadata[key])
                   break
       # 2) Derive from content fields if needed
       if not label:
           for field in (node.agent_response, node.user_message, node.system_response):
               if field:
                   label = str(field)
                   break
       # 3) Fallback to first metadata key
       if not label and isinstance(node.metadata, dict) and node.metadata:
           try:
               label = next(iter(node.metadata.keys()))
           except Exception:
               label = "node"
       if not label:
           return ""
       # Normalize to one line and trim words/length
       label = label.replace("\n", " ").replace("\r", " ").strip()
       words = label.split()
       words = words[:max_words]
       s = " ".join(words)
       if len(s) > max_len:
           s = s[: max_len - 1] + "…"
       return s




   def structure_string(self,node, include_full=False, max_words=10, max_label_len=32) -> str:
       # Start from root and recursively build structure
       def tree_structure_string(node: ContextNode, indent: int = 0, include_full=False) -> str:
           # Start from root and recursively build structure
           tree_str = ""
           tree_str = "  " * indent + "- "
           # Add the current root node
           label = self._short_label(node, max_words=max_words, max_len=max_label_len) if not include_full else repr(node)
           current_node = f"Hash: {node.content_hash} {label}"
           tree_str += current_node + "\n"
           for child in node.children:
               tree_str += current_node + "-> " + tree_structure_string(child, indent + 1)
           return tree_str
       return "=== CONTEXT TREE STRUCTURE ===\n" + tree_structure_string(node, 0, include_full=include_full)


   # --- Root to head path utilities ---
   def root_to_node_path(self, target: ContextNode | str | None = None) -> list[ContextNode]:
       """Return the list of nodes from root to the given target (inclusive).


       - target may be a ContextNode, a content hash (str), or None for current head.
       - Returns an empty list if the target is not found under root.
       """
       # Resolve target node
       if target is None:
           target_node = self.head
       elif isinstance(target, str):
           target_node = self._find_node(self.root, target)
           if not target_node:
               return []
       else:
           target_node = target


       path: list[ContextNode] = []


       def _dfs(node: ContextNode, acc: list[ContextNode]) -> bool:
           acc.append(node)
           if node is target_node:
               return True
           for ch in node.children:
               if _dfs(ch, acc):
                   return True
           acc.pop()
           return False


       acc: list[ContextNode] = []
       found = _dfs(self.root, acc)
       return acc if found else []


   def return_root_node_sub_tree_string(self, node, include_full=False) -> str:
       """ Returns the path from the root -> head, + heads subtree as well. So essentially a full view of the current context. """
       path = "=== Context Subtree ==="
       # Find the path from head to root, using previous_node links
       nodes = [node]
       while nodes[-1] is not self.root and nodes[-1].previous_node is not None:
           nodes.append(nodes[-1].previous_node)
       nodes.reverse()  # Now from root to head
       path_str = ""
       # The path string will be Hash Label -> Hash Label -> ...
       for n in nodes:
           label = self._short_label(n, max_words=5, max_len=24) if not include_full else repr(n)
           path_str += f"[{n.content_hash}] {label} -> "
       path_str = path_str.rstrip(" -> ")  # Remove trailing arrow
       path += "\n" + path_str + "\n"
       # Add the subtree under using structure_string
       path += self.structure_string(node, include_full=include_full, max_words=3, max_label_len=24)


       return path




   # --- Summarized view for LLM context (short fields; minimal metadata) ---
   def _shorten(self, text, max_len: int = 120) -> str:
       if text is None:
           return ""
       s = str(text).replace("\n", " ").replace("\r", " ")
       if len(s) <= max_len:
           return s
       return s[: max_len - 1] + "…"


   def _meta_keys_summary(self, metadata: dict, max_keys: int = 5) -> str:
       if not isinstance(metadata, dict) or not metadata:
           return ""
       keys = list(metadata.keys())
       shown = keys[:max_keys]
       more = len(keys) - len(shown)
       base = ", ".join(shown)
       return f"{base} (+{more})" if more > 0 else base


   def _tree_to_summary(
       self,
       node: ContextNode,
       indent: int = 0,
       lines: list | None = None,
       max_len: int = 120,
       max_keys: int = 5,
   ):
       if lines is None:
           lines = []
       prefix = ("  " * indent) + "- "
       head_marker = " (HEAD)" if node is self.head else ""
       pruned_marker = " [PRUNED]" if isinstance(node.metadata, dict) and node.metadata.get("pruned") else ""
       u = self._shorten(node.user_message, max_len)
       a = self._shorten(node.agent_response, max_len)
       s = self._shorten(node.system_response, max_len)
       m = self._meta_keys_summary(node.metadata, max_keys)
       label = f"[{node.content_hash}]{head_marker}{pruned_marker} u={u!r} a={a!r} s={s!r} m={m}"
       lines.append(prefix + label)
       for child in node.children:
           self._tree_to_summary(child, indent + 1, lines, max_len=max_len, max_keys=max_keys)
       return lines


   def summary_string(self, max_len: int = 120, max_keys: int = 5) -> str:
       lines = self._tree_to_summary(self.root, 0, [], max_len=max_len, max_keys=max_keys)
       out = ["=== CONTEXT TREE (SUMMARY) ==="]
       out.extend(lines)
       return "\n".join(out) + "\n"

