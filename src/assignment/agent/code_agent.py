"""The Part 1 coding agent: fix a software issue and submit a git patch."""

from __future__ import annotations

import json
from typing import Any

from assignment.agent.base import (
    DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
    DEFAULT_COMPACTION_MAX_TOKENS,
    Agent,
    format_tool_output
)
from assignment.agent.tools import EXECUTE_TOOL, SEND_MESSAGE_TOOL
from assignment.env import Environment

class CodeAgent(Agent):
    """An agent that fixes a software issue and submits a git patch."""

    def __init__(
        self,
        task: str,
        environment: Environment,
        model: str | None = None,
        logs_save_path: str | None = None,
        step_limit: int = 100,
        skills_path: str | None = None,
        auto_stop_environment: bool = True,
        compact_threshold_tokens: int | None = None,
        compaction_keep_recent_steps: int = DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
        compaction_max_tokens: int = DEFAULT_COMPACTION_MAX_TOKENS,
    ):
        super().__init__(
            environment=environment,
            model=model,
            logs_save_path=logs_save_path,
            step_limit=step_limit,
            skills_path=skills_path,
            auto_stop_environment=auto_stop_environment,
            compact_threshold_tokens=compact_threshold_tokens,
            compaction_keep_recent_steps=compaction_keep_recent_steps,
            compaction_max_tokens=compaction_max_tokens,
        )
        self.task = task
        self.submitted_patch = ""

        # TODO(Part 1.3): Make the `execute` and `send_message` tools available
        # to the agent.

        self.tools.extend([EXECUTE_TOOL, SEND_MESSAGE_TOOL])

        # TODO(1.1.b): Construct the system prompt and task_prompt. These
        # should be usable by the `Agent.build_prompt` method.

        self.system_prompt = f"""
            <system_information>
            {{
                "machine": "{environment.machine}",
                "release": "{environment.release}",
                "system": "{environment.system}",
                "version": "{environment.version}"
            }}
            </system_information>
        """

        self.task_prompt = task
        # TODO(1.4): If any skills are available to the agent, make their
        # descriptions/metadata available to the agent in the prompt.

        skill_metadata: str = ""
        if self.skills:  
            skill_metadata = "\n".join(skill["metadata"] for skill in self.skills.values())
            self.system_prompt += (
                "\n\nReusable skills are available below. "
                "The catalog contains each skill's name and description. "
                "Call `invoke_skill` with the `name` parameter set to a "
                "listed skill name to read its full instructions. "
                "Follow the instructions when using that skill."
                "\n\n<skills>\n"
                f"{skill_metadata}\n"
                "</skills>"
            )
            
        
  

#another implementation is that every tool has its own execute function
    def execute_tool_calls(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Execute ``execute`` and ``send_message`` calls in the code sandbox."""

        # TODO(Part 1.3): Parse each call, execute recognized tools, and return
        # one message per call (there may be multiple tool calls in one agent
        # response!). Malformed JSON and unknown tools must become recoverable
        # observations relayed to the agent instead of exceptions.

        observations: list[dict[str, str]] = []
        for tool in tool_calls:
            if self.finished:
                result = {"error": "Task already submitted; this call was not executed."}
            else:
                function = tool.get("function")
                if not isinstance(function, dict):
                    result = {"error": "function must be an object."}
                elif not isinstance(function.get("arguments"), str):
                    result = {"error": "arguments must be a JSON string."}
                else:
                    name = function.get("name")
                    try:
                        arguments = json.loads(function["arguments"])
                    except json.JSONDecodeError as exc:
                        result = {"error": f"Invalid JSON arguments: {exc.msg}"}
                    else:
                        if (not isinstance(arguments, dict)):
                            result = {"error": "Tool arguments must be a JSON object."}

                        elif (name == "execute"):
                            command = arguments.get("command")
                            valid_command = (
                                isinstance(command, str)
                                or (
                                    isinstance(command, list)
                                    and all(isinstance(item, str) for item in command)
                                )
                            )

                            if not valid_command:
                                result = {
                                    "error": "command is required and must be a string or a list of strings."
                                }
                            else:
                                cwd = arguments.get("cwd")
                                timeout = arguments.get("timeout")
                                env = arguments.get("env")
                                shell = arguments.get("shell")
                                result = self.env.execute(command = command, cwd = cwd, timeout = timeout, env = env, shell = shell)
                        
                        
                        elif (name == "send_message"):
                            summary = arguments.get("summary")
                            if (not isinstance(summary, str)):
                                result = {"error": "summary is required and must be a string"}

                            else:
                                print(summary)
                                self.finished = True
                                result = {"status": "submitted"}

                        elif (name == "invoke_skill"):
                            skill_name = arguments.get("name")
                            if not self.skills:
                                result = {
                                    "error": "No skills are available."
                                }
                            elif (
                                not isinstance(skill_name, str)
                                or not skill_name.strip()
                            ):
                                result = {
                                    "error": (
                                        "name is required and must be "
                                        "a non-empty string."
                                    )
                                }
                            elif skill_name not in self.skills:
                                result = {
                                    "error": f"Unknown skill: {skill_name}"
                                }
                            else:
                                observations.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tool.get("id"),
                                        "content": self.skills[skill_name]["content"],
                                    }
                                )
                                continue
                        else:
                            result = {"error": f"unknown_tool: {name}"}

                
            observations.append({"role": "tool", "tool_call_id": tool.get("id"), "content": format_tool_output(result)})
        return observations
                
