#!/usr/bin/env python3
"""Validate the explicit-only Agentic Engineering 4.0.0 package set."""

from __future__ import annotations

import json
import os
import secrets
import stat
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import yaml


PACKAGES = {
    "agentic-engineering": 8,
    "agentic-engineering-lifecycle": 10,
    "agentic-engineering-rust": 7,
    "agentic-engineering-systems": 5,
}
PACKAGE_SET_VERSION = "4.0.0"
POLICY_URLS = (
    "websiteURL",
    "privacyPolicyURL",
    "termsOfServiceURL",
)
PACK_SET_SCHEMA = "AgenticPackSet-v1"
GATEWAY = "external:harness-ultragoal"
PACKAGE_TOP_LEVEL = {".codex-plugin", "skills"}
MARKETPLACE_NAME = "agentic-engineering-local"
MARKETPLACE_SCHEMA_VERSION = "1.0"
MARKETPLACE_DISPLAY_NAME = "Agentic Engineering Local"
REQUIRED_CHECK_IDS = ("package-structure",)
CLAIM_STATES = {
    "structural_package": "observed",
    "host_install_discovery": "unobserved",
    "activation_abstention": "unobserved",
    "isolated_advice_value": "unobserved",
    "composition": "unobserved",
    "field_usefulness": "unobserved",
}


@dataclass(frozen=True)
class PackageInventory:
    name: str
    skills: tuple[str, ...]
    digest: str
    version: str = PACKAGE_SET_VERSION


@dataclass(frozen=True)
class Candidate:
    """A clean Git identity plus the exact inputs used by structural validation."""

    commit: str
    tree: str
    validation_input_digest: str


@dataclass(frozen=True)
class CheckResult:
    """One executed, structural-only check with its machine observations."""

    id: str
    status: str
    maximum_claim: str
    observations: dict[str, str]

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("check id must not be empty")
        if self.status != "passed":
            raise ValueError(f"{self.id}: only passed structural checks can be rendered")
        if self.maximum_claim != "structural":
            raise ValueError(f"{self.id}: structural release cannot claim behavioral efficacy")
        if not self.observations:
            raise ValueError(f"{self.id}: passed check requires observations")
        if any(
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            or not value.strip()
            for key, value in self.observations.items()
        ):
            raise ValueError(f"{self.id}: observations must be nonblank string pairs")


def repository_root(start: Path | None = None) -> Path:
    if start is not None:
        return start.resolve()
    return Path(__file__).resolve().parents[1]


def _git(root: Path, *arguments: str) -> str:
    """Run a read-only Git query rooted at the candidate repository."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("release candidate must be a readable Git checkout") from error
    return completed.stdout


def validation_input_paths() -> tuple[str, ...]:
    """Return every release input that must remain unchanged while it is checked."""
    return (
        *(f"plugins/{name}" for name in PACKAGES),
        ".agents/plugins/marketplace.json",
        "profiles/full.json",
        "profiles/ultragoal.json",
    )


def _regular_file_digest(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError(f"validation input must not be a symlink: {path}")
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"validation input must be a regular file: {path}")
    return sha256(path.read_bytes()).digest()


def validation_input_digest(root: Path | None = None) -> str:
    """Digest all release inputs, including untracked or ignored package material."""
    root = repository_root(root)
    entries: list[bytes] = [b"AgenticValidationInputs-v1"]
    for name in PACKAGES:
        package_root = root / "plugins" / name
        if not package_root.is_dir():
            raise ValueError(f"required package is missing: {name}")
        digest = package_manifest_digest(package_root)
        path = f"plugins/{name}".encode("utf-8")
        entries.append(len(path).to_bytes(8, "big") + path + digest.encode("ascii"))
    for relative in (
        ".agents/plugins/marketplace.json",
        "profiles/full.json",
        "profiles/ultragoal.json",
    ):
        encoded_path = relative.encode("utf-8")
        entries.append(
            len(encoded_path).to_bytes(8, "big")
            + encoded_path
            + _regular_file_digest(root / relative)
        )
    return f"sha256:{sha256(b''.join(entries)).hexdigest()}"


def _assert_clean_validation_inputs(root: Path) -> None:
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignored=matching",
        "--",
        *validation_input_paths(),
    )
    if status:
        raise ValueError("release validation inputs must be clean, including ignored files")


def _assert_clean_git_tree(root: Path) -> None:
    """Require all tracked candidate content to match the captured Git tree."""
    top_level = Path(_git(root, "rev-parse", "--show-toplevel").strip()).resolve()
    if top_level != root:
        raise ValueError("release candidate root must be the Git repository root")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ValueError("release candidate Git worktree must be clean")


def capture_candidate(root: Path | None = None) -> Candidate:
    """Capture an exact clean Git candidate before structural validation begins."""
    root = repository_root(root)
    _assert_clean_git_tree(root)
    _assert_clean_validation_inputs(root)
    return Candidate(
        commit=_git(root, "rev-parse", "HEAD").strip(),
        tree=_git(root, "rev-parse", "HEAD^{tree}").strip(),
        validation_input_digest=validation_input_digest(root),
    )


def verify_candidate(candidate: Candidate, root: Path | None = None) -> None:
    """Reject a check if the candidate identity or validation inputs changed."""
    root = repository_root(root)
    current = capture_candidate(root)
    if current != candidate:
        raise ValueError("release candidate changed after capture")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 4 or lines[0] != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("unterminated YAML frontmatter") from error
    try:
        values = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as error:
        raise ValueError("invalid YAML frontmatter") from error
    if not isinstance(values, dict) or set(values) != {"name", "description"}:
        raise ValueError("frontmatter must contain only name and description")
    if any(not isinstance(values[key], str) for key in values):
        raise ValueError("frontmatter values must be strings")
    return values


def package_manifest_digest(package_root: Path) -> str:
    entries: list[bytes] = []
    for path in sorted(package_root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"{package_root.name}: package contains symlink {path}")
        mode = path.stat().st_mode
        if path.is_dir():
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(
                f"{package_root.name}: package contains non-regular file {path}"
            )
        relative = path.relative_to(package_root).as_posix()
        if any(character in relative for character in ("\x00", "\n", "\r", "\t")):
            raise ValueError(
                f"{package_root.name}: package path contains a control character"
            )
        content = path.read_bytes()
        encoded_path = relative.encode("utf-8")
        entries.append(
            len(encoded_path).to_bytes(8, "big")
            + encoded_path
            + len(content).to_bytes(8, "big")
            + sha256(content).digest()
        )
    if not entries:
        raise ValueError(f"{package_root.name}: package manifest is empty")
    return f"sha256:{sha256(b''.join(entries)).hexdigest()}"


def safe_generated_output(root: Path, requested: Path) -> Path:
    """Resolve a report path inside the repository's ignored generated-output root."""
    root = Path(os.path.abspath(root))
    requested = Path(os.path.abspath(requested))
    allowed = root / "evals" / "results"
    try:
        relative = requested.relative_to(root)
    except ValueError as error:
        raise ValueError("output must stay inside the repository") from error
    if relative.parts[:2] != ("evals", "results") or len(relative.parts) < 3:
        raise ValueError("output must be a file under evals/results")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("output path must not contain symlinks")
    resolved = requested.resolve(strict=False)
    if allowed.resolve(strict=False) not in resolved.parents:
        raise ValueError("output must stay under evals/results")
    return resolved


def atomic_write_generated_json(root: Path, requested: Path, value: dict) -> Path:
    """Atomically write JSON beneath evals/results without following links."""
    output = safe_generated_output(root, requested)
    lexical_root = Path(os.path.abspath(root))
    relative = Path(os.path.abspath(requested)).relative_to(lexical_root)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    temporary_name: str | None = None
    try:
        descriptors.append(os.open(lexical_root, directory_flags))
        for part in relative.parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=descriptors[-1])
            except FileExistsError:
                pass
            descriptors.append(os.open(part, directory_flags, dir_fd=descriptors[-1]))
        parent = descriptors[-1]
        filename = relative.parts[-1]
        try:
            target = os.stat(filename, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            target = None
        if target is not None and stat.S_ISLNK(target.st_mode):
            raise ValueError("output path must not contain symlinks")
        payload = (json.dumps(value, indent=2) + "\n").encode("utf-8")
        temporary_name = f".{filename}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(
            temporary_name,
            filename,
            src_dir_fd=parent,
            dst_dir_fd=parent,
        )
        temporary_name = None
        os.fsync(parent)
        return output
    finally:
        if temporary_name is not None and descriptors:
            try:
                os.unlink(temporary_name, dir_fd=descriptors[-1])
            except FileNotFoundError:
                pass
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def package_inventory(root: Path, name: str) -> PackageInventory:
    package_root = root / "plugins" / name
    if not package_root.is_dir():
        raise ValueError(f"required package is missing: {name}")
    top_level = {path.name for path in package_root.iterdir()}
    if top_level != PACKAGE_TOP_LEVEL:
        raise ValueError(
            f"{name}: package root must contain only {sorted(PACKAGE_TOP_LEVEL)}; "
            f"found {sorted(top_level)}"
        )
    manifest = read_json(package_root / ".codex-plugin" / "plugin.json")
    if manifest.get("name") != name or manifest.get("version") != PACKAGE_SET_VERSION:
        raise ValueError(f"{name}: manifest identity is invalid")
    interface = manifest.get("interface")
    if not isinstance(interface, dict) or any(
        not isinstance(interface.get(key), str)
        or not interface[key].startswith("https://")
        for key in POLICY_URLS
    ):
        raise ValueError(f"{name}: policy URLs are incomplete")
    skills: list[str] = []
    for skill_dir in sorted((package_root / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        meta = frontmatter(skill_dir / "SKILL.md")
        if meta["name"] != skill_dir.name or not meta["description"].startswith(
            "Use when "
        ):
            raise ValueError(f"{name}: invalid skill trigger for {skill_dir.name}")
        agent_path = skill_dir / "agents" / "openai.yaml"
        try:
            agent = yaml.safe_load(agent_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ValueError(
                f"{name}: invalid agent YAML for {skill_dir.name}"
            ) from error
        expected_prompt = f"Use ${name}:{skill_dir.name} as an explicit advisory lens through {GATEWAY}."
        if (
            not isinstance(agent, dict)
            or set(agent) != {"interface", "policy"}
            or not isinstance(agent.get("interface"), dict)
            or not isinstance(agent.get("policy"), dict)
            or agent["interface"].get("default_prompt") != expected_prompt
            or agent["policy"].get("allow_implicit_invocation") is not False
        ):
            raise ValueError(f"{name}: {skill_dir.name} is not explicit-only")
        skills.append(skill_dir.name)
    return PackageInventory(
        name,
        tuple(skills),
        package_manifest_digest(package_root),
        manifest["version"],
    )


def validate_marketplace(root: Path) -> None:
    marketplace = read_json(root / ".agents" / "plugins" / "marketplace.json")
    if not isinstance(marketplace, dict):
        raise ValueError("marketplace document must be an object")
    if marketplace.get("schema_version") != MARKETPLACE_SCHEMA_VERSION:
        raise ValueError("marketplace schema version is invalid")
    if marketplace.get("name") != MARKETPLACE_NAME:
        raise ValueError("marketplace name is invalid")
    interface = marketplace.get("interface")
    if (
        not isinstance(interface, dict)
        or interface.get("displayName") != MARKETPLACE_DISPLAY_NAME
    ):
        raise ValueError("marketplace interface is invalid")
    entries = marketplace.get("plugins")
    if not isinstance(entries, list):
        raise ValueError("marketplace plugins must be a list")
    by_name = {
        entry.get("name"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    if set(by_name) != set(PACKAGES) or len(entries) != len(PACKAGES):
        raise ValueError("marketplace package set is invalid")
    for name, entry in by_name.items():
        if entry.get("source") != {
            "source": "local",
            "path": f"./plugins/{name}",
        }:
            raise ValueError(f"{name}: marketplace source is invalid")
        if entry.get("policy") != {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        }:
            raise ValueError(f"{name}: marketplace policy is invalid")
        if entry.get("category") != "Developer Tools":
            raise ValueError(f"{name}: marketplace category is invalid")


def validate(root: Path | None = None) -> tuple[PackageInventory, ...]:
    root = repository_root(root)
    validate_marketplace(root)
    inventories = tuple(package_inventory(root, name) for name in PACKAGES)
    counts = {inventory.name: len(inventory.skills) for inventory in inventories}
    if counts != PACKAGES:
        raise ValueError(f"package skill counts differ: {counts}")
    union = [skill for inventory in inventories for skill in inventory.skills]
    if len(union) != len(set(union)):
        raise ValueError("package skill union contains duplicates")
    full = read_json(root / "profiles" / "full.json")["enabled_skills"]
    if set(union) != set(full) or len(full) != 30:
        raise ValueError("package skill union does not equal the 30-skill full profile")
    base = set(read_json(root / "profiles" / "ultragoal.json")["enabled_skills"])
    base_inventory = next(
        (item for item in inventories if item.name == "agentic-engineering"),
        None,
    )
    if base_inventory is None or set(base_inventory.skills) != base:
        raise ValueError("base package does not equal the Ultragoal profile")
    return inventories


def render(inventories: Iterable[PackageInventory]) -> dict:
    entries = list(inventories)
    packs = [
        {
            "name": item.name,
            "version": item.version,
            "manifest_digest": item.digest,
            "enabled_skills": list(item.skills),
        }
        for item in entries
    ]
    aggregate = sha256(
        "\n".join(
            [PACK_SET_SCHEMA, GATEWAY]
            + [
                "\t".join(
                    [
                        pack["name"],
                        pack["version"],
                        pack["manifest_digest"],
                        ",".join(sorted(pack["enabled_skills"])),
                    ]
                )
                for pack in packs
            ]
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": PACK_SET_SCHEMA,
        "package_set_version": PACKAGE_SET_VERSION,
        "gateway": GATEWAY,
        "packs": packs,
        "aggregate_digest": f"sha256:{aggregate}",
        "skill_union": sorted(skill for item in entries for skill in item.skills),
    }


def _validate_check_results(checks: Iterable[CheckResult]) -> tuple[CheckResult, ...]:
    entries = tuple(checks)
    identifiers = tuple(check.id for check in entries)
    if identifiers != REQUIRED_CHECK_IDS:
        raise ValueError(
            "full release requires exactly these executed checks: "
            f"{list(REQUIRED_CHECK_IDS)}"
        )
    # Reconstructing validates caller-supplied subclasses or mutated objects too.
    for check in entries:
        CheckResult(check.id, check.status, check.maximum_claim, check.observations)
    return entries


def _validate_full_release_inventories(
    inventories: Iterable[PackageInventory],
) -> tuple[PackageInventory, ...]:
    entries = tuple(inventories)
    if tuple(item.name for item in entries) != tuple(PACKAGES):
        raise ValueError("full release requires the complete ordered package set")
    if any(item.version != PACKAGE_SET_VERSION for item in entries):
        raise ValueError("full release package versions disagree")
    counts = {item.name: len(item.skills) for item in entries}
    if counts != PACKAGES:
        raise ValueError("full release package skill counts disagree")
    union = [skill for item in entries for skill in item.skills]
    if len(union) != len(set(union)):
        raise ValueError("full release package skill identities contain duplicates")
    return entries


def render_release_result(
    candidate: Candidate,
    inventories: Iterable[PackageInventory],
    checks: Iterable[CheckResult],
) -> dict:
    """Render a machine-verifiable, structural-only full-release result."""
    executed_checks = _validate_check_results(checks)
    package_set = render(_validate_full_release_inventories(inventories))
    result = {
        "passed": True,
        "candidate": {
            "commit": candidate.commit,
            "tree": candidate.tree,
            "validation_input_digest": candidate.validation_input_digest,
        },
        "checks": [
            {
                "id": check.id,
                "status": check.status,
                "maximum_claim": check.maximum_claim,
                "observations": dict(sorted(check.observations.items())),
            }
            for check in executed_checks
        ],
        "claim_states": dict(CLAIM_STATES),
        "package_set": package_set,
    }
    validate_release_result(result)
    return result


def validate_release_result(result: dict) -> None:
    """Reject forged counts, unobserved passes, subsets, and claim inflation."""
    if "gates" in result or "check_count" in result:
        raise ValueError("release check counts are derived from checks, never reported")
    checks = result.get("checks")
    if not isinstance(checks, list):
        raise ValueError("release result must contain executed checks")
    if "executed_check_count" in result and result["executed_check_count"] != len(checks):
        raise ValueError("reported check count differs from executed checks")
    parsed: list[CheckResult] = []
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("release check must be an object")
        try:
            parsed.append(
                CheckResult(
                    check["id"],
                    check["status"],
                    check["maximum_claim"],
                    check["observations"],
                )
            )
        except KeyError as error:
            raise ValueError("release check is missing required evidence") from error
    _validate_check_results(parsed)
    if result.get("claim_states") != CLAIM_STATES:
        raise ValueError("release claim states must remain structural-only")
    package_set = result.get("package_set")
    if not isinstance(package_set, dict):
        raise ValueError("release result must contain the complete package set")
    packs = package_set.get("packs")
    if not isinstance(packs, list):
        raise ValueError("release result must contain package observations")
    try:
        rendered_names = tuple(pack["name"] for pack in packs)
        rendered_versions = tuple(pack["version"] for pack in packs)
        rendered_counts = {
            pack["name"]: len(pack["enabled_skills"]) for pack in packs
        }
    except (KeyError, TypeError) as error:
        raise ValueError("release result contains invalid package observations") from error
    if rendered_names != tuple(PACKAGES) or rendered_counts != PACKAGES:
        raise ValueError("release result does not contain the complete package set")
    if rendered_versions != (PACKAGE_SET_VERSION,) * len(PACKAGES):
        raise ValueError("release result package versions disagree")
    if package_set.get("package_set_version") != PACKAGE_SET_VERSION:
        raise ValueError("release result package-set version disagrees")


def run_structural_release(root: Path | None = None) -> dict:
    """Execute the complete structural-release scope against one frozen candidate."""
    root = repository_root(root)
    candidate = capture_candidate(root)
    inventories = validate(root)
    package_set = render(inventories)
    result = render_release_result(
        candidate,
        inventories,
        (
            CheckResult(
                id="package-structure",
                status="passed",
                maximum_claim="structural",
                observations={
                    "candidate_commit": candidate.commit,
                    "candidate_tree": candidate.tree,
                    "marketplace_contract_version": MARKETPLACE_SCHEMA_VERSION,
                    "package_count": str(len(inventories)),
                    "package_names": ",".join(item.name for item in inventories),
                    "package_set_digest": package_set["aggregate_digest"],
                    "package_set_version": PACKAGE_SET_VERSION,
                    "package_versions": ",".join(
                        f"{item.name}@{item.version}" for item in inventories
                    ),
                    "skill_count": str(sum(len(item.skills) for item in inventories)),
                    "validation_input_digest": candidate.validation_input_digest,
                },
            ),
        ),
    )
    verify_candidate(candidate, root)
    return result
