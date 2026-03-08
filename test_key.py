import google.genai as genai
import sys

def test_api_key(api_key):
    try:
        # Use the new SDK initialization
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Hello, this is a test.'
        )
        print("Success! The API key works.")
        print("Response:", response.text)
    except Exception as e:
        print("Error validating API key:", e)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        key = sys.argv[1]
    else:
        key = input("Enter API Key: ")
    test_api_key(key)
