#!/usr/bin/env python3
"""Plan one Feishu row locally; Python 3.11+, no third-party dependencies.
No network, credentials, upload, update or delete.

Usage: python plan_feishu_sync.py --project-root PROJECT --request request.json
Use --request - (default) to read UTF-8 JSON from stdin. Output is UTF-8 JSON;
invalid input exits 2, valid plans (including conflicts) exit 0.

Request schema (all names below are exact):
  kind: "project" | "asset" | "segment" | "script"
  sync_key: nonempty stable business/revision key
  snapshot_complete: boolean; only true permits planning writes
  owned_fields: unique allowed column names, including "同步键"; includes any
    attachment columns being managed. The constants below define the whitelist.
  desired_fields: object of explicitly requested scalar/link values; missing
    keys mean untouched. "同步键" may be omitted, or must equal sync_key.
  remote_records: complete queried list of {record_id, sync_key, fields, files}
  baseline: optional {record_id, fields, files} from last confirmed sync
  local_files: optional [{field, path, role?}]; path is relative to project root.
Each remote/baseline files entry is {field, name, sha256?, file_token?}.
sha256 is 64 hexadecimal characters or null; token is a string or null. The
caller normalizes each attachment column to at most ONE CURRENT managed file;
history and extra user attachments must remain outside this input and be kept.
Unknown remote scalar/attachment columns (including user videos) are ignored.
Each local target field and optional role must be unique. Only supplied local
files are compared. Actual bytes are hashed; a supplied hash is not accepted.
Baseline fields/files may be partial; omitted entries are not a common baseline.

Output: {kind, sync_key, operations: [{op, record_id?, reason?, fields?,
  missing_fields?, field?, files?, uploads?, attachment_mode?, preserve_local?}]}.
op is create/update/noop/pull/conflict/inspect_remote/revision_required.
Create/update fields contain only requested changed scalar/link fields.
Uploads are {field,path,name,sha256,role?}, always append-only; they never imply
replacing an attachment array. Conflict/inspect_remote/revision_required blocks
ALL writes for this row. Pull describes remote values, not a cloud write, and
always sets preserve_local=true: retain local files/values before adopting any
remote state, including remote deletion. No baseline + differing scalar means
pull; differing actual attachments mean conflict and retain BOTH versions.
Same hash + real token skips. Empty local_files does not request bootstrap
downloads; the caller restores missing local files outside this planner.
An attachment or exact identity/link changed only locally needs a new
asset/segment/script revision row, including asset direction, space group and
type, script range/identity and the exact source script of a segment; project
index revisions may append. Script MD uses attachment field "剧本md文件" and
file role "screenplay_md". Remote removal is never blindly reuploaded.

Project "当前剧本" is the FULL set of adopted script-revision record IDs across
all episode/scene batches. Caller must read the full remote set and replace only
the intended batch, retaining unrelated current scripts; omit the field when it
is not being changed. Never send only the just-uploaded script as a partial set.
The planner checks this collection against the common baseline like any other
project field; it does not infer ranges or merge links automatically. Drafts,
unaccepted feedback and conflicted revisions must not enter this collection.
Publish confirmed script attachments/manifests before changing this pointer.

Example request (empty local_files is valid):
{"kind":"asset","sync_key":"P1:A1:v001","snapshot_complete":true,
 "owned_fields":["同步键","名称","图片资产"],
 "desired_fields":{"名称":"角色_林岚_基础_角色板_v001"},
 "remote_records":[],"local_files":[{"field":"图片资产","path":"a.png"}]}

This is a plan, not concurrency control. Caller must refresh the complete scoped
snapshot immediately before execution, recheck local hashes, execute serially,
preserve all existing attachment tokens/user fields, and confirm results before
saving a baseline. No CAS/lock or cross-device atomicity is claimed.
"""

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys

SCALARS = {
    "project": {"名称", "同步键", "项目ID", "协作约定", "修订ID", "生产负责人", "状态", "当前剧本"},
    "asset": {"名称", "同步键", "资产ID", "修订ID", "主体与别名", "类型", "方向",
              "空间组ID", "状态", "生产负责人", "任务ID", "所属项目", "来源A"},
    "segment": {"名称", "同步键", "段落ID", "修订ID", "段号", "状态", "所属项目", "关联资产", "来源剧本",
                "生产负责人", "任务ID"},
    "script": {"名称", "同步键", "剧本ID", "修订ID", "集场范围", "状态", "所属项目", "生产负责人"},
}
ATTACHMENTS = {"project": {"总索引md文件"},
               "asset": {"图片资产", "对应图片生成提示词md文件"},
               "segment": {"对应段落提示词md文件"},
               "script": {"剧本md文件"}}
MISSING = object()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(left, right):
    if left is MISSING or right is MISSING:
        return left is right
    return json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(
        right, sort_keys=True, ensure_ascii=False)


def file_map(items, allowed):
    require(isinstance(items, list), "files must be a list")
    result = {}
    for item in items:
        require(isinstance(item, dict) and isinstance(item.get("field"), str),
                "each remote/baseline file needs field")
        field = item["field"]
        if field not in allowed:
            continue
        require(field not in result, "duplicate current attachment field: " + field)
        require(isinstance(item.get("name"), str) and item["name"], "file needs name")
        sha, token = item.get("sha256"), item.get("file_token")
        require(sha is None or isinstance(sha, str) and re.fullmatch(r"[0-9a-fA-F]{64}", sha),
                "invalid sha256 for " + field)
        require(token is None or isinstance(token, str), "invalid file_token")
        result[field] = {"field": field, "name": item["name"],
                         "sha256": sha.lower() if sha else None, "file_token": token or None}
    return result


def local_files(items, root, allowed):
    require(isinstance(items, list), "local_files must be a list")
    result, roles = {}, set()
    for item in items:
        require(isinstance(item, dict) and set(item) <= {"field", "path", "role"},
                "local file accepts only field/path/role")
        field, relative, role = item.get("field"), item.get("path"), item.get("role")
        require(isinstance(field, str) and field in allowed, "attachment field is not owned/allowed")
        require(field not in result, "duplicate local attachment field: " + field)
        require(role is None or isinstance(role, str) and role and role not in roles,
                "invalid or duplicate local role")
        require(isinstance(relative, str) and relative and "\0" not in relative,
                "local path must be nonempty")
        win = PureWindowsPath(relative)
        require(not win.drive and not win.root and not Path(relative).is_absolute()
                and ".." not in win.parts and ":" not in relative,
                "unsafe relative path: " + relative)
        path = (root / relative.replace("\\", "/")).resolve(strict=True)
        require(path.is_relative_to(root) and path.is_file(), "file escapes root or is not a file")
        with path.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        result[field] = {"field": field, "path": path.relative_to(root).as_posix(),
                         "name": path.name, "sha256": sha}
        if role is not None:
            roles.add(role)
            result[field]["role"] = role
    return result


def plan(request, project_root):
    """Return a deterministic JSON-compatible plan; raise ValueError on bad input."""
    require(isinstance(request, dict), "request must be an object")
    require(set(request) <= {"kind", "sync_key", "snapshot_complete", "owned_fields",
                            "desired_fields", "remote_records", "baseline", "local_files"},
            "unknown request key")
    kind, key = request.get("kind"), request.get("sync_key")
    require(isinstance(kind, str) and kind in SCALARS, "invalid kind")
    require(isinstance(key, str) and key.strip(), "sync_key must be nonempty")
    require(type(request.get("snapshot_complete")) is bool, "snapshot_complete must be boolean")
    owned = request.get("owned_fields")
    require(isinstance(owned, list) and all(isinstance(x, str) for x in owned), "owned_fields must be strings")
    require(len(owned) == len(set(owned)) and "同步键" in owned
            and set(owned) <= SCALARS[kind] | ATTACHMENTS[kind], "invalid owned_fields whitelist")
    owned = set(owned)
    desired = request.get("desired_fields")
    require(isinstance(desired, dict) and set(desired) <= owned & SCALARS[kind], "desired_fields not allowed")
    require(desired.get("同步键", key) == key, "desired 同步键 differs from sync_key")
    root = Path(project_root).resolve(strict=True)
    require(root.is_dir(), "project root must be a directory")
    local = local_files(request.get("local_files", []), root, owned & ATTACHMENTS[kind])
    records, baseline = request.get("remote_records"), request.get("baseline")
    require(isinstance(records, list), "remote_records must be a list")
    matches = []
    for record in records:
        require(isinstance(record, dict) and isinstance(record.get("record_id"), str)
                and record["record_id"] and isinstance(record.get("sync_key"), str)
                and isinstance(record.get("fields"), dict) and isinstance(record.get("files"), list),
                "remote record needs record_id/sync_key/fields/files")
        if record["sync_key"] == key:
            require(record["fields"].get("同步键", key) == key, "remote sync_key mismatch")
            matches.append(record)
    if baseline is not None:
        require(isinstance(baseline, dict) and isinstance(baseline.get("record_id"), str)
                and baseline["record_id"] and isinstance(baseline.get("fields"), dict)
                and isinstance(baseline.get("files"), list), "baseline needs record_id/fields/files")
        require(baseline.get("sync_key", key) == key and baseline["fields"].get("同步键", key) == key,
                "baseline sync_key mismatch")
    operations = []
    result = {"kind": kind, "sync_key": key, "operations": operations}
    if not request["snapshot_complete"]:
        operations.append({"op": "inspect_remote", "reason": "snapshot_incomplete"})
        return result
    if len(matches) > 1:
        operations.append({"op": "conflict", "reason": "duplicate_sync_key"})
        return result
    if not matches:
        if baseline:
            operations.append({"op": "conflict", "reason": "remote_record_removed"})
        else:
            operations.append({"op": "create", "fields": dict(desired, 同步键=key),
                               "uploads": [local[x] for x in sorted(local)], "attachment_mode": "append"})
        return result
    remote = matches[0]
    rid = remote["record_id"]
    if baseline and baseline["record_id"] != rid:
        operations.append({"op": "conflict", "record_id": rid, "reason": "baseline_record_mismatch"})
        return result
    before = baseline["fields"] if baseline else {}
    remote_files = file_map(remote["files"], owned & ATTACHMENTS[kind])
    before_files = file_map(baseline["files"], owned & ATTACHMENTS[kind]) if baseline else {}
    changes, uploads = {}, []

    def event(op, reason, **payload):
        if op == "pull":
            payload["preserve_local"] = True
        operations.append(dict(op=op, record_id=rid, reason=reason, **payload))

    for field in sorted(desired):
        left, right, old = desired[field], remote["fields"].get(field, MISSING), before.get(field, MISSING)
        if field == "同步键" or same(left, right):
            continue
        if old is MISSING or same(left, old):
            payload = {"missing_fields": [field]} if right is MISSING else {"fields": {field: right}}
            event("pull", "no_common_baseline" if old is MISSING else "remote_field_changed", **payload)
        elif same(right, old):
            if kind != "project" and field in {"资产ID", "段落ID", "剧本ID", "修订ID", "所属项目", "来源A",
                                               "关联资产", "来源剧本", "集场范围", "方向", "空间组ID", "类型"}:
                event("revision_required", "existing_identity_or_link_changed", field=field)
            else:
                changes[field] = left
        else:
            event("conflict", "both_changed_field", field=field)
    for field in sorted(local):
        left, right, old = local[field], remote_files.get(field), before_files.get(field)
        if right and right["file_token"] and not right["sha256"]:
            event("inspect_remote", "remote_hash_unknown", field=field)
        elif right and right["file_token"] and left["sha256"] == right["sha256"]:
            continue
        elif not right or not right["file_token"]:
            if old:
                op = "pull" if old["sha256"] == left["sha256"] else "conflict"
                event(op, "remote_attachment_removed", field=field)
            elif right:
                event("inspect_remote", "remote_token_missing", field=field)
            else:
                uploads.append(left)
        elif not old or not old["sha256"]:
            event("conflict", "no_common_attachment_baseline", field=field, files=[right])
        elif left["sha256"] == old["sha256"]:
            event("pull", "remote_attachment_changed", files=[right])
        elif right["sha256"] != old["sha256"]:
            event("conflict", "both_changed_attachment", field=field)
        elif kind != "project":
            event("revision_required", "existing_attachment_changed", files=[left])
        else:
            uploads.append(left)
    if not any(x["op"] in {"conflict", "inspect_remote", "revision_required"} for x in operations):
        if changes or uploads:
            operations.append({"op": "update", "record_id": rid, "fields": changes,
                               "uploads": uploads, "attachment_mode": "append"})
    if not operations:
        event("noop", "already_current")
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    whitelist = "Allowed owned_fields (scalar/link; attachments):\n" + "\n".join(
        kind + ": " + ", ".join(sorted(SCALARS[kind])) + "; " + ", ".join(sorted(ATTACHMENTS[kind]))
        for kind in SCALARS)
    parser = argparse.ArgumentParser(description=__doc__, epilog=whitelist,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-root", required=True, help="Existing local project directory")
    parser.add_argument("--request", default="-", help="JSON path, or - for stdin")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig") if args.request == "-" else Path(args.request).read_text(encoding="utf-8-sig")
        request = json.loads(raw, object_pairs_hook=unique_object,
                             parse_constant=lambda value: require(False, "invalid JSON constant: " + value))
        result = plan(request, args.project_root)
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
