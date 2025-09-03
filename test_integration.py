#!/usr/bin/env python3
"""
Integration test script for enhanced housing assistant
"""

def test_basic_functionality():
    print("🧪 Testing Basic Integration...")
    
    try:
        from agents.orchestrator_agent import orchestrator
        print("✅ Orchestrator loaded successfully")
        
        from core.mcp_context_manager import MCPContextManager
        context_manager = MCPContextManager()
        print("✅ MCP Context Manager initialized")
        
        from tools import initialize_rag_system
        rag_status = initialize_rag_system()
        print(f"✅ RAG System: {rag_status}")
        
        # Test basic conversation
        test_query = "I'm a Singapore citizen looking for housing grants"
        response = orchestrator(test_query)
        print(f"✅ Test query response: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    test_basic_functionality()