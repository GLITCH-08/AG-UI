from fastmcp import FastMCP
import subprocess
import asyncio

mcp = FastMCP()

@mcp.tool()
async def get_hostname() -> str:
    """
    Runs a system command to get the machine's hostname and returns it.
    """
    try:
        command = ["hostname"]
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error getting hostname: {str(e)}"
    
if __name__ == "__main__":
    mcp.run(transport="stdio") 