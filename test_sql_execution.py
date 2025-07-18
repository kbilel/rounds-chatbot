#!/usr/bin/env python3
"""
Test script to verify SQL execution with SQLAlchemy text() wrapper.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from ai.sql_engine import SQLGenerationEngine

def test_sql_execution():
    """Test that SQL execution works with the text() wrapper fix."""
    
    print("🧪 Testing SQL Execution Fix...")
    print("-" * 50)
    
    engine = SQLGenerationEngine()
    
    test_questions = [
        "How many apps do we have?",
        "Show me all app names",
        "What's our total revenue?"
    ]
    
    for question in test_questions:
        print(f"\n📝 Question: {question}")
        try:
            # This should now work with the text() wrapper
            result = engine.process_query(question)
            
            if result.get('success'):
                print(f"✅ Success! Found {result.get('result_count', 0)} results")
                if result.get('data'):
                    print(f"   Sample: {result['data'][:2]}")  # Show first 2 results
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print("\n" + "="*50)
    print("Test completed!")

if __name__ == "__main__":
    test_sql_execution() 