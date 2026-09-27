"""Investigate claims, exchange evidence, and compare with a sequential controller."""

import argparse
import fcntl
import json
import random
import statistics
from concurrent.futures import ThreadPoolExecutor

import core
import prompts
import schemas


def parallel(tasks):
    results, failures = {}, []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {key: pool.submit(fn) for key, fn in tasks.items()}
        for key, job in jobs.items():
            try:
                results[key] = job.result()
            except Exception as exc:
                failures.append(f"{key}: {exc}")
    if failures:
        raise core.Blocked("\n".join(failures))
    return results


def context(plan, history):
    return "\nPAPER INVESTIGATION MAP\n" + json.dumps(plan) + "\nCOMPLETE PRIOR NOTES\n" + json.dumps(history)


def generate_arm(protocol, pid, arm_name, plan, source):
    arm = core.ROOT / "work" / pid / arm_name
    if (arm / "generation.json").exists():
        return core.read(arm / "generation.json")
    history = {}
    serial = arm_name == "sequential_single"
    identity = ("You are one scientific reviewer continuing your investigation. All your earlier notes are supplied in full. You may correct them. Do not delegate.\n"
                if serial else "You are an independent investigator. Your findings will be challenged using manuscript evidence.\n")

    def invoke(stage, instruction, schema, prior):
        text = prompts.SAFETY + identity + instruction + "\nCOMPLETE MANUSCRIPT\n" + core.source_text(source) + context(plan, prior)
        active_tools = stage != "final"
        pdf = core.ROOT / "inputs" / pid / "manuscript.pdf"
        value = core.call(protocol, arm / stage, text, schema, source if active_tools else None, arm, pdf if active_tools else None)
        core.validate_evidence(value, source, core.receipts_in(arm) | core.receipts_in(arm.parent / "map"))
        core.write(arm / stage / "validated.json", value)
        return value

    def investigate(key, prior):
        instruction = prompts.INVESTIGATE + "\nASSIGNED WORK ORDER " + key + "\n" + plan["work_orders"][key]
        result = invoke("investigate_" + key, instruction, schemas.investigation(source), prior)
        for finding in result["findings"]:
            if not finding["text"].strip() or len(finding["text"].split()) > 160:
                raise core.Blocked("Candidate concern exceeds 160 words or is empty")
            if not finding["evidence_ids"]:
                raise core.Blocked("Candidate has no located manuscript evidence")
        return result

    core.write(core.ROOT / "status.json", {"stage": "investigating", "paper_id": pid, "arm": arm_name})
    if serial:
        for key in "ABC":
            history[key] = investigate(key, dict(history))
    else:
        history = parallel({key: lambda key=key: investigate(key, {}) for key in "ABC"})
    originals = {f"{key}{i}": row for key, result in history.items() for i, row in enumerate(result["findings"], 1)}
    core.write(arm / "original_findings.json", originals)
    defense_instruction = prompts.DEFEND
    if serial:
        defense_instruction += "\nCritically audit your own findings. Seek the strongest manuscript answer rather than defending your first interpretation.\n"
    else:
        defense_instruction += "\nYou are the manuscript defender responding to the independent investigators.\n"
    core.write(core.ROOT / "status.json", {"stage": "defense", "paper_id": pid, "arm": arm_name})
    defense = invoke("defense", defense_instruction + "\nCANDIDATES\n" + json.dumps(originals), schemas.defense(source, originals), history)
    history["defense"] = defense
    reply_instruction = prompts.REPLY
    reply_instruction += "\nResolve the objections from your own audit.\n" if serial else "\nYou represent the investigators and must respond to the defender's actual arguments.\n"
    core.write(core.ROOT / "status.json", {"stage": "reply", "paper_id": pid, "arm": arm_name})
    reply = invoke("reply", reply_instruction + "\nCANDIDATES\n" + json.dumps(originals), schemas.reply(source, originals), history)
    history["reply"] = reply
    cases = {key: row["final_concern"] for key, row in reply["replies"].items()}
    for value in cases.values():
        if not value["text"].strip() or len(value["text"].split()) > 160:
            raise core.Blocked("Reply concern exceeds 160 words or is empty")
    core.write(core.ROOT / "status.json", {"stage": "adjudication", "paper_id": pid, "arm": arm_name})
    final = invoke("final", prompts.FINAL + "\nFINAL CANDIDATES\n" + json.dumps(cases), schemas.final(source, cases), history)
    body = core.validate_final(final, cases, reply["replies"], source)
    (arm / "review.md").write_text(body + "\n")
    appendix = "\n\n".join(f"### {key}\n\n{cases[key]['text']}" for key in final["ranking"])
    (arm / "full_findings.md").write_text(appendix + "\n")
    result = {"arm": arm_name, "originals": originals, "cases": cases, "defense": defense,
              "reply": reply, "final": final, "final_words": len(body.split()),
              "receipts": sorted(core.receipts_in(arm)), "six_stages": True,
              "memory": "Full explicit notes carried between fresh CLI calls, hidden reasoning is not carried."}
    core.write(arm / "generation.json", result)
    return result


def generate(protocol, pid):
    out = core.ROOT / "work" / pid
    source = core.read(core.ROOT / "inputs" / pid / "source_chunks.json")
    core.write(core.ROOT / "status.json", {"stage": "reconstructing_claims", "paper_id": pid})
    text = prompts.SAFETY + prompts.MAP + "\nCOMPLETE MANUSCRIPT\n" + core.source_text(source)
    plan = core.call(protocol, out / "map", text, schemas.mapping(source))
    core.validate_evidence(plan, source, core.receipts_in(out / "map"))
    core.write(out / "map" / "validated.json", plan)
    arms = ["investigation_team", "sequential_single"]
    if core.read(core.ROOT / "manifest.json")["input_ids"].index(pid) % 2:
        arms.reverse()
    for arm in arms:
        generate_arm(protocol, pid, arm, plan, source)

