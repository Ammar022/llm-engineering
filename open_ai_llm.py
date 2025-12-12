import json
import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

load_dotenv()

MODEL_NAME = "gpt-5"

def get_horoscope(sign: str) -> str:
    """
    Mock function to retrieve a horoscope. 
    In a real app, this would hit an external API.
    """
    logger.info(f"Triggering tool 'get_horoscope' for sign: {sign}")
    return f"{sign}: Next Tuesday you will befriend a baby otter."

# Tool Schemas (The "Menu" for the LLM)
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "name": "get_horoscope",
        "description": "Get today's horoscope for an astrological sign.",
        "parameters": {
            "type": "object",
            "properties": {
                "sign": {
                    "type": "string",
                    "description": "An astrological sign like Taurus or Aquarius",
                },
            },
            "required": ["sign"],
        },
    },
]

class HoroscopeAgent:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.history: List[Dict[str, Any]] = []

    def _execute_tool(self, tool_call: Any) -> str:
        """Parses the LLM request and executes the corresponding Python function."""
        try:
            function_name = tool_call.name
            arguments = json.loads(tool_call.arguments)
            
            if function_name == "get_horoscope":
                return get_horoscope(sign=arguments.get("sign"))
            
            else:
                return f"Error: Tool {function_name} not found."
                
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return "Error: Failed to execute tool."

    def run(self, user_query: str):
        """Main orchestration loop."""
        
        # 1. Initialize conversation
        self.history.append({"role": "user", "content": user_query})
        logger.info(f"User Query: {user_query}")

        # 2. First Call: Reasoning & Tool Selection
        response = self.client.responses.create(
            model=MODEL_NAME,
            tools=AVAILABLE_TOOLS,
            input=self.history,
        )

        # Update history with the model's initial thought process
        self.history += response.output

        # 3. Check for Tool Calls
        for item in response.output:
            if item.type == "function_call":
                
                logger.info(f"Model requested tool: {item.name}")
                
                # Execute Logic
                tool_result = self._execute_tool(item)
                
                # Feed result back to the model
                self.history.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({"horoscope": tool_result})
                })

        # 4. Second Call: Final Synthesis
        # We instruct the model to just give the answer now that it has the data
        final_response = self.client.responses.create(
            model=MODEL_NAME,
            instructions="Respond naturally using the tool outputs provided.",
            tools=AVAILABLE_TOOLS,
            input=self.history,
        )

        # 5. Extract and display final text
        print("\n--- FINAL RESPONSE ---")
        print(final_response.output_text)
        print("----------------------\n")

if __name__ == "__main__":
    agent = HoroscopeAgent()
    agent.run("What is my horoscope? I am an Aquarius.")
