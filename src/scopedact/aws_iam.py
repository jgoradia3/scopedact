from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Callable


class AwsIamReadOnlyTool:
    """Optional read-only AWS IAM connector backed by the AWS CLI.

    It accepts only `get_role` and one exact `iam-role:<name>` resource. ScopedAct
    must authorize the request before this object is called.
    """

    _ROLE_NAME = re.compile(r"^[A-Za-z0-9+=,.@_-]{1,64}$")
    tool_name = "tool:aws-iam-readonly"
    connector_name = "aws-iam"
    supported_actions = frozenset({"get_role"})

    def __init__(
        self,
        *,
        profile: str | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.profile = profile
        self.runner = runner

    def execute(self, action: str, resource: str) -> Any:
        command = self.command_for(action, resource)
        if shutil.which("aws") is None:
            raise RuntimeError("AWS CLI is not installed or not on PATH")
        result = self.runner(command, check=True, capture_output=True, text=True, timeout=30)
        body = json.loads(result.stdout)
        role = body.get("Role", {})
        return {"RoleName": role.get("RoleName"), "Arn": role.get("Arn"), "CreateDate": role.get("CreateDate"), "MaxSessionDuration": role.get("MaxSessionDuration")}

    def command_for(self, action: str, resource: str) -> list[str]:
        if action != "get_role":
            raise ValueError("AWS IAM connector permits only get_role")
        prefix = "iam-role:"
        if not resource.startswith(prefix):
            raise ValueError("AWS IAM resource must use iam-role:<name>")
        role_name = resource.removeprefix(prefix)
        if not self._ROLE_NAME.fullmatch(role_name):
            raise ValueError("invalid IAM role name")
        command = ["aws", "iam", "get-role", "--role-name", role_name, "--output", "json", "--no-cli-pager"]
        if self.profile:
            command.extend(["--profile", self.profile])
        return command

    def preflight(self) -> dict[str, Any]:
        if shutil.which("aws") is None:
            raise RuntimeError("AWS CLI is not installed or not on PATH")
        command=["aws","sts","get-caller-identity","--output","json","--no-cli-pager"]
        if self.profile: command.extend(["--profile",self.profile])
        result=self.runner(command,check=True,capture_output=True,text=True,timeout=30)
        body=json.loads(result.stdout)
        return {"Account":body.get("Account"),"Arn":body.get("Arn"),"UserId":body.get("UserId")}

    def health(self) -> dict[str, Any]:
        return {"status":"healthy","identity":self.preflight()}
