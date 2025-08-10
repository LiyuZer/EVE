'''
Agent interacts with three modular components-
    LLM interface for communicating with the GPT API 
    Shell interface, for executing commands on shell and receiving stderr and stdout
    File system for interacting with the file system, read and write to the file information 
'''
from dotenv import load_dotenv
import os
import sys
from src.schema import *
from src.prompt import *
from src.file_system import FileHandler
from src.shell import ShellInterface
from src.terminal import TerminalInterface
from src.llm import llmInterface
from src.memory import EveMemory  # Import Eve's memory for semantic storage
from src.logging_config import setup_logger  # Import improved logger setup
from src.context_tree import ContextTree, ContextNode

load_dotenv()
api_key_v = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")
username = os.getenv("USERNAME") or os.getenv("USER") or "friend"

# Initialize logger once; level is picked up from LOG_LEVEL env if set
logger = setup_logger("agent", "project.log")


class Agent:
    def __init__(self, root):
        self.llm_client = llmInterface(api_key=api_key_v, model=model)
        self.shell = ShellInterface()
        self.file_system = FileHandler()
        self.terminal = TerminalInterface(username=username)
        self.memory = EveMemory()
        self.root = root
        context_node = ContextNode(
            user_message="",
            agent_response="",
            system_response=base_prompt,
            metadata={"root directory": self.root}
        )
        self.context_tree = ContextTree(root=context_node)

    def start_execution(self):
        # Show EVE ASCII banner before anything else
        self.terminal.print_banner()

        self.terminal.print_welcome_message()
        self.terminal.print_username()
        user_input = input()
        self.context_tree.add_node(ContextNode(
            user_message=user_input,
            agent_response="",
            system_response="",
            metadata={}
        ))

        # Log initial user input AFTER user step
        logger.info(f"User input received: {user_input}")

        while True:
            context_str = str(self.context_tree)
            try:
                llm_response = self.llm_client.generate_response(
                    input_text=context_str,
                    text_format=ResponseBody)
            except Exception as e:
                # Prune HEAD context
                self.context_tree.prune(node_hash=self.context_tree.head.content_hash, replacement_val=f"<ERROR when executing plan: {e}>")
                self.context_tree.head = self.context_tree._find_node(self.context_tree.root, self.context_tree.head.content_hash)

                self.terminal.print_error_message(f" I have encountered an error: {e}")
                logger.error(f"LLM API error: {e}")
                continue

            action = llm_response.action

            # --- Minimal change: exit loop if LLM says finished=True ---
            if hasattr(llm_response, 'finished') and llm_response.finished:
                self.terminal.print_agent_message("Farewell. Goodbye!")
                logger.info("Session finished by semantic goodbye detected by LLM.")
                break

            if action == 0:  # File system read/write
                self.terminal.print_agent_message(f"Action Description: {llm_response.action_description}")
                file_action = llm_response.file_action
                file_name = llm_response.file_name
                if file_action == 0:  # Read
                    self.terminal.print_agent_message(f"Reading file: {file_name}")
                    file_content = self.file_system.read_file(file_name)
                    print(file_content)
                    self.context_tree.add_node(ContextNode(
                        user_message=None,
                        agent_response=str(llm_response),
                        system_response="",
                        metadata={"Result": file_content}
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
                        metadata={"File Written": file_name, "Content": write_content}
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
                    metadata={
                        "Shell Command": shell_command,
                        "STDOUT": stdout,
                        "STDERR": stderr,
                    }
                ))
                logger.info(f"Shell command executed: {shell_command} | STDOUT: {stdout.strip()[:200]} | STDERR: {stderr.strip()[:200]}")
            elif action == 2:  # Agent/user conversation
                self.terminal.print_agent_message(llm_response.response)
                self.terminal.print_username()
                user_input = input()
                agent_response = llm_response.response
                self.context_tree.add_node(ContextNode(
                    user_message=user_input,
                    agent_response=agent_response,
                    system_response="",
                    metadata={},
                ))
                # Log only AFTER full dialogue turn
                logger.info(f"Agent response: {agent_response} | User replied: {user_input}")
            elif action == 3:  # Diff insertion
                self.terminal.print_agent_message(f"Action Description: {llm_response.action_description}")
                self.terminal.print_agent_message(f"Inserting diff into file: {llm_response.file_name}")
                diff = llm_response.diff
                print(f"Diff to insert: {diff}")
                self.file_system.insert_diff(llm_response.file_name, diff)
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata={"File Diff Inserted": llm_response.file_name, "Diff": str(diff)}
                ))
                logger.info(f"Diff inserted into file: {llm_response.file_name} | Diff: {diff}")
            elif action == 4:  # Prune context tree
                self.context_tree.prune(node_hash=llm_response.node_hash, replacement_val=llm_response.node_content)
                self.context_tree.head = self.context_tree._find_node(self.context_tree.root, llm_response.node_hash)
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata={"Pruned Context Node": llm_response.node_hash}
                ))
            elif action == 5:  # Change context HEAD
                self.context_tree.head = self.context_tree._find_node(self.context_tree.root, llm_response.node_hash)
                self.terminal.print_agent_message(f"Changed context tree head to: {llm_response.node_hash}")
                # Add a Node to head
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata={"Changed Context Head": llm_response.node_hash}
                ))
                logger.info(f"Changed context tree head to: {llm_response.node_hash}")
            elif action == 6:  # Store Node in embedding DB
                embedding = self.llm_client.generate_embedding(llm_response.save_content)
                self.memory.store_node(
                    embedding=embedding,
                    content=llm_response.save_content                )
                self.context_tree.add_node(ContextNode(
                    user_message=None,
                    agent_response=str(llm_response),
                    system_response="",
                    metadata={"Stored info to Memory": llm_response.save_content}
                ))
                logger.info(f"Stored information in memory: {llm_response.save_content} with node hash: {llm_response.node_hash}")
            elif action == 7:  # Retrieve Node from embedding DB
                embedding = self.llm_client.generate_embedding(llm_response.retrieve_content)
                retrieved_info = self.memory.retrieve_node(embedding)
                if retrieved_info:
                    self.context_tree.add_node(ContextNode(
                        user_message=None,
                        agent_response=str(llm_response),
                        system_response="",
                        metadata={"Retrieved info from Memory": retrieved_info}
                    ))
                    logger.info(f"Retrieved information from memory: {retrieved_info}")

                else:
                    self.context_tree.add_node(ContextNode(
                        user_message=None,
                        agent_response=str(llm_response),
                        system_response="",
                        metadata={"Retrieve failed": "No matching node found in memory"}
                    ))