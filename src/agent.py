'''
Agent interacts with three modular components-
    LLM interface for communicating with the GPT API
    Shell interface, for executing commands on shell and receiving stderr and stdout
    File system for interacting with the file system, read and write to the file information
'''
from dotenv import load_dotenv
import os
import sys
import re
from src.schema import *
from src.prompt import *
from src.file_system import FileHandler
from src.shell import ShellInterface
from src.terminal import TerminalInterface
from src.llm import llmInterface
from src.memory import EveMemory  # Import Eve's memory for semantic storage
from src.logging_config import setup_logger  # Import improved logger setup
from src.context_tree import ContextTree, ContextNode
import base64
from src.progress_buffer import ProgressBuffer
from dotenv import load_dotenv

load_dotenv()
api_key_v = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")
username = os.getenv("USERNAME") or os.getenv("USER") or "friend"

# Initialize logger once; level is picked up from LOG_LEVEL env if set
logger = setup_logger("agent", "project.log")

def parse_user_label(text: str) -> tuple[Optional[str], str]:
    """Extract an optional user-supplied label from the beginning of input.
    Supported forms:
      - "[label: My Label] actual message"
      - "{label: My Label} actual message"
      - "label: My Label | actual message"
    Returns: (label_or_None, cleaned_message)
    """
    if text is None:
        return None, ""
    s = str(text)
    # [label: ...] or {label: ...}
    m = re.match(r"^\s*[\[\{]\s*label\s*:\s*(.*?)\s*[\]\}]\s*(.*)$", s, flags=re.IGNORECASE)
    if m:
        label = m.group(1).strip()
        rest = m.group(2).strip()
        return (label or None), rest
    # label: ... | message
    m = re.match(r"^\s*label\s*:\s*(.*?)\s*\|\s*(.*)$", s, flags=re.IGNORECASE)
    if m:
        label = m.group(1).strip()
        rest = m.group(2).strip()
        return (label or None), rest
    return None, s

class Agent:
    def __init__(self, root, mode: str = "console"):
        self.llm_client = llmInterface(api_key=api_key_v, model=model)
        self.shell = ShellInterface()
        # Use the provided root (workspace root in IDE mode) as the base for FS ops
        self.root = root
        self.progress_buffer = ProgressBuffer(file_path=os.path.join(self.root, "PROGRESS.md"))
        self.file_system = FileHandler(base_root=self.root)
        self.terminal = TerminalInterface(username=username)
        self.memory = EveMemory()
        self.mode = mode  # "console" or "ide"
        self.images = []
        context_node = ContextNode(
            user_message="",
            agent_response="",
            system_response=base_prompt,
            metadata={"root directory": self.root}
        )
        self.context_tree = ContextTree(root=context_node)

    def start_execution(self):
        ide_mode = True if getattr(self, "mode", "console") == "ide" else False
        self.terminal.print_agent_message("Eve is in IDE mode." if ide_mode else "Eve is running in console mode.")

        # Show console banner/prompt only if NOT running inside the IDE panel
        if not ide_mode:
            # Show EVE ASCII banner before anything else
            self.terminal.print_banner()
            self.terminal.print_welcome_message()
            self.terminal.print_username()
        # First user input (from console or IDE stdin)
        user_input = input()
        # Parse optional user label syntax
        user_label, cleaned = parse_user_label(user_input)
        metadata = {"label": user_label} if user_label else {}
        self.context_tree.add_node(ContextNode(
            user_message=cleaned,
            agent_response="",
            system_response="",
            metadata=metadata
        ))

        # Log initial user input AFTER user step
        logger.info(f"User input received: {cleaned}")

        while True:
            # Use simplified summary of context tree for LLM input
            context_core = self.context_tree.return_root_node_sub_tree_string(self.context_tree.head, include_full=True) 
            size_line = "Context Tree size: " + str(len(str(context_core))) + " characters; hard max 800,000."
            policy_line = (
                """" 
                Planning policy: If the task is complex try to break it down into sub sections.
                                    When you are done with a section, prune it and go up.
                                    Plan using nop action = 9, these are your thoughts
                                    Replace context node using action=10
                                    Add context node using action=6, put the node_hash as the hash of the parent_Node (this must be there), and the label in node_label
                                    Prune context node using action=4
                                    Change context HEAD using action=5
                                    Wait for a user response using action=2
                                    Update ProgressBuffer using action=13
                Context Tree, the context tree that you see is only the path from root to the current node and the descendants of the current node.
                So if you want to see other parts of the context tree, you need to navigate there explicitly.

                Thinking vs Waiting:
                The user cannot see your thoughts, but you can use them to inform your next actions. 
                The user can see your responses, using action=2, that is the only way to yield control back to the user.

                Context policy: size > 800,000 — prioritize action=10 Replace (shorten node summaries, keep children) "
                and/or action=4 Prune (summarize and drop subtrees) until size < 800,000.

                Procedure Policy : - Plan -> Add Execution Nodes -> Execute -> Prune, Update Progress, loop.
                                   - If you are stuck prune that path and start over.
                                   - Use your context tree, wisely, parallelize and break down tasks. And switch between branches.
                                   - NOTE: Label the Planning node as BACKLOG PLAN, and the plan nodes as exec 1, exec 2 etc.
                                   - Follow the plan exactly, and then prune the subtree, by pruning the added node from the HEAD, when done with the section. This keeps the tree clean.
                                   - Progress Buffer is for your eyes only, use it to keep track of your progress, and update it frequently. Updating rewrites the file, so be careful not to lose information.
                                   - Progress Buffer is also stored in PROGRESS.md in the root of the workspace.
                                   - Progress Buffer should have a full checklist of the whole Plan in detail, including future plans.
                """
            )

            context_str = context_core + "\n" + policy_line + "\n" + self.context_tree.structure_string(self.context_tree.root, include_full=False, max_words=5, max_label_len=24) +  "Progress Buffer: " + self.progress_buffer.get_buffer() + "\n" + size_line
            print(size_line)
            try:
                llm_response = self.llm_client.generate_response(
                    input_text=context_str,
                    text_format=ResponseBody,
                    images=self.images)
            except Exception as e:
                # Prune HEAD context
                self.terminal.print_error_message(f" I have encountered an error: {e}")
                logger.error(f"LLM API error: {e}")
                continue

            # --- Minimal change: exit loop if LLM says finished=True ---
            if hasattr(llm_response, 'finished') and llm_response.finished:
                self.terminal.print_agent_message("Farewell. Goodbye!")
                logger.info("Session finished by semantic goodbye detected by LLM.")
                break

            # Delegate detailed action handling for testability
            self.process_llm_response(llm_response)
    def process_llm_response(self, llm_response: ResponseBody):
        action = llm_response.action
        ide_mode = True if getattr(self, "mode", "console") == "ide" else False

        # Common helper: attach label to a metadata dict if provided by the LLM
        def with_label(meta: dict) -> dict:
            try:
                lbl = getattr(llm_response, 'node_label', None)
            except Exception:
                lbl = None
            if lbl:
                meta = dict(meta) if not isinstance(meta, dict) else meta
                meta["label"] = lbl
            return meta

        if action == 0:  # File system read/write
            self.terminal.print_agent_message(f"Action Description: {llm_response.action_description}")
            file_action = llm_response.file_action
            file_name = llm_response.file_name
            if file_action == 0:  # Read
                self.terminal.print_agent_message(f"Reading file: {file_name}")
                file_content = self.file_system.read_file(file_name)
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata=with_label({"Result": file_content}),
                ))
                # Log AFTER the action
                logger.info(f"Read file: {file_name} for description: {llm_response.action_description}")
            else:
                self.terminal.print_agent_message(f"Writing file: {file_name}")
                write_content = llm_response.write_content
                self.file_system.write_file(file_name, write_content)
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata=with_label({"File Written": file_name, "Content": write_content}),
                ))
                logger.info(f"Wrote file: {file_name} for description: {llm_response.action_description}")

        elif action == 1:  # Shell command
            self.terminal.print_agent_message(f"Action Description: {llm_response.action_description}")
            self.terminal.print_agent_message(f"Executing shell command: {llm_response.shell_command}")
            shell_command = llm_response.shell_command
            stdout, stderr = self.shell.execute_command(shell_command)

            # Minimal, conservative handling of SYSTEM_BLOCK sentinel
            if isinstance(stderr, str) and stderr.startswith("SYSTEM_BLOCK:"):
                # Display System message in distinct color and log as warning
                system_msg = stderr.split(":", 1)[1].strip()
                self.terminal.print_system_message(system_msg)
                logger.warning(f"SYSTEM_BLOCK for command: {shell_command} | {system_msg}")

            self.context_tree.add_node(ContextNode(
                user_message=None,
                agent_response=str(llm_response),
                system_response="",
                metadata=with_label({
                    "Shell Command": shell_command,
                    "STDOUT": stdout,
                    "STDERR": stderr,
                })
            ))
            logger.info(f"Shell command executed: {shell_command} | STDOUT: {stdout.strip()[:200]} | STDERR: {stderr.strip()[:200]}")
        elif action == 2:  # Agent/user conversation
            self.terminal.print_agent_message(llm_response.response)
            # Only prompt with username in console mode; IDE provides its own input UI
            if not ide_mode:
                self.terminal.print_username()
            user_input = input()
            # Parse user-provided label and prefer it over LLM-provided node_label
            user_label, cleaned = parse_user_label(user_input)
            agent_response = llm_response.response
            metadata = {"label": user_label} if user_label else with_label({})
            self.context_tree.add_node(ContextNode(
                user_message=cleaned,
                agent_response=agent_response,
                system_response="",
                metadata=metadata,
            ))
            # Log only AFTER full dialogue turn
            logger.info(f"Agent response: {agent_response} | User replied: {cleaned}")
        
        elif action == 3:  # Diff insertion
            self.terminal.print_agent_message(f"Action Description: {llm_response.action_description}")
            self.terminal.print_agent_message(f"Inserting diff into file: {llm_response.file_name}")
            diff = llm_response.diff
            print(f"Diff to insert: {diff}")
            self.file_system.insert_diff(diff)
            self.context_tree.add_node(ContextNode(
                user_message=None,
                agent_response=str(llm_response),
                system_response="",
                metadata=with_label({"File Diff Inserted": llm_response.file_name, "Diff": str(diff)})
            ))
            logger.info(f"Diff inserted into file: {llm_response.file_name} | Diff: {diff}")

        elif action == 4:  # Prune context tree
            self.context_tree.prune(node_hash=llm_response.node_hash, replacement_val=llm_response.node_content)
            # Update the metadata of the current node
            if "pruned_nodes" in self.context_tree.head.metadata:
                self.context_tree.head.metadata["pruned_nodes"].append(llm_response.node_hash)
            else:
                self.context_tree.head.metadata["pruned_nodees"] = [llm_response.node_hash]

            self.terminal.print_agent_message(f"Pruned context tree node: {llm_response.node_hash}")
        
        elif action == 5:  # Change context HEAD
            previous_head = self.context_tree.head
            self.context_tree.head = self.context_tree._find_node(self.context_tree.root, llm_response.node_hash)
            self.terminal.print_agent_message(f"Changed context tree head to: {llm_response.node_hash}")
            self.context_tree.head.metadata = with_label({"Changed Context Head": llm_response.node_hash, "Previous Context Head": previous_head, "Change Summary": llm_response.node_content})
            logger.info(f"Changed context tree head to: {llm_response.node_hash}")

        elif action == 6:  # Add context node
            self.terminal.print_agent_message(f"Action Description: {llm_response.action_description}")
            parent_hash = getattr(llm_response, 'node_hash', None)
            node_content = getattr(llm_response, 'node_content', None)
            label = getattr(llm_response, 'node_label', None)
            if not node_content:
                node_content = getattr(llm_response, 'response', "") or ""
            new_meta = with_label({"added_via_action": 6, "Label": label if label else {}})
            new_node = ContextNode(
                user_message=None,
                agent_response=node_content,
                system_response="",
                metadata=new_meta
            )
            self.context_tree.add_node(new_node, parent_hash=parent_hash, advance_head=False)
            self.terminal.print_agent_message(f"Added context node under: {parent_hash or 'HEAD'}")
            # Update the metadata of the current node
            if "added_context_nodes" in self.context_tree.head.metadata:
                self.context_tree.head.metadata["added_context_nodes"].append(new_node.content_hash)
            else:
                self.context_tree.head.metadata["added_context_nodes"] = [new_node.content_hash]

            logger.info(f"Action 6: added context node under {parent_hash or 'HEAD'} | new node hash: {new_node.content_hash}")



        elif action == 7:  # Store Node in embedding DB
            embedding = self.llm_client.generate_embedding(llm_response.save_content)
            self.memory.store_node(
                embedding=embedding,
                content=llm_response.save_content
            )
            self.context_tree.add_node(ContextNode(
                user_message=None,
                agent_response=str(llm_response),
                system_response="",
                metadata=with_label({"Stored info to Memory": llm_response.save_content})
            ))
            logger.info(f"Stored information in memory: {llm_response.save_content} with node hash: {llm_response.node_hash}")
        elif action == 8:  # Retrieve Node from embedding DB
            embedding = self.llm_client.generate_embedding(llm_response.retrieve_content)
            retrieved_info = self.memory.retrieve_node(embedding)
            if retrieved_info:
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata=with_label({"Retrieved info from Memory": retrieved_info})
                ))
                logger.info(f"Retrieved information from memory: {retrieved_info}")

            else:
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata=with_label({"Retrieve failed": "No matching node found in memory"})
                ))
        elif action == 9:  # No operation
            # Add thoughts to current context
            if "thoughts" in self.context_tree.head.metadata:
                self.context_tree.head.metadata["thoughts"].append(llm_response.response)
            else:
                self.context_tree.head.metadata["thoughts"] = [llm_response.response]
            self.terminal.print_agent_message(f"Thinking about: {llm_response.response}")
            logger.info("No operation performed, waiting for next action.")
        elif action == 10:  # Replace context node (keep subtree)
            try:
                node_label = getattr(llm_response, 'node_label', None)
            except Exception:
                node_label = None
            ok = self.context_tree.replace(
                node_hash=llm_response.node_hash,
                replacement_val=llm_response.node_content,
                node_label=node_label
            )
            if ok:
                # Update the metadata of the current node
                if "replaced_context_nodes" in self.context_tree.head.metadata:
                    self.context_tree.head.metadata["replaced_context_nodes"].append(llm_response.node_hash)
                else:
                    self.context_tree.head.metadata["replaced_context_nodes"] = [llm_response.node_hash]

            status = "Replaced" if ok else "Replace failed (node not found)"
            self.terminal.print_agent_message(f"{status}: {llm_response.node_hash}")
            logger.info(f"Action 10: {status} | target={llm_response.node_hash}")

        elif action == 11:  # Rename context node
            label = getattr(llm_response, 'node_label', None)
            if not label:
                self.terminal.print_agent_message("Rename failed: no node_label provided.")
                logger.warning("Action 11: Rename failed, no node_label provided.")
            else:
                ok = self.context_tree.rename(
                    node_hash=llm_response.node_hash,
                    new_label=label
                )
                status = "Renamed" if ok else "Rename failed (node not found)"
                self.terminal.print_agent_message(f"{status}: {llm_response.node_hash} to '{label}'")
                if ok:
                    # Update the metadata of the current node
                    if "renamed_context_nodes" in self.context_tree.head.metadata:
                        self.context_tree.head.metadata["renamed_context_nodes"].append({"node_hash": llm_response.node_hash, "new_label": label})
                    else:
                        self.context_tree.head.metadata["renamed_context_nodes"] = [{"node_hash": llm_response.node_hash, "new_label": label}]
                logger.info(f"Action 11: {status} | target={llm_response.node_hash} to '{label}'")
        elif action == 12:  # Input an image file, convert it to base64
            img_str = self.file_system.read_img_as_base64(llm_response.file_name)
            self.images.append({"file_path": llm_response.file_name, "img_str": img_str})
            meta = {"file_name": llm_response.file_name, "img_str": img_str}
            self.context_tree.add_node(ContextNode(user_message=None, agent_response=str(llm_response), system_response="", metadata=meta))
            self.terminal.print_agent_message(f"Image {llm_response.file_name} processed successfully")

        elif action == 13:  # Update ProgressBuffer
            self.progress_buffer.write(llm_response.write_content)
            self.terminal.print_agent_message(f"ProgressBuffer updated.")
            self.context_tree.add_node(ContextNode(
                user_message=None,
                agent_response=str(llm_response),
                system_response="",
                metadata=with_label({"ProgressBuffer Updated": True})# Placeholder metadata
            ))
            logger.info(f"ProgressBuffer updated with content: {llm_response.write_content}")



