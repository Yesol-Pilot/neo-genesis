# -*- coding: utf-8 -*-
"""
소라(Sora) 멀티스텝 태스크 플래너 — Phase 2A + Phase 5B A2A 위임

복합 명령을 서브태스크로 분해하고 기존 도구를 순차 호출합니다.
도구가 없으면 A2A 프로토콜로 다른 에이전트에게 위임합니다.

흐름:
    [사용자 메시지] → is_multi_step? → [Gemini JSON 분해]
                                        → [위험도 평가]
                                        → [순차 실행 (도구 호출)]
                                        → [결과 종합 → 응답]
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("neo.jarvis")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 위험도 임계값 (mission_controller_v2.py 호환)
RISK_AUTO_EXECUTE = int(os.getenv("RISK_THRESHOLD_AUTO", "50"))
RISK_HITL_REQUIRED = int(os.getenv("RISK_THRESHOLD_HITL", "70"))

# 멀티스텝 감지 키워드
_MULTI_STEP_MARKERS = [
    "후에", "다음에", "그리고", "한 다음", "완료되면",
    "분석 후", "검토 후", "확인 후",
    "먼저", "그런 다음",
    "after", "then", "and then", "once done",
]

# 도구 이름 → 함수 매핑 (지연 로딩)
_tool_map: Optional[dict] = None


def _get_tool_map() -> dict:
    global _tool_map
    if _tool_map is None:
        from src.core.tools import ALL_TOOLS
        _tool_map = {t.__name__: t for t in ALL_TOOLS}
    return _tool_map


@dataclass
class SubTask:
    """서브태스크 단위"""
    step: int
    description: str
    tool_name: str
    tool_args: dict = field(default_factory=dict)
    risk: int = 0
    result: Optional[str] = None
    success: bool = False
    error: str = ""


@dataclass
class TaskPlan:
    """분해된 태스크 계획"""
    command: str
    intent: str = ""
    tasks: list[SubTask] = field(default_factory=list)
    risk_score: int = 0
    risk_category: str = "auto"  # "auto" | "debate" | "hitl"
    status: str = "planning"     # "planning" | "executing" | "completed" | "failed" | "blocked"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def summary(self) -> str:
        """실행 결과 요약 텍스트"""
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t.success)
        failed = sum(1 for t in self.tasks if t.result and not t.success)

        lines = [f"📋 **멀티스텝 실행 결과** ({done}/{total} 성공)"]
        lines.append(f"🎯 의도: {self.intent}")
        lines.append("")

        for t in self.tasks:
            icon = "✅" if t.success else ("❌" if t.result else "⏳")
            lines.append(f"{icon} Step {t.step}: {t.description}")
            if t.result:
                # 결과를 150자로 요약
                result_preview = t.result[:150]
                lines.append(f"   → {result_preview}")
            if t.error:
                lines.append(f"   ⚠️ {t.error[:100]}")

        if failed > 0:
            lines.append(f"\n⚠️ {failed}개 스텝 실패. 나머지는 정상 완료.")

        return "\n".join(lines)


class TaskPlanner:
    """복합 명령을 서브태스크로 분해 + 순차 실행"""

    def __init__(self):
        self._api_key = os.getenv("SORA_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
        self._model = os.getenv("SORA_GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._active_plan: Optional[TaskPlan] = None

    def is_multi_step(self, command: str) -> bool:
        """단일/멀티 판별 (키워드 + 길이 휴리스틱)"""
        cmd_lower = command.lower()

        # 키워드 기반
        for marker in _MULTI_STEP_MARKERS:
            if marker in cmd_lower:
                return True

        # 길이 기반 (80자 이상이고 동사가 2개 이상)
        verbs = ["해줘", "분석", "검색", "실행", "배포", "확인", "생성", "삭제",
                 "스캔", "인덱싱", "크롤링", "저장", "보고"]
        verb_count = sum(1 for v in verbs if v in cmd_lower)
        return verb_count >= 2 and len(command) > 60

    async def plan_and_execute(self, command: str, owner_approved: bool = False) -> TaskPlan:
        """메인 엔트리포인트: 분해 → 위험도 평가 → 실행 → 결과"""
        # 1) Gemini로 분해
        plan = await self._analyze(command)
        self._active_plan = plan

        # 2) 위험도 평가
        self._evaluate_risk(plan)
        logger.info(f"[Planner] 위험도: {plan.risk_score} → {plan.risk_category}")

        # 3) 위험도에 따른 실행
        if plan.risk_category == "hitl":
            plan.status = "blocked"
            logger.warning(f"[Planner] 고위험 ({plan.risk_score}) — HITL 필요")
            return plan

        # 자동 실행 또는 디베이트 통과
        plan.status = "executing"
        await self._execute_steps(plan, owner_approved=owner_approved)

        self._active_plan = None
        return plan

    def get_active_plan(self) -> Optional[TaskPlan]:
        """현재 진행 중인 계획"""
        return self._active_plan

    # ── 내부: Gemini 분해 ──

    async def _analyze(self, command: str) -> TaskPlan:
        """Gemini에게 명령을 서브태스크로 분해시킴"""
        tool_map = _get_tool_map()
        tool_names = list(tool_map.keys())

        prompt = f"""사용자 명령을 서브태스크로 분해하세요.

사용 가능한 도구:
{json.dumps(tool_names, ensure_ascii=False)}

명령: "{command}"

JSON만 출력 (마크다운 없이):
{{
  "intent": "명령의 핵심 의도 (한 줄)",
  "tasks": [
    {{
      "step": 1,
      "description": "무엇을 하는지 (한국어)",
      "tool_name": "사용할 도구 이름 (위 목록에서)",
      "tool_args": {{"arg1": "value1"}},
      "risk": 0
    }}
  ]
}}

규칙:
- tool_name은 반드시 위 목록에 있는 이름
- risk는 0-100 (데이터 삭제/배포 = 높음, 검색/조회 = 낮음)
- 일반 대화/질문은 단일 스텝으로"""

        result = await asyncio.to_thread(self._call_gemini_json, prompt)

        plan = TaskPlan(command=command)

        if result and "tasks" in result:
            plan.intent = result.get("intent", command)
            for t in result["tasks"]:
                tool_name = t.get("tool_name", "")
                # 도구 존재 검증
                if tool_name not in tool_map:
                    logger.warning(f"[Planner] 알 수 없는 도구: {tool_name}")
                    continue
                plan.tasks.append(SubTask(
                    step=t.get("step", len(plan.tasks) + 1),
                    description=t.get("description", ""),
                    tool_name=tool_name,
                    tool_args=t.get("tool_args", {}),
                    risk=t.get("risk", 0),
                ))
        else:
            # Gemini 실패 → 단일 태스크 폴백
            plan.intent = command
            logger.warning("[Planner] Gemini 분해 실패 → 단일 태스크 폴백")

        return plan

    # ── 내부: 위험도 평가 ──

    @staticmethod
    def _evaluate_risk(plan: TaskPlan):
        """위험도 종합 평가 (mission_controller_v2 호환)"""
        if not plan.tasks:
            plan.risk_score = 0
            plan.risk_category = "auto"
            return

        max_risk = max(t.risk for t in plan.tasks)
        plan.risk_score = max_risk

        if max_risk < RISK_AUTO_EXECUTE:
            plan.risk_category = "auto"
        elif max_risk >= RISK_HITL_REQUIRED:
            plan.risk_category = "hitl"
        else:
            plan.risk_category = "debate"

    # ── 내부: 순차 실행 ──

    async def _execute_steps(self, plan: TaskPlan, owner_approved: bool = False):
        """서브태스크 순차 실행"""
        tool_map = _get_tool_map()

        for task in plan.tasks:
            try:
                from src.core.governance.execution_gate import evaluate_tool_execution_gate

                func = tool_map.get(task.tool_name)
                if not func:
                    # Phase 5B: A2A 폴백
                    a2a_result = self._try_a2a_delegate(task)
                    if a2a_result:
                        task.result = a2a_result
                        task.success = True
                        continue
                    task.error = f"도구 '{task.tool_name}' 미등록 (위임도 실패)"
                    task.success = False
                    task.result = task.error
                    continue

                gate = evaluate_tool_execution_gate(task.tool_name, owner_approved=owner_approved)
                if not gate.allowed:
                    task.error = (
                        f"SEC-002/004/008 gate blocked {task.tool_name}: "
                        f"{gate.authority_tier} requires approval"
                    )
                    task.success = False
                    task.result = task.error
                    logger.warning("[Planner] %s", task.error)
                    continue

                logger.info(f"[Planner] Step {task.step}: {task.tool_name}({task.tool_args})")

                # 동기 도구를 스레드에서 실행
                result_str = await asyncio.to_thread(func, **task.tool_args)
                task.result = result_str
                task.success = True

                # JSON 파싱하여 에러 체크
                try:
                    parsed = json.loads(result_str)
                    if parsed.get("error"):
                        task.success = False
                        task.error = parsed["error"][:200]
                except (json.JSONDecodeError, TypeError):
                    pass

            except Exception as e:
                task.error = str(e)[:200]
                task.success = False
                task.result = f"실행 오류: {task.error}"
                logger.error(f"[Planner] Step {task.step} 실패: {e}")

        # 최종 상태
        success_count = sum(1 for t in plan.tasks if t.success)
        plan.status = "completed" if success_count == len(plan.tasks) else "failed"

    # ── 내부: Gemini JSON 호출 ──

    def _call_gemini_json(self, prompt: str):
        """Gemini API → JSON 파싱 (동기)"""
        if not self._api_key:
            return None
        try:
            import urllib.request
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000},
            }).encode()
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # 코드블록 제거
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            logger.error(f"[Planner] Gemini JSON 호출 실패: {e}")
            return None

    # ── Phase 5B: A2A 에이전트 위임 ──

    def _try_a2a_delegate(self, task: SubTask) -> Optional[str]:
        """미등록 도구일 때 A2A 프로토콜로 다른 에이전트에 위임"""
        try:
            from src.core.a2a_protocol import A2AProtocol
            a2a = A2AProtocol()

            # 스킬 기반 에이전트 검색
            matched_agent = a2a.find_agent_by_skill(task.tool_name)
            if not matched_agent:
                logger.debug(f"[Planner] A2A: '{task.tool_name}' 처리 가능 에이전트 없음")
                return None

            # A2A delegate(agent_id, task_dict) 호출
            handle = a2a.delegate(matched_agent, {
                "skill": task.tool_name,
                "description": task.description,
                "params": task.tool_args,
            })

            if handle and handle.status == "completed":
                logger.info(f"[Planner] A2A 위임 성공: {task.tool_name} → {matched_agent}")
                return str(handle.result)[:500] if handle.result else "완료"

            return None

        except Exception as e:
            logger.debug(f"[Planner] A2A 위임 실패: {e}")
            return None


# ── 싱글턴 ──

_planner: Optional[TaskPlanner] = None

def get_task_planner() -> TaskPlanner:
    global _planner
    if _planner is None:
        _planner = TaskPlanner()
    return _planner
