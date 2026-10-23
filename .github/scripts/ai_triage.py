#!/usr/bin/env python3
"""CI에서 테스트가 실패했을 때만 실행된다.

build/test-results/test/*.xml(JUnit 포맷)에서 실패한 테스트 이름과 메시지만 추려
Gemini API(무료 등급, 카드 등록 불필요)에 보내고, 한국어로 받은 분석을 PR 코멘트로 남긴다.
"""
import glob
import json
import os
import subprocess
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

RESULTS_GLOB = "auction-engine/build/test-results/test/*.xml"
MAX_DETAIL_LEN = 500
MAX_FAILURES = 10
MODEL = "gemini-3.8-flash"


def collect_failures():
    failures = []
    for path in sorted(glob.glob(RESULTS_GLOB)):
        root = ET.parse(path).getroot()
        for testcase in root.iter("testcase"):
            node = testcase.find("failure")
            if node is None:
                node = testcase.find("error")
            if node is None:
                continue

            classname = testcase.get("classname", "")
            name = testcase.get("name", "")
            detail = (node.get("message") or node.text or "").strip()
            if len(detail) > MAX_DETAIL_LEN:
                detail = detail[:MAX_DETAIL_LEN] + " ...(생략)"

            failures.append({"test": f"{classname}.{name}", "detail": detail})

    return failures[:MAX_FAILURES]


def call_gemini(failures):
    failure_lines = "\n".join(f"- {f['test']}: {f['detail']}" for f in failures)
    prompt = (
        "다음은 CI에서 실패한 JUnit 테스트 목록이다. 한국어로, 아래 형식에 맞춰 간결하게 답하라.\n\n"
        "## 실패한 테스트\n"
        "## 원인 추정\n"
        "## 수정 제안\n\n"
        f"실패 목록:\n{failure_lines}"
    )

    body = json.dumps({
        "systemInstruction": {
            "parts": [{"text": "너는 Spring Boot/JUnit 기반 백엔드 테스트 실패를 분석해주는 어시스턴트다."}]
        },
        "contents": [{"parts": [{"text": prompt}]}],
    }).encode("utf-8")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
        f"?key={os.environ['GEMINI_API_KEY']}"
    )
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def post_pr_comment(body):
    pr_number = os.environ["PR_NUMBER"]
    footer = "\n\n---\n🤖 AI 분석 결과이므로 사람이 확인 필요합니다."
    subprocess.run(
        ["gh", "pr", "comment", pr_number, "--body", body + footer],
        check=True,
    )


def main():
    failures = collect_failures()
    if not failures:
        print("JUnit XML에서 실패한 테스트를 찾지 못했습니다 - AI 분석을 건너뜁니다.")
        return

    try:
        analysis = call_gemini(failures)
    except urllib.error.HTTPError as e:
        print(f"Gemini API 호출 실패: {e.code} {e.read().decode(errors='ignore')}")
        raise

    post_pr_comment(analysis)


if __name__ == "__main__":
    main()
