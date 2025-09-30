# context_tree_visualizer.py
"""
Rich terminal visualization for ContextTree
Add this to your context_tree.py file
"""
import colorama
from typing import Optional

class TreeVisualizer:
    """ASCII visualization for ContextTree with rich formatting"""
    
    def __init__(self, tree):
        self.tree = tree
        colorama.init()
        
        # Color scheme
        self.colors = {
            'head': colorama.Fore.YELLOW + colorama.Style.BRIGHT,
            'pruned': colorama.Fore.RED + colorama.Style.DIM,
            'checkpoint': colorama.Fore.CYAN + colorama.Style.BRIGHT,
            'file_op': colorama.Fore.GREEN,
            'shell': colorama.Fore.BLUE,
            'thinking': colorama.Fore.MAGENTA + colorama.Style.DIM,
            'buffer': colorama.Fore.LIGHTMAGENTA_EX,
            'default': colorama.Fore.WHITE,
            'hash': colorama.Fore.WHITE + colorama.Style.DIM,
            'dim': colorama.Style.DIM,
            'reset': colorama.Style.RESET_ALL,
        }
    
    def _get_node_color(self, node) -> str:
        """Determine color based on node metadata"""
        meta = node.metadata
        
        if node == self.tree.head:
            return self.colors['head']
        elif meta.get('pruned'):
            return self.colors['pruned']
        elif meta.get('checkpoint'):
            return self.colors['checkpoint']
        elif meta.get('File Written') or meta.get('File Read'):
            return self.colors['file_op']
        elif meta.get('Shell Command'):
            return self.colors['shell']
        elif meta.get('thoughts'):
            return self.colors['thinking']
        elif any(k.startswith('Buffer') for k in meta.keys()):
            return self.colors['buffer']
        
        return self.colors['default']
    
    def _get_node_icon(self, node) -> str:
        """Get icon for node type"""
        meta = node.metadata
        
        if node == self.tree.head:
            return "◀"
        elif meta.get('pruned'):
            return "✂"
        elif meta.get('checkpoint'):
            return "★"
        elif meta.get('File Written'):
            return "✍"
        elif meta.get('File Read'):
            return "📖"
        elif meta.get('Shell Command'):
            return "⚡"
        elif meta.get('thoughts'):
            return "💭"
        elif meta.get('replaced'):
            return "🔄"
        elif any(k.startswith('Buffer') for k in meta.keys()):
            return "📝"
        
        return "•"
    
    def _format_node_label(self, node, max_len: int = 50) -> str:
        """Format node label with metadata hints"""
        label = self.tree._short_label(node, max_words=6, max_len=max_len)
        
        # Add metadata hints
        meta = node.metadata
        hints = []
        
        if meta.get('File Written'):
            hints.append(f"wrote: {meta['File Written']}")
        elif meta.get('File Read'):
            hints.append(f"read: {meta['File Read']}")
        elif meta.get('Shell Command'):
            cmd = meta['Shell Command']
            hints.append(f"ran: {cmd[:30]}...")
        elif meta.get('checkpoint'):
            hints.append(f"checkpoint: {meta['checkpoint']}")
        
        if hints:
            label = f"{label} {self.colors['dim']}({', '.join(hints)}){self.colors['reset']}"
        
        return label
    
    def render_tree(self, 
                   node: Optional['ContextNode'] = None,
                   show_full: bool = False,
                   max_depth: Optional[int] = None,
                   highlight_path: bool = True) -> str:
        """
        Render tree as ASCII art with Unicode box drawing
        
        Args:
            node: Starting node (defaults to root)
            show_full: Show full details vs compact view
            max_depth: Maximum depth to render (None = unlimited)
            highlight_path: Highlight path from root to HEAD
        """
        if node is None:
            node = self.tree.root
        
        # Get path from root to HEAD for highlighting
        head_path = set()
        if highlight_path:
            path_nodes = self.tree.root_to_node_path(self.tree.head)
            head_path = {n.content_hash for n in path_nodes}
        
        output = []
        output.append("\n" + self.colors['head'] + "═" * 70 + self.colors['reset'])
        output.append(self.colors['head'] + "  CONTEXT TREE VISUALIZATION" + self.colors['reset'])
        output.append(self.colors['head'] + "═" * 70 + self.colors['reset'] + "\n")
        
        def render_node(node, prefix: str = "", is_last: bool = True, depth: int = 0):
            if max_depth is not None and depth > max_depth:
                return
            
            # Determine if this node is on path to HEAD
            on_path = node.content_hash in head_path
            
            # Build the tree structure
            if depth == 0:
                connector = ""
                extension = ""
            else:
                connector = "└── " if is_last else "├── "
                extension = "    " if is_last else "│   "
            
            # Get node styling
            color = self._get_node_color(node)
            icon = self._get_node_icon(node)
            hash_str = self.colors['hash'] + f"[{node.content_hash[:6]}]" + self.colors['reset']
            label = self._format_node_label(node)
            
            # Add path indicator
            path_indicator = " ←" if on_path and node != self.tree.head else ""
            
            # Compose the line
            line = f"{prefix}{connector}{icon} {hash_str} {color}{label}{self.colors['reset']}{path_indicator}"
            output.append(line)
            
            # Render children
            children = node.children
            for i, child in enumerate(children):
                is_last_child = (i == len(children) - 1)
                new_prefix = prefix + extension
                render_node(child, new_prefix, is_last_child, depth + 1)
        
        render_node(node)
        
        # Add statistics
        output.append("\n" + self.colors['dim'] + "─" * 70 + self.colors['reset'])
        stats = self._get_tree_stats()
        output.append(f"{self.colors['dim']}Stats: {stats}{self.colors['reset']}")
        output.append(self.colors['dim'] + "─" * 70 + self.colors['reset'] + "\n")
        
        return "\n".join(output)
    
    def _get_tree_stats(self) -> str:
        """Calculate tree statistics"""
        total_nodes = 0
        pruned_nodes = 0
        max_depth = 0
        
        def count_nodes(node, depth=0):
            nonlocal total_nodes, pruned_nodes, max_depth
            total_nodes += 1
            if node.metadata.get('pruned'):
                pruned_nodes += 1
            max_depth = max(max_depth, depth)
            for child in node.children:
                count_nodes(child, depth + 1)
        
        count_nodes(self.tree.root)
        
        return (f"Total nodes: {total_nodes} | "
                f"Pruned: {pruned_nodes} | "
                f"Max depth: {max_depth} | "
                f"HEAD: [{self.tree.head.content_hash[:6]}]")
    
    def render_path_to_head(self) -> str:
        """Render just the path from root to current HEAD"""
        path = self.tree.root_to_node_path(self.tree.head)
        
        output = []
        output.append("\n" + self.colors['head'] + "═" * 70 + self.colors['reset'])
        output.append(self.colors['head'] + "  PATH TO HEAD" + self.colors['reset'])
        output.append(self.colors['head'] + "═" * 70 + self.colors['reset'] + "\n")
        
        for i, node in enumerate(path):
            color = self._get_node_color(node)
            icon = self._get_node_icon(node)
            hash_str = self.colors['hash'] + f"[{node.content_hash[:6]}]" + self.colors['reset']
            label = self._format_node_label(node, max_len=60)
            
            arrow = " ↓" if i < len(path) - 1 else ""
            line = f"  {icon} {hash_str} {color}{label}{self.colors['reset']}{arrow}"
            output.append(line)
        
        output.append("")
        return "\n".join(output)
    
    def render_subtree(self, node_hash: str, max_depth: int = 3) -> str:
        """Render a specific subtree"""
        node = self.tree._find_node(self.tree.root, node_hash)
        if not node:
            return f"Node {node_hash} not found"
        
        return self.render_tree(node=node, max_depth=max_depth, highlight_path=False)
    
    def export_html(self, output_path: str = "context_tree.html"):
        """Export tree as interactive HTML"""
        def node_to_dict(node):
            return {
                "hash": node.content_hash[:8],
                "label": self.tree._short_label(node, max_words=4, max_len=40),
                "is_head": node == self.tree.head,
                "pruned": node.metadata.get("pruned", False),
                "metadata": str(node.metadata)[:100],
                "children": [node_to_dict(child) for child in node.children]
            }
        
        tree_data = node_to_dict(self.tree.root)
        
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: 'Courier New', monospace; 
            padding: 20px; 
            background: #1e1e1e; 
            color: #d4d4d4;
        }
        h1 { color: #ffd700; }
        .tree { margin-top: 20px; }
        .node { margin-left: 20px; border-left: 1px solid #444; padding-left: 10px; margin-top: 5px; }
        .node-header { cursor: pointer; padding: 5px; }
        .node-header:hover { background: #2a2a2a; }
        .hash { color: #888; font-size: 0.9em; }
        .label { color: #d4d4d4; }
        .head { background: #ffd70033; border-left: 3px solid #ffd700; }
        .pruned { color: #ff6b6b; text-decoration: line-through; }
        .children { margin-left: 10px; }
        .toggle { color: #569cd6; margin-right: 5px; user-select: none; }
        .metadata { 
            color: #888; 
            font-size: 0.85em; 
            margin-left: 20px; 
            padding: 5px;
            background: #2a2a2a;
            border-radius: 3px;
            display: none;
        }
    </style>
</head>
<body>
    <h1>🐉 Context Tree Visualization</h1>
    <div class="tree" id="tree"></div>
    
    <script>
        const treeData = """ + str(tree_data).replace("'", '"').replace("True", "true").replace("False", "false") + """;
        
        function renderNode(node, container) {
            const nodeDiv = document.createElement('div');
            nodeDiv.className = 'node' + (node.is_head ? ' head' : '') + (node.pruned ? ' pruned' : '');
            
            const header = document.createElement('div');
            header.className = 'node-header';
            
            const hasChildren = node.children && node.children.length > 0;
            const toggle = hasChildren ? '<span class="toggle">▼</span>' : '<span class="toggle">•</span>';
            
            const icon = node.is_head ? '◀' : (node.pruned ? '✂' : '•');
            header.innerHTML = `${toggle}${icon} <span class="hash">[${node.hash}]</span> <span class="label">${node.label}</span>`;
            
            const metaDiv = document.createElement('div');
            metaDiv.className = 'metadata';
            metaDiv.textContent = node.metadata;
            
            header.onclick = () => {
                metaDiv.style.display = metaDiv.style.display === 'none' ? 'block' : 'none';
            };
            
            nodeDiv.appendChild(header);
            nodeDiv.appendChild(metaDiv);
            
            if (hasChildren) {
                const childrenDiv = document.createElement('div');
                childrenDiv.className = 'children';
                node.children.forEach(child => renderNode(child, childrenDiv));
                nodeDiv.appendChild(childrenDiv);
            }
            
            container.appendChild(nodeDiv);
        }
        
        renderNode(treeData, document.getElementById('tree'));
    </script>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
