import json
import os
import re
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

load_dotenv()

MODEL_NAME = "gpt-4.1-mini"


class ProductPriceArgs(BaseModel):
    product_name: str
    reason: str | None = None


class StockPriceArgs(BaseModel):
    ticker: str
    reason: str | None = None


class CalculateArgs(BaseModel):
    expression: str
    reason: str | None = None

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
    """Safely evaluate a basic math expression."""
    # Simple normalization
    normalized = expression.lower().strip()

    # Handle 'a% of b'  -> '(a/100)*b'
    normalized = normalized.replace("% of", "/100 *")

    # Handle 'a% * b' or 'a%  b' -> '(a/100)*b'
    # e.g. '69% * 69' -> '(69/100)*69'
    match = re.fullmatch(r"\s*(\d+)\s*%\s*\*\s*(\d+)\s*", normalized)
    if match:
        a, b = match.groups()
        normalized = f"({a}/100)*{b}"

    # Allow only safe characters
    if not re.fullmatch(r"[0-9+\-*/(). %]+", normalized):
        raise ValueError("Expression contains unsupported characters.")

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
                },
                "reason": {
                    "type": "string",
                    "description": "Short explanation of why this tool is appropriate.",
                },
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
                },
                "reason": {
                    "type": "string",
                    "description": "Short explanation of why this tool is appropriate.",
                },
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
                },
                "reason": {
                    "type": "string",
                    "description": "Short explanation of why this tool is appropriate.",
                },
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
        """Parses the LLM request and executes one of the Python tools with validation and retry."""
        retries = 0
        while retries <= self.max_retries:
            try:
                function_name = tool_call.name
                raw_arguments = json.loads(tool_call.arguments or "{}")

                logger.info(f"Tool requested: {function_name} with raw args: {raw_arguments}")

                if function_name == "get_product_price":
                    args = ProductPriceArgs(**raw_arguments)
                    if args.reason:
                        logger.info(f"Model's reason for using get_product_price: {args.reason}")
                    result = get_product_price(product_name=args.product_name)

                elif function_name == "get_stock_price":
                    args = StockPriceArgs(**raw_arguments)
                    if args.reason:
                        logger.info(f"Model's reason for using get_stock_price: {args.reason}")
                    result = get_stock_price(ticker=args.ticker)

                elif function_name == "calculate":
                    args = CalculateArgs(**raw_arguments)
                    if args.reason:
                        logger.info(f"Model's reason for using calculate: {args.reason}")
                    calc_result = calculate(expression=args.expression)
                    result = f"Result of '{args.expression}' is {calc_result}."

                else:
                    logger.warning(f"Error: Tool {function_name} not found.")
                    return f"Error: Tool {function_name} not found."

                logger.info(f"Tool {function_name} executed successfully with result: {result}")
                return result

            except ValidationError as ve:
                retries += 1
                logger.warning(
                    f"Argument validation failed for '{tool_call.name}', "
                    f"attempt {retries}/{self.max_retries}: {ve}"
                )
                if retries > self.max_retries:
                    return f"Error: Invalid arguments for {tool_call.name}."

            except Exception as e:
                retries += 1
                logger.warning(
                    f"Error executing tool '{tool_call.name}', "
                    f"attempt {retries}/{self.max_retries}: {e}"
                )
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
    agent.run("what is the price of Redmi Note 10S 8GB/128GB?")
    agent.run("what is the stock price of TSLA?")
    agent.run("Calculate 69% of 69?")
