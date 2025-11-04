import os
from .modules import client_config, pipeline, export, evaluator, translator

def main():
    print("Initializing OpenAI client...")
    client_config.main()
    print("Running main pipeline...")
    #pipeline.main()
    print("Exporting results...")
    #export.main()
    print("Running evaluation...")
    #evaluator.main()
    run_translation = os.environ.get("RUN_TRANSLATION")
    if run_translation is None or run_translation == "1":
        print("Translation started...")
        translator.main()
    else:
        print("Translation skipped.")
    print("All steps completed.")

if __name__ == "__main__":
	main()
