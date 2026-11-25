# SPDX-License-Identifier: GPL-3.0-only
"""Run a disposable SonarQube analysis with Docker and report all open issues."""

import argparse
import base64
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "tt-tool"
LOCAL_ADMIN = "admin"
SERVER_IMAGE = (
    "docker.io/library/sonarqube:26.11.0.134175-community"
    "@sha256:7b2296713a92b8ea0dd7a083a25faadc59376c9a1e6daf2744a89711c54ea1ba"
)
SCANNER_IMAGE = (
    "docker.io/sonarsource/sonar-scanner-cli:12.5.0.4351_8.5.0"
    "@sha256:8bb84373f00346f9a579adb7ccb2999f8cd050ab7167fa9ae08a16069de03c84"
)


def docker(*arguments, capture=False, env=None, timeout=600):
    return subprocess.run(
        ["docker", *arguments], capture_output=capture, encoding="utf-8",
        errors="replace", env=env, timeout=timeout, check=True,
    ).stdout


def basic_auth(login, password):
    value = base64.b64encode(f"{login}:{password}".encode()).decode()
    return f"Basic {value}"


def password_error_reason(response):
    try:
        result = json.loads(response.read(4096))
    except (OSError, ValueError):
        return ""
    if not isinstance(result, dict) or not isinstance(result.get("result"), str):
        return ""
    known = {
        "old_password_incorrect": "previous local administrator password rejected",
        "new_password_same_as_old": "new password matches the initial password",
        "Password must be at least 12 characters long": "new password is too short",
        "Password must contain at least one uppercase character": "new password needs an uppercase letter",
        "Password must contain at least one lowercase character": "new password needs a lowercase letter",
        "Password must contain at least one digit": "new password needs a digit",
        "Password must contain at least one special character": "new password needs a special character",
    }
    return known.get(result["result"], "")


def checkout_revision():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, encoding="ascii").strip()


def tracked_paths():
    paths = subprocess.check_output(["git", "ls-files", "-z", "--cached"], cwd=ROOT)
    return set(paths.decode("utf-8").split("\0")) - {""}


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SonarApi:
    def __init__(self, port):
        if type(port) is not int or not 0 < port <= 65535:
            raise ValueError("Invalid SonarQube loopback port")
        self.url = f"http://127.0.0.1:{port}"
        self.connection = build_opener(ProxyHandler({}), NoRedirects())
        self.authorization = ""

    def request(self, path, query=None, form=None):
        url = self.url + "/api/" + path
        if query:
            url += "?" + urlencode(query)
        headers = {"Accept": "application/json"}
        if self.authorization:
            headers["Authorization"] = self.authorization
        body = urlencode(form).encode() if form is not None else None
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=body, headers=headers)
        try:
            with self.connection.open(request, timeout=15) as response:
                content = response.read()
        except HTTPError as error:
            with error:
                if path == "system/status" and (error.code == 429 or error.code >= 500):
                    raise
                reason = password_error_reason(error) if path == "users/change_password" else ""
            detail = f" ({reason})" if reason else ""
            raise RuntimeError(f"SonarQube API /api/{path} returned HTTP {error.code}{detail}") from None
        return json.loads(content) if content else None

    def wait_until_ready(self):
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            try:
                if self.request("system/status")["status"] == "UP":
                    return
            except (URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(3)
        raise TimeoutError("The disposable SonarQube server did not become ready")

    def create_project(self):
        # SonarQube requires all four character classes, which a random token alone may omit.
        password = "Aa1!" + secrets.token_urlsafe(32)
        self.authorization = basic_auth(LOCAL_ADMIN, LOCAL_ADMIN)
        self.request("users/change_password", form={
            "login": LOCAL_ADMIN, "previousPassword": LOCAL_ADMIN, "password": password,
        })
        self.authorization = basic_auth(LOCAL_ADMIN, password)
        token = self.request("user_tokens/generate", form={"name": "tt-tool-ci"})["token"]
        self.authorization = f"Bearer {token}"
        self.request("projects/create", form={"project": PROJECT, "name": "tt tool", "visibility": "private"})
        return token

    def wait_for_analysis(self):
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            state = self.request("ce/component", {"component": PROJECT})
            if not state["queue"] and state.get("current"):
                task = state["current"]
                if task["status"] == "SUCCESS":
                    return task["analysisId"]
                raise RuntimeError(f"SonarQube compute task ended with {task['status']}")
            time.sleep(2)
        raise TimeoutError("SonarQube did not finish computing the analysis")

    def pages(self, route, key, query):
        results = []
        for page in range(1, 21):
            batch = self.request(route, {**query, "p": page, "ps": 500})
            results.extend(batch[key])
            if len(results) == batch["paging"]["total"]:
                return results
        raise RuntimeError(f"SonarQube returned an incomplete {key} report")


def cleanup(*arguments):
    try:
        docker(*arguments, capture=True, timeout=30)
    except (subprocess.SubprocessError, OSError):
        print(f"Could not clean up disposable Docker resource {arguments[-1]}")


def published_port(address):
    binding = re.fullmatch(r"127\.0\.0\.1:([0-9]{1,5})", address.strip())
    if binding and 0 < (port := int(binding[1])) <= 65535:
        return port
    raise RuntimeError("SonarQube is not bound to the expected IPv4 loopback port")


@contextmanager
def instance(memory=None, cpus=None):
    name = "tt-tool-sonar-" + uuid4().hex[:10]
    limits = []
    if memory:
        limits.extend(("--memory", memory))
    if cpus:
        limits.extend(("--cpus", str(cpus)))
    docker("network", "create", name, capture=True)
    try:
        docker(
            "run", "--detach", "--rm", "--name", name, "--network", name,
            "--publish", "127.0.0.1::9000", "--ulimit", "nofile=131072:131072",
            "--ulimit", "nproc=8192:8192", "--env", "SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true",
            *limits, SERVER_IMAGE,
        )
        try:
            port = published_port(docker("port", name, "9000/tcp", capture=True))
            yield name, SonarApi(port)
        except Exception:
            try:
                docker("logs", "--tail", "60", name, timeout=20)
            except (subprocess.SubprocessError, OSError):
                pass
            raise
    finally:
        cleanup("stop", "--time", "5", name)
        cleanup("network", "rm", name)


def scan(server, token, revision):
    environment = {**os.environ, "SONAR_TOKEN": token}
    docker(
        "run", "--rm", "--network", f"container:{server}",
        "--env", "SONAR_HOST_URL=http://127.0.0.1:9000", "--env", "SONAR_TOKEN",
        "--env", "SONAR_SCANNER_JAVA_OPTS=-Xmx512m",
        "--mount", f"type=bind,source={ROOT},target=/usr/src,readonly",
        SCANNER_IMAGE, "-Dsonar.working.directory=/tmp/tt-tool-scannerwork",
        f"-Dsonar.scm.revision={revision}",
        timeout=600, env=environment,
    )


def get_report(api, analysis_id):
    gate = api.request("qualitygates/project_status", {"analysisId": analysis_id})["projectStatus"]
    metrics = api.request("measures/component", {"component": PROJECT, "metricKeys": "files,ncloc"})
    measures = {item["metric"]: int(item["value"]) for item in metrics["component"]["measures"]}
    if not measures.get("ncloc", 0):
        raise RuntimeError("SonarQube did not analyze any source lines")
    issues = api.pages("issues/search", "issues", {"components": PROJECT, "resolved": "false"})
    hotspots = api.pages("hotspots/search", "hotspots", {"project": PROJECT, "status": "TO_REVIEW"})
    return {"quality_gate": gate, "measures": measures, "issues": issues, "hotspots_to_review": hotspots}


def location(item, paths):
    path = item.get("component", "").removeprefix(f"{PROJECT}:")
    rule = item.get("rule") or item.get("ruleKey", "")
    if path not in paths or not re.fullmatch(r"[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+", rule):
        return None
    line = item.get("line") or (item.get("textRange") or {}).get("startLine")
    severity = item.get("severity") or item.get("vulnerabilityProbability", "")
    status = item.get("issueStatus") or item.get("status", "")
    return {
        "path": path, "line": line if type(line) is int and line > 0 else 0, "rule": rule,
        "severity": severity if re.fullmatch(r"[A-Z_]{1,24}", severity) else "UNKNOWN",
        "status": status if re.fullmatch(r"[A-Z_]{1,24}", status) else "UNKNOWN",
    }


def public_gate(gate):
    return {
        "status": gate["status"],
        "ignored_conditions": bool(gate.get("ignoredConditions")),
        "conditions": [
            {
                key: value for key, value in condition.items()
                if key in {"metricKey", "status", "comparator", "errorThreshold", "actualValue"}
                and isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value)
            }
            for condition in gate.get("conditions", ())
        ],
    }


def gate_passes(report):
    gate = report["quality_gate"]
    # A fresh SonarQube project may have no gate conditions computed on its first scan.
    evaluated_ok = gate["status"] == "OK" or (gate["status"] == "NONE" and not gate.get("conditions"))
    return evaluated_ok and not report["issues"]


def write_report(directory, report, revision):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "sonar-findings.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    issues = report["issues"]
    gate = report["quality_gate"]["status"]
    hotspots = len(report["hotspots_to_review"])
    rules = Counter(item["rule"] for item in issues)
    paths = tracked_paths()
    locations = {
        key: [entry for item in report[key] if (entry := location(item, paths)) is not None]
        for key in ("issues", "hotspots_to_review")
    }
    (directory / "sonar-locations.json").write_text(json.dumps({
        "revision": revision,
        "quality_gate": public_gate(report["quality_gate"]),
        "line_zero_means_no_line": True,
        "locations": locations,
        "omitted_locations": {key: len(report[key]) - len(entries) for key, entries in locations.items()},
    }, indent=2) + "\n", encoding="utf-8")
    (directory / "sonar-summary.json").write_text(json.dumps({
        "revision": revision, "quality_gate": gate, "measures": report["measures"], "open_issues": len(issues),
        "open_issues_by_rule": dict(rules.most_common()), "hotspots_to_review": hotspots,
    }, indent=2) + "\n", encoding="utf-8")
    summary = [
        "## SonarQube",
        "",
        f"- Quality gate: **{gate}**",
        f"- Source lines analyzed: **{report['measures']['ncloc']:,}**",
        f"- Open issues: **{len(issues)}**",
        f"- Security hotspots to review separately: **{hotspots}**",
    ]
    if gate == "NONE" and not report["quality_gate"].get("conditions"):
        summary.append("- The first analysis had no evaluated gate conditions. The open-issue check still applies.")
    if rules:
        summary.extend(["", "| Rule | Open issues |", "| --- | ---: |"])
        summary.extend(f"| `{rule}` | {count} |" for rule, count in rules.most_common())
    text = "\n".join(summary) + "\n"
    if target := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(target).open("a", encoding="utf-8") as stream:
            stream.write(text)
    print(text, flush=True)
    print(f"Full findings: {directory / 'sonar-findings.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--server-memory", help="Optional Docker memory limit for the disposable server, e.g. 2500m")
    parser.add_argument("--server-cpus", type=float, help="Optional Docker CPU limit for the disposable server")
    parser.add_argument(
        "--report-only", action="store_true",
        help="Collect a baseline without treating existing findings as a failing exit status.",
    )
    args = parser.parse_args()
    revision = checkout_revision()
    with instance(args.server_memory, args.server_cpus) as (server, api):
        api.wait_until_ready()
        scan(server, api.create_project(), revision)
        report = get_report(api, api.wait_for_analysis())
    write_report(args.report_dir, report, revision)
    return 0 if gate_passes(report) or args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
