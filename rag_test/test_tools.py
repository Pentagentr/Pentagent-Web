"""
TOOL REGISTRY TEST SCRIPT

Tum tool'lari test eder ve hangilerinin calistigini rapor eder.
"""

import asyncio
import logging
import sys
import os

# Windows encoding fix
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

from mcp_server.tool_registry import get_tool_registry

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_tool_execution():
    """Test tool execution with sample params"""
    print("\n" + "="*70)
    print(">>> PENTAGENT TOOL EXECUTION TEST <<<")
    print("="*70 + "\n")
    
    # Get registry
    registry = get_tool_registry()
    
    # Registry status
    status = registry.get_status()
    print(f"[*] Registry Status:")
    print(f"   [+] Loaded Tools: {status['loaded_tools']}/{status['total_tools']}")
    print(f"   [+] Success Rate: {status['success_rate']:.1f}%")
    print(f"   [-] Failed Tools: {status['failed_tools']}")
    print()
    
    # Test target
    test_target = "example.com"
    
    # Test cases
    test_cases = [
        # Reconnaissance
        {
            "tool": "enum_tech_detector",
            "params": {"target": f"https://{test_target}"},
            "category": "Reconnaissance"
        },
        {
            "tool": "recon_whois_lookup",
            "params": {"target": test_target},
            "category": "Reconnaissance"
        },
        {
            "tool": "enum_port_scanner",
            "params": {"target": test_target, "ports": "80,443", "profile": "quick"},
            "category": "Reconnaissance"
        },
        
        # Vulnerability Scanning
        {
            "tool": "vuln_http_header_analyzer",
            "params": {"target": f"https://{test_target}"},
            "category": "Vulnerability Scanning"
        },
        
        # API Security
        {
            "tool": "api_vuln_jwt_tester",
            "params": {
                "target": test_target,
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
            },
            "category": "API Security"
        },
    ]
    
    # Run tests
    results = {
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    print(f"[*] Testing {len(test_cases)} tools...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        tool_name = test_case["tool"]
        params = test_case["params"]
        category = test_case["category"]
        
        print(f"[{i}/{len(test_cases)}] Testing {tool_name} ({category})...")
        
        try:
            # Execute tool
            result = await registry.execute_tool(tool_name, params)
            
            # Check result
            if result.get("success"):
                print(f"   [+] PASSED - Execution successful")
                results["passed"] += 1
                results["details"].append({
                    "tool": tool_name,
                    "status": "passed",
                    "execution_time": result.get("execution_time", 0)
                })
            else:
                error = result.get("error", "Unknown error")
                print(f"   [-] FAILED - {error}")
                results["failed"] += 1
                results["details"].append({
                    "tool": tool_name,
                    "status": "failed",
                    "error": error
                })
                
        except Exception as e:
            print(f"   [-] EXCEPTION - {str(e)}")
            results["failed"] += 1
            results["details"].append({
                "tool": tool_name,
                "status": "exception",
                "error": str(e)
            })
        
        print()
    
    # Summary
    print("="*70)
    print(">>> TEST SUMMARY <<<")
    print("="*70)
    print(f"[+] Passed: {results['passed']}/{len(test_cases)}")
    print(f"[-] Failed: {results['failed']}/{len(test_cases)}")
    
    success_rate = (results['passed'] / len(test_cases)) * 100 if test_cases else 0
    print(f"[*] Success Rate: {success_rate:.1f}%")
    print("="*70 + "\n")
    
    # Detailed results
    if results['failed'] > 0:
        print("[-] Failed Tools:")
        for detail in results['details']:
            if detail['status'] != 'passed':
                print(f"   [-] {detail['tool']}: {detail.get('error', 'Unknown')}")
        print()
    
    return results

async def list_all_tools():
    """List all available tools"""
    print("\n" + "="*70)
    print(">>> ALL AVAILABLE TOOLS <<<")
    print("="*70 + "\n")
    
    registry = get_tool_registry()
    tool_list = registry.get_tool_list_for_planner()
    
    # Group by category
    categories = tool_list.get("categories", {})
    
    for category, tools in sorted(categories.items()):
        if tools:
            print(f"[*] {category.upper().replace('_', ' ')} ({len(tools)} tools)")
            for tool in sorted(tools):
                metadata = registry.tool_metadata.get(tool, {})
                description = metadata.get("description", "No description")
                priority = metadata.get("priority", "unknown")
                print(f"   [+] {tool}")
                print(f"       --> {description} [{priority}]")
            print()
    
    print(f"[*] Total: {len(registry.tools)} tools loaded\n")

async def main():
    """Main test function"""
    try:
        # List all tools
        await list_all_tools()
        
        # Test execution
        results = await test_tool_execution()
        
        # Exit code based on results
        if results['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n[!] Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[-] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

