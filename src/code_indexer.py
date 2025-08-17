'''
A code indexer with TTL caching for file contexts and a lightweight
AST-based dependency resolver that searches within the repository.

Keeps the original AstVisitor and return_context API shape while
removing external pydeps dependency.
'''
import json
import os
import ast
import time
from typing import Dict, Optional, List, Set


class AstVisitor(ast.NodeVisitor):
    """Collect class and function definitions from a Python AST.

    get_context returns a JSON string with the following structure:
    {
        'classes': [{'name': ...}, ...],
        'functions': [{'name': ..., 'args': [...], 'posonlyargs': [...]}, ...]
    }
    """

    def __init__(self):
        super().__init__()
        self.classes = []
        self.functions = []

    def visit_ClassDef(self, node):
        self.classes.append({
            'name': node.name,
        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append({
            'name': node.name,
            'args': [arg.arg for arg in node.args.args],
            'posonlyargs': [arg.arg for arg in node.args.posonlyargs],
        })
        self.generic_visit(node)

    # Return string representation of the context
    def get_context(self):
        context = {
            'classes': self.classes,
            'functions': self.functions
        }
        return json.dumps(context)


class CodeIndexer:
    """Code indexer that resolves direct imports via AST and caches file contexts.

    - TTL cache: caches parsed file contexts keyed by absolute file path.
    - Dependency analysis: only direct imports ("bacon" == 1) are returned.
    - return_context: builds a mapping of {file_name: {'context': json_string}}
      for dependencies within the given root.
    """

    def __init__(self, ttl_seconds: int = 300, time_provider=None):
        # Time-to-live for cached file contexts (seconds)
        self.ttl_seconds = int(ttl_seconds)
        # Time provider for testability (injectable); defaults to time.time
        self.time = time_provider or time.time
        # Cache format: {abs_path: {'expires_at': float, 'data': json_string}}
        self._context_cache: Dict[str, Dict[str, object]] = {}
        # Lightweight stats to facilitate testing/inspection
        self._stats: Dict[str, int] = {
            'contexts_parsed': 0  # counts actual AST parses for contexts
        }

    # -------------------------------
    # TTL Cache helpers
    # -------------------------------
    def _get_cached_context(self, abs_path: str) -> Optional[str]:
        entry = self._context_cache.get(abs_path)
        if not entry:
            return None
        if self.time() < entry.get('expires_at', 0):
            return entry.get('data')  # type: ignore[return-value]
        # Expired: delete and miss
        self._context_cache.pop(abs_path, None)
        return None

    def _set_cache(self, abs_path: str, json_context: str) -> None:
        self._context_cache[abs_path] = {
            'expires_at': self.time() + self.ttl_seconds,
            'data': json_context,
        }

    # -------------------------------
    # Context extraction (with cache)
    # -------------------------------
    def _parse_file_context(self, dependency_path: str) -> Optional[str]:
        """Return JSON string context for a file, using TTL cache when valid."""
        abs_path = os.path.realpath(dependency_path)
        cached = self._get_cached_context(abs_path)
        if cached is not None:
            return cached
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=abs_path)
        except Exception:
            return None

        visitor = AstVisitor()
        visitor.visit(tree)
        context_json = visitor.get_context()
        self._set_cache(abs_path, context_json)
        self._stats['contexts_parsed'] += 1
        return context_json

    # -------------------------------
    # Dependency analysis
    # -------------------------------
    def _is_path_within_root(self, path: str, root_path: str) -> bool:
        real_path = os.path.realpath(path)
        real_root = os.path.realpath(root_path)
        return os.path.commonpath([real_path, real_root]) == real_root

    def _resolve_module_to_path(self, module: str, root_path: str) -> Optional[str]:
        """Resolve absolute module name to a file path within root.

        Tries root/a/b.py and root/a/b/__init__.py for module 'a.b'.
        """
        parts = module.split('.') if module else []
        if not parts:
            return None
        candidate_py = os.path.join(root_path, *parts) + '.py'
        candidate_pkg = os.path.join(root_path, *parts, '__init__.py')
        for cand in (candidate_py, candidate_pkg):
            if os.path.isfile(cand) and self._is_path_within_root(cand, root_path):
                # Ignore virtual envs or site-packages
                if 'venv' in cand or 'site-packages' in cand:
                    continue
                return os.path.realpath(cand)
        return None

    def _resolve_relative_to_path(self, base_dir: str, parts: List[str], root_path: str) -> Optional[str]:
        """Resolve a module expressed as parts relative to base_dir within root."""
        if not parts:
            return None
        # Prefer module file then package __init__.py
        candidate_py = os.path.join(base_dir, *parts) + '.py'
        candidate_pkg = os.path.join(base_dir, *parts, '__init__.py')
        for cand in (candidate_py, candidate_pkg):
            if os.path.isfile(cand) and self._is_path_within_root(cand, root_path):
                if 'venv' in cand or 'site-packages' in cand:
                    continue
                return os.path.realpath(cand)
        return None

    def analyze_project_dependencies(self, file_path: str, root_path: Optional[str] = None) -> Dict[str, Dict[str, object]]:
        """Analyze direct imports of a file using AST, resolving only within root_path.

        Returns a dict compatible with the previous structure:
        {
          module_key: {
             'path': '/abs/path/to/file.py',
             'bacon': 1
          },
          ...
        }

        Notes:
        - Only direct imports of the target file are considered (bacon == 1).
        - Anything outside root_path or inside venv/site-packages is skipped.
        - For "from X import Y", we first try X.Y; if it cannot be resolved to a
          file, we fall back to X.
        - Relative imports are resolved from the current file's directory,
          moving up (level - 1) directories for ImportFrom with level > 0.
        """
        if root_path is None:
            # Default to the directory of file_path if not provided
            root_path = os.path.dirname(os.path.realpath(file_path))
        deps: Dict[str, Dict[str, object]] = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
        except Exception:
            return deps

        # Collect and resolve imports
        resolved_paths: Set[str] = set()
        file_dir = os.path.dirname(os.path.realpath(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # import a, import a.b as c
                for alias in node.names:
                    module_name = alias.name
                    path = self._resolve_module_to_path(module_name, root_path)
                    if path and path not in resolved_paths:
                        deps[module_name] = {'path': path, 'bacon': 1}
                        resolved_paths.add(path)

            elif isinstance(node, ast.ImportFrom):
                level = getattr(node, 'level', 0) or 0
                module = node.module  # may be None

                if level == 0:
                    # Absolute: try module.alias first, fallback to module
                    for alias in node.names:
                        candidates: List[str] = []
                        if module:
                            if alias.name == '*':
                                candidates = [module]
                            else:
                                candidates = [f"{module}.{alias.name}", module]
                        else:
                            # from import ... with no module is unusual; skip
                            continue
                        resolved = None
                        for cand in candidates:
                            resolved = self._resolve_module_to_path(cand, root_path)
                            if resolved:
                                break
                        if resolved and resolved not in resolved_paths:
                            key = candidates[0] if candidates else (module or alias.name)
                            deps[key] = {'path': resolved, 'bacon': 1}
                            resolved_paths.add(resolved)
                else:
                    # Relative import: ascend (level - 1) dirs from file_dir
                    base_dir = file_dir
                    for _ in range(max(level - 1, 0)):
                        base_dir = os.path.dirname(base_dir)

                    for alias in node.names:
                        # Build parts. If module provided, prepend its parts.
                        if module:
                            mod_parts = module.split('.') if module else []
                        else:
                            mod_parts = []

                        if alias.name == '*':
                            parts = mod_parts
                        else:
                            parts = mod_parts + [alias.name]

                        resolved = self._resolve_relative_to_path(base_dir, parts, root_path)
                        if not resolved and module:
                            # Fallback to module only
                            resolved = self._resolve_relative_to_path(base_dir, mod_parts, root_path)
                        if resolved and resolved not in resolved_paths:
                            key = ('.' * level) + (module or '')
                            if alias.name and alias.name != '*':
                                if key:
                                    key = f"{key}.{alias.name}" if module else f"{key}{alias.name}"
                                else:
                                    key = alias.name
                            deps[key or alias.name] = {'path': resolved, 'bacon': 1}
                            resolved_paths.add(resolved)

        return deps

    # Return a dict of over file dependencies and their class/function definitions, etc
    def return_context(self, file_path: str, root_path: str = '/Users/liyuzerihun/eve'):
        # First analyze the project dependencies (direct only)
        dependencies = self.analyze_project_dependencies(file_path, root_path=root_path) or {}
        # Loop through each key in the dependencies
        context: Dict[str, Dict[str, str]] = {}
        for key, value in dependencies.items():
            # Preserve original bacon filtering behavior
            try:
                bacon = value.get('bacon', 1)
            except Exception:
                bacon = 1
            if bacon == 0 or bacon == 2:
                continue

            dependency_path = value.get('path')
            if not dependency_path or not isinstance(dependency_path, str):
                continue

            # Skip venv/site-packages explicitly (defensive)
            if 'venv' in dependency_path or 'site-packages' in dependency_path:
                continue
            # Ensure the path is within root_path
            if not self._is_path_within_root(dependency_path, root_path):
                continue

            # Take the filename
            file_name = dependency_path.split('/')[-1]

            # Parse file context with cache
            context_json = self._parse_file_context(dependency_path)
            if context_json is None:
                continue

            # Get the context from the visitor
            context[file_name] = {
                'context': context_json
            }

        return context