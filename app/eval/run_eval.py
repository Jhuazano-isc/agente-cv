import os
import httpx
from dotenv import load_dotenv
from app.eval.cases import EVAL_CASES

load_dotenv()

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")


def extract_text(data: dict) -> str:
    text = ""
    for item in data["output"]:
        if item["type"] == "message":
            for block in item["content"]:
                if block["type"] == "output_text":
                    text += block["text"]
    return text


def ask(question: str) -> str:
    payload = {
        "model": "placeholder",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": question}]}],
        "previous_response_id": None, 
    }
    resp = httpx.post(API_URL, headers={"Authorization": f"Bearer {API_KEY}"}, json=payload, timeout=30)
    resp.raise_for_status()
    return extract_text(resp.json())


def run():
    passed = 0
    failed = []

    for case in EVAL_CASES:
        answer = ask(case["question"])
        ok = True

        for keyword in case.get("must_include", []):
            if keyword.lower() not in answer.lower():
                ok = False

        for keyword in case.get("must_not_include", []):
            if keyword.lower() in answer.lower():
                ok = False

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['id']}")
        print(f"  Q: {case['question']}")
        print(f"  A: {answer[:150]}\n")

        if ok:
            passed += 1
        else:
            failed.append(case["id"])

    print(f"{passed}/{len(EVAL_CASES)} passed")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    run()