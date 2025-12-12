import json
import os
import re
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

MODEL_NAME = "gpt-4.1-mini"

def get_product_price(product_name: str):
    # Dummy product catalog
    products = {
        "Redmi Note 10S 8GB/128GB": 1700,
        "iPhone 15": 1200,
        "Samsung S24": 1100,
        "MacBook Air": 1500,
        "AirPods Pro": 250,
        "Watch": None
    }

    price = products.get(product_name, None)

    if price is None:
        logger.warning(f"Price for '{product_name}' not found.")
        return f"Price for '{product_name}' not found."
    
    return f"The price of {product_name} is ${price}."

def get_stock_price(ticker: str):
    # Dummy stock database
    stocks = {
        "AAPL": 185.30,
        "GOOGL": 138.50,
        "MSFT": 402.20,
        "TSLA": 210.10
    }

    price = stocks.get(ticker, None)

    if price is None:
        logger.warning(f"Stock price for '{ticker}' not found.")
        return f"Stock price for '{ticker}' not found."

    return f"The current stock price of {ticker} is ${price}."


def calculate(expression: str) -> float:
    """Safely evaluate a basic math expression.

    Supports things like percentages and arithmetic, e.g. "15% of 2500".
    This is intentionally conservative: it only allows digits, spaces,
    basic operators, decimal points, parentheses and the percent sign.
    """

    # Simple normalization: "15% of 2500" -> "(15/100)*2500"
    normalized = expression.lower().strip()
    normalized = normalized.replace("% of", "/100 *")

    # Allow only safe characters
    if not re.fullmatch(r"[0-9+\-*/(). %]+", normalized):
        raise ValueError("Expression contains unsupported characters.")

    # Final safety: evaluate with empty globals/locals
    return eval(normalized, {"__builtins__": {}}, {})

# Tool Schemas (The "Menu" for the LLM)
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "name": "get_product_price",
        "description": "Get the price of a product from a predefined catalog.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name of the product to get the price for.",
                }
            },
            "required": ["product_name"],
        },
    },
    {
        "type": "function",
        "name": "get_stock_price",
        "description": "Get the current stock price for a given ticker symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol of the stock to get the price for.",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "type": "function",
        "name": "calculate",
        "description": "Safely evaluate a basic math expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate, e.g. '15% of 2500' or '3 * (4 + 5)'.",
                }
            },
            "required": ["expression"],
        },
    },
]

class PriceAgent:
    def __init__(self , max_retries: int = 2):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.history: List[Dict[str, Any]] = []
        self.max_retries = max_retries

    def _execute_tool(self, tool_call: Any) -> str:
        """Parses the LLM request and executes the corresponding Python function with retry."""
        retries = 0
        while retries <= self.max_retries:
            try:
                function_name = tool_call.name
                arguments = json.loads(tool_call.arguments)
                
                if function_name == "get_product_price":
                    return get_product_price(product_name=arguments.get("product_name"))
                elif function_name == "get_stock_price":
                    return get_stock_price(ticker=arguments.get("ticker"))
                elif function_name == "calculate":
                    result = calculate(expression=arguments.get("expression", ""))
                    return f"Result of '{arguments.get('expression', '')}' is {result}."
                else:
                    logger.warning(f"Error: Tool {function_name} not found.")
                    return f"Error: Tool {function_name} not found."
            
            except Exception as e:
                retries += 1
                logger.warning(f"Error executing tool '{tool_call.name}', attempt {retries}/{self.max_retries}: {e}")
                if retries > self.max_retries:
                    return f"Error: Failed to execute {tool_call.name} after {self.max_retries} retries."
                

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
                    "output" : tool_result
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
    agent = PriceAgent()
    agent.run(
        "Use your tools to answer. "
        "First, what is 69% of 69? "
        "Then, what is the price of Redmi Note 10S 8GB/128GB? "
        "And also, what is the stock price of TSLA?"
    )
