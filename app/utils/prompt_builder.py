from __future__ import annotations


class PromptBuilder:
    def __init__(self, history_limit: int = 6, max_rounds: int = 3):
        self.history_limit = history_limit
        self.max_rounds = max_rounds

    def build_debate_messages(self, session, history: list, user_content: str) -> list[dict]:
        assistant_position = "反方" if session.position == "正方" else "正方"
        recent_history = history[-self.history_limit :]
        round_no = session.current_round + 1
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一名严格、专业但克制的中文辩论陪练。"
                    f"本场辩题是：{session.topic}。"
                    f"用户持方是：{session.position}，你必须坚定扮演{assistant_position}。"
                    f"当前是第 {round_no} / {self.max_rounds} 回合，这是一场连续攻防，不是三次独立问答。"
                    "你必须结合此前交锋，延续或收束同一条核心争点；如果用户回应了你上一轮的质疑，"
                    "要判断其是否真正补强，不能无视历史重新开题。"
                    "回复必须紧扣用户最新发言中的具体词句或主张，不要泛泛而谈，也不要重复辩题背景。"
                    "第1轮：建立你的反方主线，并指出用户开场论证最薄弱的前提。"
                    "第2轮：围绕上一轮留下的争点继续追问，检验用户是否补足论据或偷换概念。"
                    "第3轮：做终局反驳，明确指出用户三轮中仍未解决的关键漏洞。"
                    "每轮回复要包含三类信息：一处具体漏洞、一个反例/边界情形/现实代价、一个迫使对方补证的追问。"
                    "不得承认自己是 AI，不要寒暄，不要用“首先/其次/最后”编号。"
                    "回复保持 170 到 280 字，语气有压迫感但不要人身攻击。"
                ),
            }
        ]

        for item in recent_history:
            messages.append({"role": item.role, "content": item.content})

        messages.append({"role": "user", "content": user_content})
        return messages

    def build_evaluation_messages(self, session, history: list) -> list[dict]:
        transcript_lines = []
        for item in history:
            role_label = "用户" if item.role == "user" else "AI"
            transcript_lines.append(f"第{item.round_no}回合 {role_label}：{item.content}")

        transcript = "\n".join(transcript_lines)
        return [
            {
                "role": "system",
                "content": (
                    "你是一名严格的中文辩论教练，任务是评价用户一方的三轮表现，"
                    "不是评价 AI 一方。你必须基于完整三轮攻防记录评分，不能只看最后一轮，"
                    "也不能使用脱离本场内容的通用建议。请只返回 JSON 对象，不要输出解释。"
                    "JSON 必须包含 logic_score、evidence_score、fluency_score、suggestion 四个字段。"
                    "前三项是 0 到 10 的整数，评分要有区分度："
                    "0-3 表示明显缺失，4-6 表示基本可用但问题较多，"
                    "7-8 表示较好但仍有短板，9-10 只给论证完整且回应充分的表现。"
                    "suggestion 用 160 到 220 字中文，必须贴合本场记录，包含："
                    "用户三轮中最好的一个点、被 AI 追问后仍没补上的短板、"
                    "下一次训练可以直接照做的一条改法。建议中要点名至少一个本场出现过的具体论点或表达。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"请根据以下完整 3 回合辩论记录，为用户生成赛后评分。\n"
                    f"辩题：{session.topic}\n"
                    f"用户持方：{session.position}\n"
                    "评分维度说明：\n"
                    "logic_score：是否有清晰主张、因果链条、前提自洽，并能回应对方攻击。\n"
                    "evidence_score：是否有事实、例子、数据、场景或可验证依据支撑，而不是只喊价值判断。\n"
                    "fluency_score：表达是否清楚、有层次、关键词稳定，是否便于听众理解。\n"
                    "请按三轮连续攻防来判断：用户是否回应了 AI 上一轮的挑战，是否补强原论点，"
                    "是否出现重复表达、回避问题或偷换概念。请避免平均给分；"
                    "如果用户论据空泛，evidence_score 应明显低于其他项。\n"
                    f"辩论记录：\n{transcript}"
                ),
            },
        ]
