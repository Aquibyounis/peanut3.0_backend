import os
import json


KNOWLEDGE_PATH = "app/knowledge"


def load_json_files():

    documents = []

    print("\n========== LOADING JSON FILES ==========\n")

    print(
        f"Scanning path: {KNOWLEDGE_PATH}"
    )

    for root, _, files in os.walk(
        KNOWLEDGE_PATH
    ):

        print(f"\nROOT: {root}")

        print(f"FILES: {files}")

        for file in files:

            if not file.endswith(".json"):

                continue

            full_path = os.path.join(
                root,
                file
            )

            print(
                f"\nAttempting to load: {full_path}"
            )

            try:

                with open(
                    full_path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    data = json.load(f)

                    print(
                        f"SUCCESS: {file}"
                    )

                    documents.append(
                        {
                            "path": full_path,
                            "data": data
                        }
                    )

            except Exception as e:

                print(
                    f"FAILED: {file}"
                )

                print(e)

    print(
        f"\nTOTAL DOCUMENTS LOADED: {len(documents)}"
    )

    return documents