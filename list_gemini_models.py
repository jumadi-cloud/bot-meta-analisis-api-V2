from langchain_google_genai import list_models

if __name__ == "__main__":
    models = list_models()
    for m in models:
        print(m)
