import sys
import requests
import json
import base64
import time
import difflib
import os
from urllib.parse import urlparse


def main():
    # loading environment variables
    github_token = load_env("GITHUB_TOKEN")
    etherscan_token = load_env("ETHERSCAN_TOKEN")
    contract_address = load_env("CONTRACT_ADDRESS")
    repo_link = load_env("REPO_LINK")

    # fetching contract code from Etherscan 
    response = requests.get(f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={contract_address}&apikey={etherscan_token}")
    if response.status_code != 200:
        print("🔴 [ERROR]: Request to api.etherscan.io failed!")
        sys.exit()

    data = response.json()
    if data['message'] == "NOTOK":
        print(f"🔴 [ERROR]: Etherscan {data['result']}!")
        sys.exit()

    # transforming source code to (contract_path, {"content": "code"}) format
    contracts = json.loads(data['result'][0]["SourceCode"][1:-1])["sources"].items()

    # parsing github link to get user repo and ref (commit or branch)
    (user_slash_repo, ref) = parse_repo_link(repo_link)

    for contract_path, code in contracts:
        print("* " * 30)
        print("Contract path:", contract_path)

        github_link = f"https://api.github.com/repos/{user_slash_repo}/contents/{contract_path}" + ("?ref" + ref if ref else "")

        if "@aragon" in contract_path:
            contract_path = contract_path.replace("@aragon/os/", "")
            github_link = f"https://api.github.com/repos/aragon/aragonOS/contents/{contract_path}" + ("?ref" + ref if ref else "")

        print(f"🔵 [INFO]: Fetching source code from {github_link}")

        github_response = requests.get(github_link, headers={"Authorization": f"token {github_token}"})
        github_data = github_response.json()
        contract_name = github_data.get("name")
        if not contract_name:
            print(f"🟠 [WARNING]: Failed to find {contract_path} in the repo!")
            continue

        encoded_source_code = github_data.get("content")
        if encoded_source_code:
            github_file_content = base64.b64decode(encoded_source_code).decode()

        time.sleep(1)

        github_code_lines = github_file_content.splitlines()
        etherscan_code_lines = code['content'].splitlines()

        diffs = difflib.unified_diff(github_code_lines, etherscan_code_lines)
        if len(list(diffs)):
            diff_html = difflib.HtmlDiff().make_file(github_code_lines, etherscan_code_lines)
            filename = f"diffs/{contract_name}.html"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w") as f:
                f.write(diff_html)
            print(f"🟠 [WARNING]: Diffs found in {contract_name}! More details in {filename}")
        else:
            print(f"🟢 [SUCCESS]: No diffs found in {contract_name}!")


def load_env(variable_name):
    value = os.getenv(variable_name)
    if not value:
        print(f"🔴 [ERROR]: `{variable_name}` unset!")
        sys.exit()

    return value


def parse_repo_link(repo_link):
    parse_result = urlparse(repo_link)
    repo_location = [item.strip("/") for item in parse_result[2].split("tree")]
    user_slash_repo = repo_location[0]
    ref = repo_location[1] if len(repo_location) > 1 else None
    return (user_slash_repo, ref)




if __name__ == "__main__":
    main()

