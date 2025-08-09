'''
Agent interacts with three modular components-
    LLM interface for communicating with the GPT API 
    Shell interface, for executing commands on shell and receiving stderr and stdout
    File system for interacting with the file system, read and write to the file information 
'''
from dotenv import load_dotenv
import os
import sys
import argparse
from schema import *
from prompt import *
from file_system import FileHandler
from shell import ShellInterface
from terminal import TerminalInterface
from llm import llmInterface
from logging_config import setup_logger  # Import improved logger setup

load_dotenv()
api_key_v = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")
username = os.getenv("USERNAME")

# Argument parser to accept -env flag
parser = argparse.ArgumentParser(description="Run the agent with specified environment mode.")
parser.add_argument("-env", type=str, default=None, help="Set environment mode: prod or debug (sets logger level)")
args = parser.parse_args()

def get_log_level_from_env(env_str: str):
    if env_str is None:
        return os.getenv("LOG_LEVEL", "INFO")
    env_str = env_str.strip().lower()
    if env_str in ["prod", "production", "personal"]:
        return "WARNING"
    if env_str in ["debug", "dev", "development"]:
        return "DEBUG"
    return "INFO"

log_level = get_log_level_from_env(args.env)
os.environ["LOG_LEVEL"] = log_level  # so logging_config picks it up

# Initialize logger once, with env-aware level
logger = setup_logger("agent", "project.log")

class Agent:
    def __init__(self):
        self.llm_client = llmInterface(api_key=api_key_v, model=model)
        self.shell = ShellInterface()
        self.file_system = FileHandler()
        self.terminal = TerminalInterface(username=username)
        self.context = [base_prompt]

    def start_execution(self):
        # Show EVE ASCII banner before anything else
        self.terminal.print_banner()

        self.terminal.print_welcome_message()
        self.terminal.print_username()
        user_input = input()
        self.context.append({username: user_input})

        # Log initial user input AFTER user step
        logger.info(f"User input received: {user_input}")

        while True:
            context_str = "\n".join([f"{key}: {value}" for item in self.context for key, value in item.items()])
            try: 
                llm_response = self.llm_client.generate_response(
                    input_text=context_str,
                    text_format=ResponseBody)
            except Exception as e:
                self.context.pop()
                self.context.append({"Error": str(e)})
                self.terminal.print_error_message(f" I have encountered an error: {e}")
                logger.error(f"LLM API error: {e}")
                continue
            
            self.context.append({"Action": llm_response.action})
            action = llm_response.action
            
            # --- Minimal change: exit loop if LLM says finished=True ---
            if hasattr(llm_response, 'finished') and llm_response.finished:
                self.terminal.print_agent_message("Farewell. Goodbye!")
                logger.info("Session finished by semantic goodbye detected by LLM.")
                break

            if action == 0: # File system read/write
                self.terminal.print_agent_message(f"Action Description: {llm_response.action_description}")
                file_action = llm_response.file_action
                file_name = llm_response.file_name
                if file_action == 0:  # Read
                    self.terminal.print_agent_message(f"Reading file: {file_name}")
                    file_content = self.file_system.read_file(file_name)
                    self.context.append({"File Read": file_content, "Action Description": llm_response.action_description})
                    # Log AFTER the action
                    logger.info(f"Read file: {file_name} for description: {llm_response.action_description}")
                else:
                    self.terminal.print_agent_message(f"Writing file: {file_name}")
                    write_content = llm_response.write_content
                    self.file_system.write_file(file_name, write_content)
                    self.context.append({"File Written": write_content, "File Name": file_name, "Action Description": llm_response.action_description})
                    logger.info(f"Wrote file: {file_name} for description: {llm_response.action_description}")

            elif action == 1: # Shell command
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
                
                self.context.append({
                    "Shell Command": shell_command, 
                    "STDOUT": stdout, 
                    "STDERR": stderr, 
                    "Action Description": llm_response.action_description})
                logger.info(f"Shell command executed: {shell_command} | STDOUT: {stdout.strip()[:200]} | STDERR: {stderr.strip()[:200]}")
            elif action == 2: # Agent/user conversation
                self.terminal.print_agent_message(llm_response.response)
                self.terminal.print_username()
                user_input = input()
                agent_response = llm_response.response
                self.context.append({"Agent Response": agent_response, "Agent Description": llm_response.action_description})
                self.context.append({username: user_input})
                # Log only AFTER full dialogue turn
                logger.info(f"Agent response: {agent_response} | User replied: {user_input}")

if __name__ == "__main__":
    agent = Agent()
    response = agent.start_execution()
