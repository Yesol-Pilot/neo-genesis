"""Generate the left-support AiNo weekly content pack.

This is a local artifact generator. It does not upload, schedule, publish, or
call external media providers.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "tiktok_aino_weekly_content_pack_20260524"

COMMON_HASHTAGS = ["정치", "시사", "뉴스", "팩트체크", "이슈정리", "올바른AiNo"]
BASE_STYLE = (
    "photorealistic cinematic Korean editorial satire still, vertical 9:16, "
    "realistic lighting, 35mm documentary lens, clean high-contrast news mood"
)
NEGATIVE_VISUAL = (
    "No real politician likeness, no party logo, no readable fake document text, "
    "no real news-channel UI, no ballot instruction, no public figure endorsement, "
    "no gore, no horror. Leave clean safe area for Korean overlay text."
)


SOURCES = {
    "tiktok_rewards": {
        "name": "TikTok Creator Rewards Program",
        "url": "https://newsroom.tiktok.com/introducing-the-new-creator-rewards-program/?lang=en",
        "note": "1분 이상 원본성, 재생시간, 검색가치, 참여 신호 기준",
    },
    "tiktok_search": {
        "name": "TikTok Creator Search Insights",
        "url": "https://newsroom.tiktok.com/creator-search-insights?lang=en",
        "note": "검색 수요와 콘텐츠 갭 기반 주제 선정",
    },
    "tiktok_aigc": {
        "name": "TikTok AIGC guidance",
        "url": "https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content?invalid_lang=es-419",
        "note": "현실적인 AI 이미지·오디오·영상 라벨링",
    },
    "tiktok_integrity": {
        "name": "TikTok Integrity and Authenticity Guidelines",
        "url": "https://www.tiktok.com/community-guidelines/en/integrity-authenticity",
        "note": "선거 허위정보, 미확인 선거 주장, 유료 정치광고 제한",
    },
    "realmeter": {
        "name": "서울신문 리얼미터 2026-05-18",
        "url": "https://www.seoul.co.kr/news/politics/president/2026/05/18/20260518500044",
        "note": "이재명 대통령 긍정 60.5%, 민주당 45.8%, 국민의힘 33.5% 보도",
    },
    "nbs": {
        "name": "동아일보 NBS 2026-05-21",
        "url": "https://www.donga.com/news/Politics/article/all/20260521/133966825/1",
        "note": "민주당 45%, 국민의힘 20% 보도",
    },
    "gallup": {
        "name": "동아일보 한국갤럽 2026-05-22",
        "url": "https://www.donga.com/news/Politics/article/all/20260522/133976023/1",
        "note": "이재명 대통령 직무 긍정 64%, 민주 45%, 국힘 22% 보도",
    },
    "starbucks_donga": {
        "name": "동아일보 스타벅스 5·18 논란 2026-05-20",
        "url": "https://www.donga.com/news/Society/article/all/20260520/133961880/2",
        "note": "탱크데이 논란, 서재페 부스 취소, 사과 관련 보도",
    },
    "starbucks_newspim": {
        "name": "뉴스핌 서울시장 후보 스타벅스 공방 2026-05-24",
        "url": "https://www.newspim.com/news/view/20260524000096",
        "note": "오세훈·정원오 서울시장 선거와 스타벅스 논란 공방",
    },
    "yoon_perjury": {
        "name": "다음/리걸타임즈 윤석열 위증 선고 일정 2026-04-16",
        "url": "https://v.daum.net/v/20260416174623795",
        "note": "한덕수 재판 위증 혐의, 징역 2년 구형, 5월 28일 선고 보도",
    },
    "ilbe_memorial": {
        "name": "서울신문 노무현 추도식 일베 포즈 논란 2026-05-24",
        "url": "https://www.seoul.co.kr/news/society/2026/05/24/20260524500009",
        "note": "고 노무현 전 대통령 추도식 당일 봉하 기념관 일베 포즈 논란",
    },
    "residence_seoul": {
        "name": "서울신문 관저 이전 의혹 구속영장 2026-05-19",
        "url": "https://www.seoul.co.kr/news/society/law/2026/05/20/20260520010004",
        "note": "관저 이전 공사 특혜 의혹 관련 구속영장 청구 보도",
    },
    "residence_mbc": {
        "name": "MBC 관저 이전 구속 및 윗선 수사 2026-05-23",
        "url": "https://imnews.imbc.com/replay/2026/nwtoday/article/6824712_37013.html",
        "note": "관저 이전 의혹 관련 구속 및 윗선 수사 보도",
    },
    "seoul_race": {
        "name": "뉴스토마토 서울시장 초접전 2026-05-22",
        "url": "https://www.newstomato.com/ReadNews.aspx?no=1301814",
        "note": "정원오·오세훈 0.1%p 차 초접전 조사 보도",
    },
}


POSTS = [
    {
        "date": "2026-05-25",
        "time": "08:10",
        "format": "growth_short",
        "topic": "지지율 60%대인데, 왜 민주당은 불안해야 하나",
        "title": "지지율 60%대, 그래도 방심하면 안 되는 이유",
        "thesis": "대통령 지지율이 높아도 정당 지지율, 보수 결집, 지역 이탈은 별도의 위험 신호다.",
        "hook": "숫자는 높습니다. 그런데 안심할 판은 아닙니다.",
        "why": "대통령 지지율은 60%대지만, 정당 지지율과 지역 흐름은 더 복잡합니다.",
        "fact": "리얼미터 보도는 이재명 대통령 긍정 60.5%, 민주당 45.8%, 국민의힘 33.5%를 전했습니다.",
        "conflict": "진보층은 안정론을 보고, 보수층은 결집 신호를 봅니다.",
        "evidence": "갤럽 보도도 대통령 직무 긍정 64%와 민주 45%, 국힘 22%를 함께 보여줍니다.",
        "counter": "보수 반론은 대통령 지지율과 지방선거는 다르다는 겁니다.",
        "rebuttal": "맞습니다. 그래서 더 위험합니다. 높은 지지율이 방심으로 바뀌는 순간 댓글장과 투표장은 다르게 움직입니다.",
        "choice": "1 안심해도 된다, 2 방심하면 흔들린다. 어디에 가깝습니까?",
        "cta": "올바른 AiNo는 숫자 뒤의 흐름을 계속 추적합니다. 다음 편까지 보려면 팔로우하세요.",
        "hashtags": ["이재명", "지지율", "민주당", "국민의힘", "지방선거", "여론조사"],
        "sources": ["realmeter", "gallup", "tiktok_rewards", "tiktok_integrity"],
        "visual_anchor": "split election war room with glowing poll boards, blue side confident and red side reorganizing",
        "comment_trigger": "지지율 높으면 안심해도 될까요, 아니면 이럴수록 더 조심해야 할까요?",
    },
    {
        "date": "2026-05-25",
        "time": "11:20",
        "format": "reward_deep",
        "topic": "스타벅스 5·18 논란, 커피 문제가 아닌 이유",
        "title": "스타벅스 5·18 논란, 커피 문제가 아닙니다",
        "thesis": "쟁점은 불매 자체가 아니라 역사 기억을 마케팅 언어에 올린 책임이다.",
        "hook": "이건 커피 취향 문제가 아닙니다. 기억을 어디까지 팔아도 되는가의 문제입니다.",
        "why": "5·18 기념일에 탱크데이 문구가 겹치며 논란이 커졌고, 서울재즈페스티벌 부스 운영도 취소됐습니다.",
        "fact": "동아일보는 탱크데이 논란, 서재페 부스 취소, 정용진 회장의 사과를 보도했습니다.",
        "conflict": "진보층은 역사 조롱으로 보고, 보수 쪽은 과도한 정치화라고 반박합니다.",
        "evidence": "뉴스핌 보도에 따르면 서울시장 선거판에서도 이 논란은 후보 간 공방으로 이어졌습니다.",
        "counter": "보수 반론은 기업이 사과했으면 그 정도로 끝낼 일이라는 주장입니다.",
        "rebuttal": "하지만 질문은 남습니다. 역사적 상처를 건드린 마케팅이 단순 실수라면, 왜 책임 기준은 늘 흐려집니까?",
        "choice": "1 단순 실수, 2 역사 조롱, 3 정치 과잉. 어디입니까?",
        "cta": "이 쟁점은 댓글에서 갈릴 수밖에 없습니다. 반론까지 남겨주세요. 팔로우하면 다음 쟁점을 이어갑니다.",
        "hashtags": ["스타벅스", "518민주화운동", "탱크데이", "역사인식", "불매", "서울시장"],
        "sources": ["starbucks_donga", "starbucks_newspim", "tiktok_aigc", "tiktok_integrity"],
        "visual_anchor": "empty festival coffee booth with covered sign, rain-slick floor, remembrance-colored light in background",
        "comment_trigger": "기업 사과로 끝낼 일인가요, 아니면 역사 기억의 책임을 더 물어야 하나요?",
    },
    {
        "date": "2026-05-25",
        "time": "19:30",
        "format": "debate_followup",
        "topic": "오세훈의 이 정도면 됐다, 진짜 쟁점은 뭔가",
        "title": "오세훈의 '이 정도면 됐다', 진짜 쟁점은 따로 있습니다",
        "thesis": "스타벅스 공방의 핵심은 기업 비판의 한계가 아니라 역사 조롱에 대한 공적 책임 기준이다.",
        "hook": "'이 정도면 됐다'는 말, 여기서 댓글이 갈립니다.",
        "why": "뉴스핌 보도에 따르면 오세훈 후보는 스타벅스 논란을 두고 여권 비판이 과하다는 취지로 맞섰습니다.",
        "fact": "동아일보 보도는 탱크데이 논란 이후 부스 취소와 사과까지 사태가 확산됐다고 전했습니다.",
        "conflict": "한쪽은 과잉 정치화라고 보고, 다른 쪽은 역사 기억에 대한 최소한의 책임이라고 봅니다.",
        "evidence": "선거판에서 이 이슈가 커진 이유는 역사·권력·책임 프레임이 겹쳤기 때문입니다.",
        "counter": "보수 반론은 공적 권한을 가진 정치인이 민간 기업을 압박하면 위험하다는 겁니다.",
        "rebuttal": "그 반론은 필요합니다. 다만 역사 조롱이 반복될 때 공적 비판조차 과잉이라고 밀어내는 것도 문제입니다.",
        "choice": "기업 책임 추궁입니까, 과도한 정치화입니까?",
        "cta": "둘 중 하나만 고르기 어렵다면 이유를 댓글로 남겨주세요. 다음 편에서 반론을 비교합니다.",
        "hashtags": ["오세훈", "정원오", "스타벅스", "518민주화운동", "서울시장", "정치논쟁"],
        "sources": ["starbucks_newspim", "starbucks_donga", "seoul_race"],
        "visual_anchor": "two microphones facing each other on a dark debate stage, torn apology draft on table",
        "comment_trigger": "정치권이 기업의 역사 논란을 어디까지 비판해도 된다고 보세요?",
    },
    {
        "date": "2026-05-26",
        "time": "08:10",
        "format": "growth_short",
        "topic": "민주 45, 국힘 20? 그런데 다른 조사는 33.5",
        "title": "민주 45, 국힘 20? 숫자만 보면 틀립니다",
        "thesis": "여론조사는 수치보다 조사 방식, 흐름, 격차 변화로 읽어야 한다.",
        "hook": "민주 45, 국힘 20. 그런데 다른 조사에선 33.5입니다.",
        "why": "같은 주간에도 NBS, 리얼미터, 갤럽 보도 수치가 다르게 보입니다.",
        "fact": "NBS 보도는 민주 45%, 국힘 20%를, 리얼미터 보도는 민주 45.8%, 국힘 33.5%를 전했습니다.",
        "conflict": "진보층은 압승 흐름을 보고 싶고, 보수층은 반등 신호를 강조합니다.",
        "evidence": "갤럽 보도에서도 대통령 지지율은 64%였지만 정당 지지율은 별도로 봐야 했습니다.",
        "counter": "보수 반론은 조사마다 다르니 여론조사는 믿을 수 없다는 겁니다.",
        "rebuttal": "아닙니다. 믿지 않는 게 아니라, 한 숫자만 믿지 않는 겁니다. 흐름과 격차를 같이 봐야 합니다.",
        "choice": "1 압승 신호, 2 보수 결집, 3 아직 모름. 어디입니까?",
        "cta": "숫자 싸움에 속지 않으려면 다음 조사도 같이 봐야 합니다. 팔로우하세요.",
        "hashtags": ["여론조사", "민주당", "국민의힘", "리얼미터", "NBS", "갤럽"],
        "sources": ["nbs", "realmeter", "gallup", "tiktok_search"],
        "visual_anchor": "transparent glass boards with three different polling charts overlapping, anonymous hands moving markers",
        "comment_trigger": "여론조사는 믿을 수 없나요, 아니면 읽는 법이 문제인가요?",
    },
    {
        "date": "2026-05-26",
        "time": "11:20",
        "format": "reward_deep",
        "topic": "보수 결집은 착시인가, 실제 신호인가",
        "title": "보수 결집, 착시일까요 실제 신호일까요",
        "thesis": "전체 판세가 진보 우위여도 보수 결집 신호는 댓글장과 지역 선거를 흔들 수 있다.",
        "hook": "전체 숫자는 앞섭니다. 그런데 결집은 다른 문제입니다.",
        "why": "리얼미터 보도는 민주당 하락과 국민의힘 상승을 함께 전했습니다.",
        "fact": "서울신문 보도에 따르면 민주당은 전주 대비 하락했고, 국민의힘은 상승했습니다.",
        "conflict": "진보층은 '그래도 우위'를 보고, 보수층은 '이제 붙는다'를 봅니다.",
        "evidence": "갤럽과 NBS 수치를 함께 보면 대통령 지지율, 정당 지지율, 지역 판세가 같은 방향으로 움직이지 않습니다.",
        "counter": "보수 반론은 정권 견제론이 막판에 먹힐 수 있다는 겁니다.",
        "rebuttal": "그래서 진보층이 봐야 할 건 승리감이 아니라 빈틈입니다. 댓글 프레임을 뺏기면 여론도 느슨해집니다.",
        "choice": "보수 결집은 착시입니까, 실제 경고입니까?",
        "cta": "선거판은 숫자보다 해석 싸움입니다. 이 프레임을 계속 추적합니다.",
        "hashtags": ["보수결집", "정권견제론", "민주당", "국민의힘", "지방선거", "판세분석"],
        "sources": ["realmeter", "nbs", "gallup"],
        "visual_anchor": "Korean election map in a dim strategy room, small red lights relighting while a larger blue field remains visible",
        "comment_trigger": "보수 결집은 진짜 위험 신호라고 보세요, 아니면 과장이라고 보세요?",
    },
    {
        "date": "2026-05-26",
        "time": "19:30",
        "format": "debate_followup",
        "topic": "김건희·특검 이슈, 왜 선거판에서 계속 살아나는가",
        "title": "김건희·특검 이슈가 계속 살아나는 이유",
        "thesis": "개인 스캔들 소비가 아니라 특권, 예산, 권력 사유화의 상징이기 때문이다.",
        "hook": "왜 이 이슈는 계속 다시 올라올까요. 이름 때문만은 아닙니다.",
        "why": "관저 이전 의혹과 21그램 관련 보도는 선거판의 공정성 프레임과 연결됩니다.",
        "fact": "서울신문은 특검이 관저 이전 공사 특혜 의혹과 관련해 김대기 전 비서실장 등 3명에 대해 구속영장을 청구했다고 보도했습니다.",
        "conflict": "진보층은 권력 사유화로 보고, 보수층은 정치 보복 수사라고 반박합니다.",
        "evidence": "MBC는 관저 이전 의혹 수사와 윗선 수사 흐름을 보도했습니다.",
        "counter": "보수 반론은 아직 재판으로 확정되지 않았다는 점입니다.",
        "rebuttal": "맞습니다. 그래서 단정이 아니라 질문해야 합니다. 왜 공적 예산과 사적 관계 의혹이 계속 같은 곳에서 만나는가.",
        "choice": "1 정치보복, 2 특권수사, 3 더 지켜봐야 함. 어디입니까?",
        "cta": "확정되지 않은 건 확정하지 않고, 드러난 구조는 끝까지 봅니다. 팔로우하세요.",
        "hashtags": ["김건희", "특검", "관저이전", "21그램", "권력감시", "공정성"],
        "sources": ["residence_seoul", "residence_mbc", "tiktok_integrity"],
        "visual_anchor": "dark government corridor, sealed evidence boxes, luxury interior blueprint under a cold desk lamp",
        "comment_trigger": "이 이슈는 정치보복 프레임이 맞나요, 아니면 권력 책임 프레임이 맞나요?",
    },
    {
        "date": "2026-05-27",
        "time": "08:10",
        "format": "growth_short",
        "topic": "윤석열 위증 선고 D-1, 핵심은 형량이 아니다",
        "title": "윤석열 위증 선고 D-1, 핵심은 형량이 아닙니다",
        "thesis": "선고 전 핵심은 형량 예측이 아니라 계엄 정당화 서사의 사실관계다.",
        "hook": "내일 선고. 그런데 봐야 할 건 형량만이 아닙니다.",
        "why": "위증 혐의 1심 선고가 5월 28일로 지정됐다는 보도가 나왔습니다.",
        "fact": "보도에 따르면 특검은 윤석열 전 대통령에게 징역 2년을 구형했습니다.",
        "conflict": "진보층은 책임 판단을 보고, 보수층은 정치재판 프레임을 꺼낼 가능성이 큽니다.",
        "evidence": "쟁점은 한덕수 전 총리 재판 증언과 비상계엄 국무회의 준비 여부로 보도됐습니다.",
        "counter": "보수 반론은 기억과 법리의 문제를 정치적으로 몰아간다는 겁니다.",
        "rebuttal": "그래서 더 정확히 봐야 합니다. 판결의 핵심은 감정이 아니라 증언과 기록의 충돌입니다.",
        "choice": "정치재판입니까, 책임 판단입니까?",
        "cta": "내일 결과가 나오면 판결문 기준으로 다시 정리합니다. 팔로우해두세요.",
        "hashtags": ["윤석열", "위증", "한덕수", "특검", "법원", "계엄"],
        "sources": ["yoon_perjury", "tiktok_integrity"],
        "visual_anchor": "empty courtroom corridor with a ticking wall clock, closed heavy wooden door, anonymous hand holding a sealed file",
        "comment_trigger": "형량보다 중요한 쟁점은 뭐라고 보세요?",
    },
    {
        "date": "2026-05-27",
        "time": "11:20",
        "format": "reward_deep",
        "topic": "정부견제론 vs 정권안정론, 댓글이 갈리는 이유",
        "title": "정부견제론 vs 정권안정론, 댓글이 갈리는 진짜 이유",
        "thesis": "지방선거가 생활정치만이 아니라 정권 평가 프레임으로 끌려가고 있다.",
        "hook": "지방선거인데, 댓글은 이미 정권 평가로 싸우고 있습니다.",
        "why": "6·3 지방선거를 앞두고 정당 지지율과 서울시장 초접전 보도가 동시에 나오고 있습니다.",
        "fact": "서울시장 선거는 복수 보도에서 초접전 흐름으로 전해졌고, 정당 지지율은 조사마다 다른 격차를 보였습니다.",
        "conflict": "진보 쪽은 안정적 국정 운영을, 보수 쪽은 견제를 강조합니다.",
        "evidence": "리얼미터, NBS, 갤럽 보도를 함께 보면 대통령 지지율과 정당 경쟁은 분리해서 봐야 합니다.",
        "counter": "보수 반론은 지방권력까지 한쪽으로 쏠리면 견제가 무너진다는 겁니다.",
        "rebuttal": "진보 반박은 다릅니다. 견제라는 이름으로 책임을 회피한 세력에게 다시 권한을 줄 수 있느냐는 질문입니다.",
        "choice": "1 안정론, 2 견제론, 3 지역 후보론. 무엇이 더 큽니까?",
        "cta": "댓글에서 이 세 프레임이 부딪힐 겁니다. 다음 편에서 실제 사례로 봅니다.",
        "hashtags": ["정부견제론", "정권안정론", "지방선거", "서울시장", "민주당", "국민의힘"],
        "sources": ["realmeter", "nbs", "gallup", "seoul_race"],
        "visual_anchor": "forked road outside a polling station, stability scale and watchdog silhouette, no readable text",
        "comment_trigger": "이번 선거는 지역 후보 평가가 클까요, 정권 안정·견제 프레임이 클까요?",
    },
    {
        "date": "2026-05-27",
        "time": "19:30",
        "format": "debate_followup",
        "topic": "일베식 조롱, 표현의 자유인가 혐오 장사인가",
        "title": "일베식 조롱, 표현의 자유인가 혐오 장사인가",
        "thesis": "표현의 자유와 추모·역사 조롱의 놀이화는 분리해서 판단해야 한다.",
        "hook": "표현의 자유라는 말로 어디까지 덮을 수 있을까요.",
        "why": "서울신문은 고 노무현 전 대통령 17주기 추도식 당일 봉하 기념관에서 일베 포즈 인증샷 논란이 있었다고 보도했습니다.",
        "fact": "보도에 따르면 노무현재단 관계자는 고인 모독과 혐오 표현 처벌 필요성을 언급했습니다.",
        "conflict": "진보층은 추모 공간 조롱으로 보고, 보수 반론은 표현의 자유 침해를 말할 수 있습니다.",
        "evidence": "이 논란은 스타벅스 5·18 논란과 함께 역사 기억을 조롱하는 문화가 어디까지 허용되는지 묻습니다.",
        "counter": "반론은 중요합니다. 처벌을 넓히면 표현의 자유가 위축될 수 있다는 우려입니다.",
        "rebuttal": "하지만 질문도 남습니다. 특정 고통을 반복적으로 조롱하는 놀이를 사회가 계속 방치해야 합니까?",
        "choice": "1 표현의 자유, 2 혐오 방치, 3 별도 기준 필요. 어디입니까?",
        "cta": "이건 댓글이 갈릴 수밖에 없는 주제입니다. 반론까지 남겨주세요.",
        "hashtags": ["노무현", "일베", "혐오표현", "표현의자유", "민주주의", "역사기억"],
        "sources": ["ilbe_memorial", "starbucks_donga", "tiktok_integrity"],
        "visual_anchor": "somber memorial gallery with empty bench and fractured reflection wall, anonymous visitor shadows",
        "comment_trigger": "표현의 자유와 혐오 조롱의 경계는 어디라고 보세요?",
    },
    {
        "date": "2026-05-28",
        "time": "08:10",
        "format": "growth_short",
        "topic": "오늘 윤석열 위증 1심 선고, 봐야 할 3가지",
        "title": "오늘 윤석열 위증 선고, 봐야 할 건 3가지입니다",
        "thesis": "선고 결과 전에는 유무죄를 예측하지 말고 쟁점, 판단 근거, 정치적 반응을 분리해 봐야 한다.",
        "hook": "오늘 선고. 예측보다 먼저 봐야 할 게 있습니다.",
        "why": "5월 28일 윤석열 전 대통령 위증 혐의 1심 선고가 예정됐다고 보도됐습니다.",
        "fact": "보도상 구형은 징역 2년, 쟁점은 한덕수 전 총리 재판 증언과 국무회의 준비 여부입니다.",
        "conflict": "진보층은 책임 판단을, 보수층은 정치재판 논리를 볼 가능성이 큽니다.",
        "evidence": "결과가 나오면 먼저 판결 이유, 증거 판단, 양측 반응을 분리해야 합니다.",
        "counter": "보수 반론은 재판이 정치적으로 소비된다는 겁니다.",
        "rebuttal": "그래서 더더욱 판결문 기준으로 봐야 합니다. 감정이 아니라 판단 이유가 핵심입니다.",
        "choice": "결과보다 판결 이유를 먼저 볼 준비 됐습니까?",
        "cta": "결과가 나오면 즉시 후속편으로 정리합니다. 팔로우하세요.",
        "hashtags": ["윤석열", "위증", "1심선고", "특검", "법원", "판결"],
        "sources": ["yoon_perjury", "tiktok_integrity"],
        "visual_anchor": "court building clock at morning light, three sealed folders with color marks only, anonymous reporters from behind",
        "comment_trigger": "선고 결과보다 판결 이유가 더 중요하다고 보세요?",
    },
    {
        "date": "2026-05-28",
        "time": "11:20",
        "format": "reward_deep",
        "dynamic_locked": True,
        "topic": "선고 결과 즉시 해석",
        "title": "윤석열 위증 선고 결과, 판결문 기준으로 봅니다",
        "thesis": "이 콘텐츠는 실제 선고 결과와 판결 이유 확인 후 생성해야 한다.",
        "hook": "결과가 나왔습니다. 이제 숫자가 아니라 이유를 봐야 합니다.",
        "why": "선고 결과 확인 후 판결 이유, 특검·변호인 반응, 정치적 파장을 분리합니다.",
        "fact": "[RESULT_PLACEHOLDER] 실제 선고 결과와 판결 이유를 입력해야 합니다.",
        "conflict": "정치재판 프레임과 책임 판결 프레임이 맞붙을 겁니다.",
        "evidence": "판결문 또는 법원 발표, 주요 언론 보도 2개 이상 확인 후 치환합니다.",
        "counter": "보수 반론은 판결이 정치적으로 이용된다는 주장일 수 있습니다.",
        "rebuttal": "진보 반박은 재판 소비가 아니라 책임 판단의 근거를 보자는 것입니다.",
        "choice": "정치재판입니까, 책임 판결입니까?",
        "cta": "판결문 기준 후속 검증까지 이어갑니다. 팔로우하세요.",
        "hashtags": ["윤석열", "위증", "선고결과", "판결문", "특검", "법원"],
        "sources": ["yoon_perjury", "tiktok_integrity"],
        "visual_anchor": "abstract court document under spotlight with blank pages, breaking-news energy without real news UI",
        "comment_trigger": "판결 이유를 보고 나면 정치재판 프레임이 설득력 있다고 보세요?",
    },
    {
        "date": "2026-05-28",
        "time": "19:30",
        "format": "debate_followup",
        "dynamic_locked": True,
        "topic": "정치재판인가, 책임 판결인가",
        "title": "정치재판인가, 책임 판결인가: 댓글이 갈릴 지점",
        "thesis": "이 콘텐츠는 실제 판결 결과와 양측 반응 확인 뒤 생성해야 한다.",
        "hook": "오늘 댓글은 이 한 문장으로 갈릴 겁니다. 정치재판이냐, 책임 판결이냐.",
        "why": "선고 이후 양측 반응이 확인되면 논쟁의 구조를 정리합니다.",
        "fact": "[REACTION_PLACEHOLDER] 실제 양측 반응과 판결 핵심을 입력해야 합니다.",
        "conflict": "보수는 정치재판, 진보는 책임 판결 프레임을 밀 가능성이 큽니다.",
        "evidence": "실제 발언과 보도를 인용하지 않고 요약해야 하며, 확인된 반응만 사용합니다.",
        "counter": "반론은 판결이 선거판에 이용된다는 우려입니다.",
        "rebuttal": "하지만 책임 판단을 선거와 분리하자는 말이 책임 회피가 되어서는 안 됩니다.",
        "choice": "1 정치재판, 2 책임판결, 3 더 봐야 함. 어디입니까?",
        "cta": "반론까지 보고 다음 판세 분석으로 이어갑니다.",
        "hashtags": ["윤석열", "정치재판", "책임판결", "위증", "특검", "댓글토론"],
        "sources": ["yoon_perjury", "tiktok_integrity"],
        "visual_anchor": "two opposing comment walls projected inside a courtroom-like civic hall, anonymous people only",
        "comment_trigger": "선고를 선거 프레임으로 읽는 게 정당하다고 보세요?",
    },
    {
        "date": "2026-05-29",
        "time": "08:10",
        "format": "growth_short",
        "topic": "판결 이후 지지율, 움직일까",
        "title": "판결 이후 지지율, 움직일까요",
        "thesis": "판결 자체보다 판결을 해석하는 프레임이 지지율에 더 크게 작동할 수 있다.",
        "hook": "판결 하나로 지지율이 움직일까요. 답은 조금 다릅니다.",
        "why": "지지율은 사건 자체보다 사건을 해석하는 프레임과 반복 노출에 반응합니다.",
        "fact": "최근 보도에서 대통령 지지율은 60%대였지만, 정당 지지율과 선거 판세는 조사마다 다른 긴장을 보였습니다.",
        "conflict": "진보층은 책임 판단을 강조하고, 보수층은 정치재판 프레임을 키울 가능성이 큽니다.",
        "evidence": "리얼미터, NBS, 갤럽 수치는 모두 높은 대통령 지지율과 별도 정당 경쟁을 같이 보게 만듭니다.",
        "counter": "보수 반론은 판결을 선거에 이용하지 말라는 겁니다.",
        "rebuttal": "하지만 공적 책임 판단은 정치와 완전히 분리될 수 없습니다. 문제는 왜곡 없이 읽는 겁니다.",
        "choice": "지지율을 움직이는 건 판결입니까, 프레임입니까?",
        "cta": "다음 조사에서 실제로 확인해보겠습니다. 팔로우하세요.",
        "hashtags": ["지지율", "판결", "윤석열", "이재명", "프레임", "여론조사"],
        "sources": ["realmeter", "nbs", "gallup", "yoon_perjury"],
        "visual_anchor": "polling graph line vibrating after a court gavel sound wave, abstract not literal",
        "comment_trigger": "판결이 지지율을 바꿀까요, 아니면 이미 각자 믿고 싶은 대로 해석할까요?",
    },
    {
        "date": "2026-05-29",
        "time": "11:20",
        "format": "reward_deep",
        "topic": "국민의힘의 정부견제론, 아직 먹히나",
        "title": "국민의힘 정부견제론, 아직 먹히나요",
        "thesis": "정부견제론은 보수 결집에는 유효하지만 중도 설득에는 책임 회피 프레임과 충돌한다.",
        "hook": "견제라는 말은 강합니다. 그런데 누가 누구를 견제한다는 겁니까?",
        "why": "지방선거 막판에는 정책보다 정권 안정·견제 프레임이 더 크게 소비될 수 있습니다.",
        "fact": "정당 지지율 보도는 민주당 우위와 국민의힘 반등 신호를 동시에 보여줬습니다.",
        "conflict": "보수는 견제를, 진보는 책임 있는 안정 운영을 말합니다.",
        "evidence": "리얼미터 보도는 국민의힘 상승을 보수 지지층 결집과 선거 체제 정비로 해석했습니다.",
        "counter": "보수 반론은 지방권력까지 여권에 쏠리면 균형이 무너진다는 겁니다.",
        "rebuttal": "진보 반박은 이겁니다. 견제를 말하려면 먼저 지난 권력의 책임부터 설명해야 합니다.",
        "choice": "견제론은 설득입니까, 책임 회피입니까?",
        "cta": "댓글에서 가장 많이 나올 보수 논리를 다음 편에서 정리합니다.",
        "hashtags": ["정부견제론", "국민의힘", "민주당", "지방선거", "정권안정", "책임정치"],
        "sources": ["realmeter", "nbs", "gallup"],
        "visual_anchor": "large balance scale in city hall plaza, one side marked by abstract red shapes and one by blue shapes",
        "comment_trigger": "견제론이 이번 선거에서 중도층에게 먹힐 거라고 보세요?",
    },
    {
        "date": "2026-05-29",
        "time": "19:30",
        "format": "debate_followup",
        "topic": "민주당 지지층이 방심하면 안 되는 3가지",
        "title": "민주당 지지층이 방심하면 안 되는 3가지",
        "thesis": "높은 대통령 지지율, 지역 공천 잡음, 보수 결집은 서로 다른 변수다.",
        "hook": "이길 것 같을 때 가장 많이 놓치는 게 있습니다.",
        "why": "선거 막판에는 우위보다 실수, 방심, 프레임 전환이 더 크게 보입니다.",
        "fact": "최근 보도는 대통령 지지율 60%대와 정당 지지율 차이를 함께 보여줬습니다.",
        "conflict": "진보 지지층은 낙관하고 싶고, 보수 지지층은 막판 반전을 말합니다.",
        "evidence": "리얼미터 보도는 민주당 하락과 국민의힘 상승 흐름도 함께 전했습니다.",
        "counter": "보수 반론은 정권 견제론이 결국 막판 투표장을 움직인다는 겁니다.",
        "rebuttal": "그래서 필요한 건 과신이 아니라 정리입니다. 지지율, 지역 후보, 댓글 프레임을 따로 봐야 합니다.",
        "choice": "민주당이 가장 조심해야 할 건 1 방심, 2 공천 잡음, 3 보수 결집. 무엇입니까?",
        "cta": "댓글로 하나만 골라주세요. 다음 편에서 실제 사례로 갑니다.",
        "hashtags": ["민주당", "방심금지", "지방선거", "보수결집", "지지율", "프레임"],
        "sources": ["realmeter", "nbs", "gallup"],
        "visual_anchor": "blue campaign office late at night, three warning lights on a dashboard, coffee cups and maps",
        "comment_trigger": "민주당 지지층이 제일 경계해야 할 변수는 뭐라고 보세요?",
    },
    {
        "date": "2026-05-30",
        "time": "08:10",
        "format": "growth_short",
        "topic": "스타벅스 불매, 선거용 분노인가 역사 책임인가",
        "title": "스타벅스 불매, 선거용 분노입니까 역사 책임입니까",
        "thesis": "불매 논쟁은 소비 선택이 아니라 역사 조롱에 대한 사회적 책임 기준 논쟁이다.",
        "hook": "불매가 과하다는 말, 정말 그게 핵심일까요?",
        "why": "탱크데이 논란은 기업 사과 이후에도 선거판과 시민사회 논쟁으로 이어졌습니다.",
        "fact": "동아일보는 논란 이후 서재페 스타벅스 부스 운영 취소와 사과 흐름을 보도했습니다.",
        "conflict": "한쪽은 역사 책임을 말하고, 다른 쪽은 선거용 분노라고 반박합니다.",
        "evidence": "뉴스핌 보도에서도 서울시장 선거 공방과 연결됐습니다.",
        "counter": "보수 반론은 민간 기업 문제를 정치가 과하게 때린다는 겁니다.",
        "rebuttal": "하지만 역사 기억을 건드린 마케팅은 소비자가 책임을 묻는 방식까지 포함해 논쟁될 수밖에 없습니다.",
        "choice": "불매는 책임입니까, 과잉입니까?",
        "cta": "이 질문에 답하면 역사 인식의 기준도 드러납니다. 댓글로 남겨주세요.",
        "hashtags": ["스타벅스불매", "탱크데이", "518민주화운동", "역사책임", "정치화", "소비자운동"],
        "sources": ["starbucks_donga", "starbucks_newspim", "tiktok_integrity"],
        "visual_anchor": "closed coffee shop counter with a single untouched cup, cinematic daylight through glass",
        "comment_trigger": "불매를 책임 있는 소비로 보세요, 아니면 정치 과잉으로 보세요?",
    },
    {
        "date": "2026-05-30",
        "time": "11:20",
        "format": "reward_deep",
        "topic": "보수 댓글 5개 논리, 반박해보자",
        "title": "보수 댓글 5개 논리, 어디까지 맞을까요",
        "thesis": "상대 주장을 약하게 만들지 말고 가장 강한 형태로 놓고 반박해야 댓글장에서 밀리지 않는다.",
        "hook": "댓글에서 이 다섯 문장, 거의 반드시 나옵니다.",
        "why": "스타벅스, 지지율, 윤석열 재판, 특검 이슈는 모두 같은 댓글 패턴을 만듭니다.",
        "fact": "최근 보도 이슈들은 역사 책임, 정권견제, 사법 판단, 여론조사 해석으로 갈라졌습니다.",
        "conflict": "보수 댓글은 과잉 정치화, 정치보복, 여론조사 불신, 표현의 자유, 경제·민생 우선으로 압축됩니다.",
        "evidence": "각 반론은 실제 공방 기사와 지지율 보도에서 반복되는 프레임입니다.",
        "counter": "반론을 무시하면 댓글장에서 집니다. 상대 논리를 먼저 정확히 적어야 합니다.",
        "rebuttal": "진보 반박은 감정이 아니라 기준이어야 합니다. 책임, 기록, 공정성, 역사 기억, 권력 감시입니다.",
        "choice": "가장 강한 보수 댓글 논리는 무엇입니까?",
        "cta": "댓글에 하나만 적어주세요. 다음 콘텐츠에서 그 논리부터 반박합니다.",
        "hashtags": ["보수댓글", "댓글전쟁", "프레임분석", "정치논쟁", "팩트체크", "진보"],
        "sources": ["realmeter", "starbucks_newspim", "yoon_perjury", "residence_seoul"],
        "visual_anchor": "five floating comment cards made of glass colliding with a blue fact-check desk, anonymous hands typing",
        "comment_trigger": "보수 댓글 중 가장 설득력 있는 논리는 뭐라고 보세요?",
    },
    {
        "date": "2026-05-30",
        "time": "19:30",
        "format": "debate_followup",
        "topic": "이번 주 우파가 밀어붙인 프레임 TOP5",
        "title": "이번 주 우파 프레임 TOP5, 끌려가면 집니다",
        "thesis": "프레임을 먼저 알아야 댓글과 여론전에서 방어가 가능하다.",
        "hook": "이번 주 댓글장을 흔든 프레임, 다섯 개로 정리됩니다.",
        "why": "선거 막판에는 사실보다 프레임이 먼저 퍼지고, 나중에 사실이 따라갑니다.",
        "fact": "정부견제론, 과잉 정치화, 정치재판, 여론조사 불신, 표현의 자유가 주요 반론으로 반복됩니다.",
        "conflict": "진보층은 책임 기준을 말하지만, 보수층은 과잉·보복·견제 프레임으로 밀어붙입니다.",
        "evidence": "스타벅스 공방, 지지율 보도, 윤석열 선고 이슈, 특검 보도가 이 프레임의 재료가 됐습니다.",
        "counter": "보수 반론은 이 모든 게 선거용 프레임이라는 주장입니다.",
        "rebuttal": "하지만 프레임이라고 해서 책임이 사라지지는 않습니다. 프레임을 걷어내고 기준을 봐야 합니다.",
        "choice": "가장 위험한 프레임은 1 견제론, 2 정치재판, 3 과잉정치화. 무엇입니까?",
        "cta": "가장 많이 본 댓글 문장을 남겨주세요. 다음 편에서 해부합니다.",
        "hashtags": ["우파프레임", "프레임전쟁", "지방선거", "정치댓글", "진보콘텐츠", "시사정리"],
        "sources": ["starbucks_newspim", "realmeter", "yoon_perjury", "residence_mbc"],
        "visual_anchor": "news strategy wall with five red strings connecting anonymous issue photos and empty headline blocks",
        "comment_trigger": "이번 주 가장 많이 본 우파 프레임은 무엇이었나요?",
    },
    {
        "date": "2026-05-31",
        "time": "08:10",
        "format": "growth_short",
        "topic": "이번 주 선거판 흔든 장면 TOP5",
        "title": "이번 주 선거판 흔든 장면 TOP5",
        "thesis": "지지율, 역사 논란, 재판, 혐오표현, 서울시장 초접전이 한 주의 핵심 장면이다.",
        "hook": "이번 주 선거판, 다섯 장면이면 정리됩니다.",
        "why": "선거 직전 주말에는 이슈를 흩어보면 흐름을 놓칩니다.",
        "fact": "지지율 60%대, 스타벅스 5·18 논란, 윤석열 선고 일정, 일베 포즈 논란, 서울시장 초접전이 겹쳤습니다.",
        "conflict": "진보층은 책임·기억·안정론을 보고, 보수층은 견제·과잉·정치재판을 봅니다.",
        "evidence": "각 이슈는 최근 주요 보도와 여론조사 보도로 확인됩니다.",
        "counter": "보수 반론은 진보 진영이 모든 이슈를 선거에 끌어온다는 겁니다.",
        "rebuttal": "하지만 선거는 결국 무엇을 기억하고 무엇에 책임을 묻는지의 싸움입니다.",
        "choice": "이번 주 가장 컸던 장면은 무엇입니까?",
        "cta": "댓글로 TOP1을 골라주세요. 다음 주 선거 직전 프레임을 정리합니다.",
        "hashtags": ["이번주정치", "지방선거", "지지율", "스타벅스", "윤석열", "서울시장"],
        "sources": ["realmeter", "starbucks_donga", "yoon_perjury", "ilbe_memorial", "seoul_race"],
        "visual_anchor": "five cinematic panels floating in a vertical newsroom, representing polls, coffee booth, court, memorial, city race",
        "comment_trigger": "이번 주 정치 이슈 TOP1은 뭐였다고 보세요?",
    },
    {
        "date": "2026-05-31",
        "time": "11:20",
        "format": "reward_deep",
        "topic": "지지율이 높을수록 조심해야 할 말",
        "title": "지지율이 높을수록 조심해야 할 말",
        "thesis": "높은 지지율은 오만 프레임으로 공격받기 쉬우므로 진보 진영은 책임과 근거 언어를 유지해야 한다.",
        "hook": "높은 지지율, 기분 좋은 숫자입니다. 그런데 말 한마디가 프레임이 됩니다.",
        "why": "여론조사 우위는 선거 막판에 오만, 방심, 싹쓸이 프레임으로 공격받을 수 있습니다.",
        "fact": "최근 보도에서 대통령 지지율은 60%대였고, 정당 지지율은 조사마다 다른 격차를 보였습니다.",
        "conflict": "진보층은 안정론을 원하지만, 보수층은 견제론과 오만 프레임을 동시에 밀 수 있습니다.",
        "evidence": "리얼미터 보도는 민주당 하락과 국민의힘 상승도 함께 전했습니다.",
        "counter": "보수 반론은 권력이 한쪽으로 쏠리면 위험하다는 겁니다.",
        "rebuttal": "진보의 답은 승리감이 아니라 책임감이어야 합니다. 숫자보다 기준을 말해야 합니다.",
        "choice": "진보 진영이 가장 피해야 할 말은 무엇입니까?",
        "cta": "댓글에 금지해야 할 한 문장을 적어주세요. 다음 편에서 정리합니다.",
        "hashtags": ["지지율", "오만프레임", "민주당", "이재명", "지방선거", "정치전략"],
        "sources": ["realmeter", "nbs", "gallup"],
        "visual_anchor": "campaign speech podium with a glowing poll number casting a long risky shadow, anonymous speaker silhouette from behind",
        "comment_trigger": "진보 지지층이 선거 막판 가장 조심해야 할 말은 뭐라고 보세요?",
    },
    {
        "date": "2026-05-31",
        "time": "19:30",
        "format": "debate_followup",
        "topic": "심판론이냐 안정론이냐, 댓글로 판정",
        "title": "심판론이냐 안정론이냐, 댓글로 판정해봅시다",
        "thesis": "선거 직전 마지막 프레임은 과거 권력 심판과 현재 국정 안정 사이의 선택지로 압축된다.",
        "hook": "결국 댓글은 이 질문으로 돌아옵니다. 심판입니까, 안정입니까?",
        "why": "선거가 가까워질수록 생활 공약보다 큰 프레임이 댓글과 공유를 지배합니다.",
        "fact": "이번 주 보도 이슈는 지지율, 역사 논란, 재판, 특검, 서울시장 초접전으로 이어졌습니다.",
        "conflict": "진보층은 책임 있는 안정과 과거 권력 심판을 같이 말하고, 보수층은 견제를 말합니다.",
        "evidence": "여론조사 보도와 주요 논란 보도는 모두 이 프레임 충돌 안에 들어옵니다.",
        "counter": "보수 반론은 심판론이 이미 지나갔고 이제 견제가 필요하다는 겁니다.",
        "rebuttal": "진보 반박은 책임이 끝나지 않았고, 안정도 책임 위에서 가능하다는 겁니다.",
        "choice": "1 심판론, 2 안정론, 3 견제론. 댓글로 판정해주세요.",
        "cta": "가장 설득력 있는 댓글은 다음 콘텐츠에서 다룹니다. 팔로우하고 이어서 보세요.",
        "hashtags": ["심판론", "안정론", "견제론", "지방선거", "댓글토론", "정치프레임"],
        "sources": ["realmeter", "nbs", "gallup", "starbucks_newspim", "yoon_perjury"],
        "visual_anchor": "three-way civic debate arena with blue, red, and neutral light beams converging on an empty central chair",
        "comment_trigger": "이번 선거의 핵심은 심판론, 안정론, 견제론 중 무엇입니까?",
    },
]


CARD_ROLES = [
    ("hook", "썸네일"),
    ("why", "왜 지금인가"),
    ("fact", "확인된 사실"),
    ("conflict", "충돌 지점"),
    ("evidence", "근거"),
    ("counter", "보수 반론"),
    ("rebuttal", "진보 반박"),
    ("choice", "댓글 선택"),
    ("cta", "정리와 팔로우"),
]


def short_overlay(text: str, limit: int = 38) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return f"{cut}..."


def tts_text(role: str, text: str) -> str:
    replacements = {
        "5·18": "오 일 팔",
        "60.5%": "육십 점 오 퍼센트",
        "33.5%": "삼십삼 점 오 퍼센트",
        "45.8%": "사십오 점 팔 퍼센트",
        "64%": "육십사 퍼센트",
        "45%": "사십오 퍼센트",
        "20%": "이십 퍼센트",
        "22%": "이십이 퍼센트",
        "NBS": "엔비에스",
        "5월 28일": "오월 이십팔일",
        "6·3": "육 삼",
        "21그램": "이십일 그램",
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    if role == "hook":
        return f"{result} 잠깐 멈춰서 볼 만한 쟁점입니다."
    return result


def prompt_for_card(post: dict[str, object], role: str, index: int) -> str:
    role_scene = {
        "hook": "dominant foreground object, first-second visual question, compressed depth",
        "why": "calendar and clock tension, recent news atmosphere, no readable headlines",
        "fact": "evidence table with documents represented as blank shapes, source verification mood",
        "conflict": "split composition showing two opposing civic interpretations, anonymous figures",
        "evidence": "close-up of factual anchors, charts or files without readable text",
        "counter": "opposition argument represented as a red-lit debate microphone, no party symbols",
        "rebuttal": "blue-white fact-check light cutting across a dark room, accountability mood",
        "choice": "comment-choice scene with abstract numbered panels, clean overlay zone",
        "cta": "AiNo-style closing scene, anonymous Korean female AI host silhouette from side, no real person likeness",
    }[role]
    return (
        f"{BASE_STYLE}. Scene {index}: {post['visual_anchor']}. "
        f"{role_scene}. {NEGATIVE_VISUAL}"
    )


def build_cards(post: dict[str, object]) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for index, (role, role_name) in enumerate(CARD_ROLES, start=1):
        text = str(post[role])
        cards.append(
            {
                "index": index,
                "role": role,
                "role_name": role_name,
                "overlay_text": short_overlay(text, 30 if role in {"hook", "choice"} else 42),
                "body_text": text,
                "tts_text": tts_text(role, text),
                "duration_sec_target": 5 if role in {"hook", "cta"} else (8 if post["format"] == "reward_deep" else 7),
                "visual_prompt_en": prompt_for_card(post, role, index),
                "readability_rule": (
                    "max 2 lines, keep core text outside top 120px, bottom 320px, "
                    "right 130px TikTok UI safe zones"
                ),
            }
        )
    return cards


def caption(post: dict[str, object]) -> str:
    source_names = ", ".join(
        SOURCES[key]["name"].split()[0]
        for key in post["sources"][:2]
        if key in SOURCES
    )
    return (
        f"{post['title']}\n"
        f"{post['thesis']} 확인된 보도와 반론을 나눠 봅니다. "
        f"주요 참고: {source_names}. {post['choice']} "
        "이미지: AI 생성 장면."
    )


def post_id(post: dict[str, object]) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", str(post["topic"]))[:28]
    return f"leftaino_{str(post['date']).replace('-', '')}_{str(post['time']).replace(':', '')}_{slug}"


def compile_pack() -> dict[str, object]:
    compiled: list[dict[str, object]] = []
    for post in POSTS:
        cards = build_cards(post)
        status = "dynamic_locked_until_fact_update" if post.get("dynamic_locked") else "content_pack_ready"
        compiled.append(
            {
                "id": post_id(post),
                "channel": "올바른 AiNo",
                "account": "@leftaino",
                "planned_publish_at_local": f"{post['date']}T{post['time']}:00+09:00",
                "format": post["format"],
                "generation_status": status,
                "topic": post["topic"],
                "title": post["title"],
                "thesis": post["thesis"],
                "left_audience_fit": "진보 지지층의 책임·기억·공정성·권력감시 감정에 맞춘 논쟁형 구성",
                "opposition_frame": post["counter"],
                "left_rebuttal": post["rebuttal"],
                "comment_trigger": post["comment_trigger"],
                "cards": cards,
                "caption": caption(post),
                "pinned_comment": (
                    f"{post['comment_trigger']} 반론도 받습니다. "
                    "팔로우하면 다음 쟁점에서 이어갑니다."
                ),
                "hashtags": list(dict.fromkeys(post["hashtags"] + COMMON_HASHTAGS)),
                "sources": [SOURCES[key] for key in post["sources"] if key in SOURCES],
                "policy_notes": [
                    "정치적 의견 콘텐츠이며 직접 투표 요청 문구를 쓰지 않는다.",
                    "선거 절차·결과 관련 미확인 주장을 넣지 않는다.",
                    "실존 정치인 얼굴·정당 로고·가짜 언론 UI를 생성하지 않는다.",
                    "현실적인 AI 이미지/오디오 사용이므로 AIGC 고지 또는 라벨을 적용한다.",
                ],
                "production_spec": {
                    "resolution": "1080x1920",
                    "fps": 30,
                    "target_duration_sec": sum(int(card["duration_sec_target"]) for card in cards),
                    "scene_count": 9,
                    "tts_provider_priority": ["elevenlabs", "block_upload_on_fallback"],
                    "image_provider_priority": ["codex_cli", "gemini_api", "block_upload_on_local_fallback"],
                    "motion": "no shake; hard cut, wipe, push-in under 1.5% only",
                },
            }
        )

    return {
        "schema_version": "leftaino_weekly_content_pack_v1",
        "created_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),
        "basis_document": str(ROOT / "src" / "core" / "tiktok_aino" / "LEFT_SUPPORT_CONTENT_MASTER_PLAN_20260524.md"),
        "date_range": {"start": "2026-05-25", "end": "2026-05-31"},
        "count": len(compiled),
        "ready_count": sum(item["generation_status"] == "content_pack_ready" for item in compiled),
        "dynamic_locked_count": sum(item["generation_status"] != "content_pack_ready" for item in compiled),
        "slots": compiled,
        "global_sources": SOURCES,
        "qa_gates": {
            "mobile_readability": "overlay_text max 2 lines and safe zones required",
            "source_count": "2+ sources preferred; dynamic result slots require fresh result sources before render",
            "aigc": "caption disclosure plus TikTok AIGC label where available",
            "political_safety": "public-interest commentary, no vote instruction, no paid promotion, no fake election claims",
            "visual_safety": NEGATIVE_VISUAL,
        },
    }


def write_markdown(pack: dict[str, object], path: Path) -> None:
    lines = [
        "# 올바른 AiNo 7일치 콘텐츠 생성 패키지",
        "",
        f"생성일: {pack['created_at']}",
        f"범위: {pack['date_range']['start']} ~ {pack['date_range']['end']}",
        f"총 {pack['count']}개, 즉시 제작 가능 {pack['ready_count']}개, 결과 확인 필요 {pack['dynamic_locked_count']}개",
        "",
    ]
    for post in pack["slots"]:
        lines.extend(
            [
                f"## {post['planned_publish_at_local']} | {post['title']}",
                "",
                f"- 상태: `{post['generation_status']}`",
                f"- 형식: `{post['format']}`",
                f"- 논지: {post['thesis']}",
                f"- 보수 반론: {post['opposition_frame']}",
                f"- 진보 반박: {post['left_rebuttal']}",
                f"- 고정댓글: {post['pinned_comment']}",
                f"- 해시태그: {' '.join('#' + tag for tag in post['hashtags'])}",
                "",
                "### 카드/TTS",
            ]
        )
        for card in post["cards"]:
            lines.append(f"{card['index']}. **{card['role_name']}**: {card['overlay_text']}")
            lines.append(f"   - TTS: {card['tts_text']}")
        lines.extend(["", "### 이미지 프롬프트 요약"])
        for card in post["cards"][:3]:
            lines.append(f"- {card['index']}: {card['visual_prompt_en']}")
        lines.extend(["", "### 캡션", "```text", str(post["caption"]), "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(pack: dict[str, object], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        fieldnames = [
            "id",
            "planned_publish_at_local",
            "status",
            "format",
            "title",
            "caption",
            "pinned_comment",
            "hashtags",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for post in pack["slots"]:
            writer.writerow(
                {
                    "id": post["id"],
                    "planned_publish_at_local": post["planned_publish_at_local"],
                    "status": post["generation_status"],
                    "format": post["format"],
                    "title": post["title"],
                    "caption": post["caption"],
                    "pinned_comment": post["pinned_comment"],
                    "hashtags": " ".join("#" + tag for tag in post["hashtags"]),
                }
            )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pack = compile_pack()
    json_path = OUT / "weekly_left_support_content_pack_20260525_0531.json"
    md_path = OUT / "weekly_left_support_content_pack_20260525_0531.md"
    csv_path = OUT / "weekly_upload_metadata_20260525_0531.csv"

    json_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(pack, md_path)
    write_csv(pack, csv_path)

    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(md_path),
                "csv": str(csv_path),
                "count": pack["count"],
                "ready_count": pack["ready_count"],
                "dynamic_locked_count": pack["dynamic_locked_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
