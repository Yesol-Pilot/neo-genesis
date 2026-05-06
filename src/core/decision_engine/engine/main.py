# -*- coding: utf-8 -*-
"""WhyLab Engine Entrypoint (CLI)."""

import argparse
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from engine.config import DEFAULT_CONFIG
from engine.orchestrator import Orchestrator

# New imports for API and Director
from fastapi import FastAPI
from engine.agents.director import LabDirector
from engine.agents.network import AgentNetwork # Assuming AgentNetwork is in engine.agents.network

# Initialize FastAPI app
app = FastAPI()

# Initialize Agents and Director globally for the API
agent_network = AgentNetwork()
lab_director = LabDirector()

# FastAPI Endpoints
@app.get("/system/director/agenda")
async def get_agenda():
    return lab_director.get_current_agenda()

@app.post("/system/director/agenda/next")
async def next_agenda():
    return lab_director.set_agenda() # Pick new random agenda

@app.get("/system/logs")
async def get_logs():
    return list(agent_network.logs)

def main():
    parser = argparse.ArgumentParser(description="WhyLab Causal Inference Engine")
    
    # 데이터 관련 인자
    parser.add_argument("--data", type=str, help="외부 CSV 데이터 파일 경로 (필수 아님)")
    parser.add_argument("--treatment", type=str, default="treatment", help="처치 변수(Treatment) 컬럼명")
    parser.add_argument("--outcome", type=str, default="outcome", help="결과 변수(Outcome) 컬럼명")
    parser.add_argument("--features", type=str, help="피처 컬럼 리스트 (콤마로 구분, 예: age,income)")
    
    # 실행 옵션
    parser.add_argument("--scenario", type=str, default="Scenario A", help="시나리오 이름 (리포트용)")
    parser.add_argument("--query", type=str, help="RAG: 분석 결과에 대해 질문합니다.")
    
    args = parser.parse_args()
    
    config = DEFAULT_CONFIG
    
    print("WhyLab Engine CLI Initializing...")

    # 1. RAG Query 모드
    if args.query:
        print(f"Query: {args.query}")
        try:
            from engine.rag.agent import RAGAgent
            agent = RAGAgent(config)
            
            # 지식 인덱싱 (최신 리포트 반영)
            print("indexing knowledge...")
            agent.index_knowledge()
            
            print("generating answer...")
            answer = agent.ask(args.query)
            print(f"\nAnswer:\n{answer}\n")
            return
        except ImportError:
            print("RAG Module Error: pip install chromadb sentence-transformers")
            sys.exit(1)
        except Exception as e:
            print(f"RAG Error: {e}")
            sys.exit(1)
    
    # 2. 외부 데이터 설정 적용
    if args.data:
        print(f"External Data Mode: {args.data}")
        config.data.input_path = args.data
        config.data.treatment_col = args.treatment
        config.data.outcome_col = args.outcome
        
        if args.features:
            config.data.feature_cols = [f.strip() for f in args.features.split(",")]
            print(f"Selected Features: {config.data.feature_cols}")
    else:
        print(f"Synthetic Data Mode: {args.scenario}")

    # 3. 파이프라인 실행
    orchestrator = Orchestrator(config)
    
    try:
        orchestrator.run_pipeline(scenario=args.scenario)
        print("Pipeline Completed Successfully via CLI.")
    except Exception as e:
        print(f"Pipeline Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
