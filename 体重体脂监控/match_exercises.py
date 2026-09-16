"""
匹配8周增肌塑形计划动作到 exercises.json 数据集 (v2 严格匹配)
输出: exercises_matched.json

匹配策略:
1. 精确匹配(归一化后name == 关键词)
2. name包含完整关键词(子串)
3. 不使用模糊覆盖匹配,避免错误匹配
4. 找不到的标记 matched:false, media_id=null
"""

import json
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_BASE_DIR, "..", "exercises-dataset", "data", "exercises.json")
OUT_PATH = os.path.join(_BASE_DIR, "exercises_matched.json")

# 去重后的动作清单: (中文名, [英文关键词候选, 按优先级排序])
# 关键词经过人工核对数据集,确保能匹配到最佳候选
ACTIONS = [
    # 胸+三头
    ("上斜哑铃卧推", ["dumbbell incline bench press", "incline dumbbell bench press", "incline dumbbell press"]),
    ("平板哑铃卧推", ["dumbbell bench press", "flat dumbbell press"]),
    ("绳索夹胸", ["cable cross-over variation", "cable crossover", "cable incline fly", "cable fly"]),
    ("哑铃肩推", ["dumbbell one arm shoulder press", "dumbbell shoulder press", "dumbbell seated shoulder press"]),
    ("哑铃侧平举", ["dumbbell lateral raise", "dumbbell side lateral raise", "side lateral raise"]),
    ("窄距俯卧撑", ["diamond push-up", "diamond pushup", "close-grip push-up", "close grip pushup"]),
    ("绳索下压", ["cable pushdown", "cable triceps pushdown", "triceps pushdown"]),
    ("平板支撑", ["weighted front plank", "front plank", "plank"]),
    # 背+二头
    ("单臂哑铃划船", ["dumbbell one arm bent-over row", "one arm dumbbell row", "dumbbell one arm row"]),
    ("高位下拉", ["cable lat pulldown full range of motion", "lat pulldown", "lateral pulldown"]),
    ("俯身杠铃划船", ["barbell bent over row", "barbell bent-over row", "barbell row"]),
    ("哑铃弯举", ["dumbbell biceps curl", "dumbbell curl"]),
    ("锤式弯举", ["dumbbell hammer curl", "hammer curl"]),
    ("引体向上", ["pull-up", "pullup", "chin-up", "chinup"]),
    ("直臂下压", ["cable straight arm pulldown", "straight arm pulldown", "cable pullover"]),
    ("俄罗斯转体", ["russian twist"]),
    # 腿+臀
    ("杠铃深蹲", ["barbell full squat", "barbell squat", "back squat"]),
    (
        "保加利亚分腿蹲",
        ["dumbbell single leg split squat", "barbell single leg split squat", "split squats", "bulgarian split squat"],
    ),
    ("罗马尼亚硬拉", ["dumbbell romanian deadlift", "romanian deadlift"]),
    ("哑铃硬拉", ["dumbbell deadlift"]),
    ("腿弯举", ["lever lying leg curl", "lever lying two-one leg curl", "lying leg curl", "leg curl"]),
    ("腿举", ["sled 45 leg press", "sled leg press", "leg press"]),
    ("站姿提踵", ["barbell standing calf raise", "standing calf raise", "calf raise"]),
    ("反向卷腹", ["reverse crunch"]),
    # 肩+核心
    ("坐姿哑铃肩推", ["dumbbell seated shoulder press", "dumbbell seated press"]),
    ("哑铃前平举", ["dumbbell front raise", "front raise"]),
    (
        "哑铃俯身飞鸟",
        [
            "dumbbell rear lateral raise",
            "dumbbell rear delt raise",
            "dumbbell rear fly",
            "dumbbell bent over lateral raise",
        ],
    ),
    ("阿诺德推举", ["dumbbell arnold press", "arnold press"]),
    ("仰卧举腿", ["lying leg raise flat bench", "lying leg raise", "lying straight leg raise"]),
    ("侧平板支撑", ["side bridge v. 2", "side bridge", "side plank"]),
    ("死虫", ["dead bug", "deadbug"]),
    # 全身循环HIIT
    ("上斜俯卧撑", ["incline push-up", "incline pushup"]),
    ("自重深蹲", ["bodyweight squat", "body weight squat", "air squat"]),
    ("弓步蹲", ["walking lunge", "lunge"]),
    ("登山跑", ["mountain climber", "mountain climbers"]),
    ("波比跳", ["burpee", "burpees"]),
    ("开合跳", ["jumping jack", "jumping jacks"]),
    ("高抬腿", ["high knee against wall", "high knees", "high knee"]),
]


def normalize(s):
    """归一化:小写+去标点(保留字母数字和空格)"""
    if not s:
        return ""
    out = []
    for ch in s.lower():
        if ch.isalnum() or ch == " ":
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def find_match(exercises, keywords):
    """
    严格匹配策略(词级,避免子串误匹配):
    1. 精确匹配(归一化name == 归一化关键词)
    2. 关键词词序列是name词序列的连续子序列
    3. name所有词都在关键词中出现(name是关键词的"子集",适用于短name)
    不使用字符级子串匹配
    """
    norm_kw = [normalize(k) for k in keywords if k]

    # 策略1: 精确匹配
    for kw in norm_kw:
        for ex in exercises:
            if normalize(ex.get("name", "")) == kw:
                return ex

    # 策略2: 关键词词序列是name词序列的连续子序列
    for kw in norm_kw:
        kw_tokens = kw.split()
        if not kw_tokens:
            continue
        for ex in exercises:
            n_tokens = normalize(ex.get("name", "")).split()
            if not n_tokens or len(n_tokens) < len(kw_tokens):
                continue
            # 检查 kw_tokens 是否是 n_tokens 的连续子序列
            for i in range(len(n_tokens) - len(kw_tokens) + 1):
                if n_tokens[i : i + len(kw_tokens)] == kw_tokens:
                    return ex

    # 策略3: name的所有词都在关键词词集中(name是关键词的子集,适用于短name如"plank")
    # 但要求name词数 >= 关键词词数的50%,避免短name误匹配
    for kw in norm_kw:
        kw_words_set = set(kw.split())
        if not kw_words_set:
            continue
        for ex in exercises:
            n = normalize(ex.get("name", ""))
            if not n:
                continue
            n_words = n.split()
            if not n_words:
                continue
            # name的所有词必须在关键词中出现
            if all(w in kw_words_set for w in n_words) and len(n_words) >= max(1, len(kw_words_set) * 0.5):
                return ex

    return None


def build_record(cn_name, ex):
    if ex is None:
        return {
            "id": None,
            "name_cn": cn_name,
            "name_en": None,
            "category": None,
            "target": None,
            "muscle_group": None,
            "secondary_muscles": [],
            "equipment": None,
            "instructions_zh": None,
            "instruction_steps_zh": [],
            "media_id": None,
            "matched": False,
        }
    instructions = ex.get("instructions", {}) or {}
    steps = ex.get("instruction_steps", {}) or {}
    return {
        "id": ex.get("id"),
        "name_cn": cn_name,
        "name_en": ex.get("name"),
        "category": ex.get("category"),
        "target": ex.get("target"),
        "muscle_group": ex.get("muscle_group"),
        "secondary_muscles": ex.get("secondary_muscles", []) or [],
        "equipment": ex.get("equipment"),
        "instructions_zh": instructions.get("zh") or instructions.get("en"),
        "instruction_steps_zh": steps.get("zh") or steps.get("en") or [],
        "media_id": ex.get("media_id"),
        "matched": True,
    }


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        exercises = json.load(f)
    print(f"载入数据集: {len(exercises)} 条动作")

    results = []
    matched_count = 0
    for cn_name, keywords in ACTIONS:
        ex = find_match(exercises, keywords)
        rec = build_record(cn_name, ex)
        results.append(rec)
        if rec["matched"]:
            matched_count += 1
            print(f"  ✓ {cn_name:<10} -> {rec['name_en']:<45} (id={rec['id']}, media={rec['media_id']})")
        else:
            print(f"  ✗ {cn_name:<10} -> 未匹配 (数据集中无对应动作)")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n输出: {OUT_PATH}")
    print(f"总计: {len(results)} 条, 成功匹配: {matched_count}, 未匹配: {len(results) - matched_count}")


if __name__ == "__main__":
    main()
