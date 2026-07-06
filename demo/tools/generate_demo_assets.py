from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "scenes"
DATA = ROOT / "data"


RISK_RULES = [
    {
        "id": "electric_shock",
        "name": "触电风险",
        "rule": "液体、积水或潮湿物体靠近插座、电器、电线时判定为触电风险。",
        "level_hint": "靠近插座或正在运行电器时为高风险。",
    },
    {
        "id": "fire",
        "name": "火灾风险",
        "rule": "纸张、布料、塑料袋等易燃物靠近灶台、电暖器、热水壶等热源时判定为火灾风险。",
        "level_hint": "易燃物与热源距离很近或热源开启时为高风险。",
    },
    {
        "id": "trip_or_block",
        "name": "通行/绊倒风险",
        "rule": "箱子、椅子、电线、杂物位于门口、走廊、主要通道时判定为通行或绊倒风险。",
        "level_hint": "阻挡出口或夜间不易观察的位置为中高风险。",
    },
    {
        "id": "falling_object",
        "name": "坠物风险",
        "rule": "重物、花瓶、箱子等放在高处边缘或不稳定堆叠时判定为坠物风险。",
        "level_hint": "位于头顶高度或人常经过区域上方时为高风险。",
    },
    {
        "id": "danger_exposure",
        "name": "危险物暴露",
        "rule": "刀具、化学品、工具等危险物处于儿童或无关人员易触达区域时判定为暴露风险。",
        "level_hint": "无收纳、无标签或靠近活动区域时为中高风险。",
    },
    {
        "id": "cleanliness",
        "name": "清洁度异常",
        "rule": "垃圾、污渍、食物残渣、杂乱堆积影响环境卫生或管理状态时判定为清洁度异常。",
        "level_hint": "影响通行或靠近电器、热源时风险升级。",
    },
]


SCENES = [
    {
        "id": "S01",
        "title": "宿舍桌面正常状态",
        "scene_type": "宿舍",
        "summary": "水杯位于桌面中央，插座远离液体，通道保持畅通。",
        "objects": ["书桌", "水杯", "插座", "床", "门"],
        "ground_truth": [],
        "svg": {
            "zones": [("desk", 60, 80, 260, 150), ("bed", 390, 80, 180, 170), ("door", 35, 285, 80, 120)],
            "objects": [
                ("水杯", "cup", 165, 135, "#38bdf8"),
                ("插座", "socket", 300, 205, "#475569"),
                ("书本", "book", 95, 120, "#22c55e"),
            ],
        },
    },
    {
        "id": "S02",
        "title": "水杯靠近插座",
        "scene_type": "宿舍",
        "summary": "桌角水杯靠近墙面插座，液体与电源区域距离过近。",
        "objects": ["水杯", "插座", "书桌", "床"],
        "ground_truth": [
            {
                "type": "触电风险",
                "objects": ["水杯", "插座"],
                "location": "书桌右侧靠墙区域",
                "level": "高",
                "reason": "液体容器靠近插座，若倾倒可能导致短路或触电。",
                "suggestion": "将水杯移到远离插座的位置，并保持插座周围干燥。",
            }
        ],
        "svg": {
            "zones": [("desk", 60, 80, 270, 150), ("bed", 390, 80, 180, 170)],
            "objects": [
                ("水杯", "cup", 276, 150, "#38bdf8"),
                ("插座", "socket", 305, 145, "#475569"),
                ("风险距离", "line", 284, 150, "#ef4444"),
            ],
        },
    },
    {
        "id": "S03",
        "title": "门口箱子阻塞",
        "scene_type": "宿舍",
        "summary": "收纳箱堆在门口，影响出入和紧急疏散。",
        "objects": ["箱子", "门", "床", "书桌"],
        "ground_truth": [
            {
                "type": "通行/绊倒风险",
                "objects": ["箱子", "门"],
                "location": "门口主通道",
                "level": "中",
                "reason": "箱子位于出入口，阻碍通行并可能造成绊倒。",
                "suggestion": "清理门口杂物，保持通道和出口畅通。",
            }
        ],
        "svg": {
            "zones": [("desk", 70, 70, 210, 125), ("bed", 390, 70, 180, 165), ("door", 40, 260, 100, 120)],
            "objects": [
                ("箱子", "box", 80, 305, "#f59e0b"),
                ("箱子", "box", 125, 315, "#d97706"),
            ],
        },
    },
    {
        "id": "S04",
        "title": "厨房纸张靠近灶台",
        "scene_type": "厨房",
        "summary": "纸巾和塑料袋放在灶台旁，靠近热源。",
        "objects": ["灶台", "纸巾", "塑料袋", "水槽"],
        "ground_truth": [
            {
                "type": "火灾风险",
                "objects": ["纸巾", "塑料袋", "灶台"],
                "location": "厨房灶台左侧",
                "level": "高",
                "reason": "易燃物靠近热源，点火或余温可能引发燃烧。",
                "suggestion": "将纸巾和塑料袋移至远离灶台的收纳区。",
            }
        ],
        "svg": {
            "zones": [("counter", 55, 75, 500, 150), ("sink", 370, 110, 105, 70)],
            "objects": [
                ("灶台", "stove", 180, 145, "#111827"),
                ("纸巾", "paper", 118, 138, "#f8fafc"),
                ("塑料袋", "bag", 250, 145, "#e0f2fe"),
                ("火源", "flame", 187, 130, "#ef4444"),
            ],
        },
    },
    {
        "id": "S05",
        "title": "厨房台面正常状态",
        "scene_type": "厨房",
        "summary": "厨具收纳整齐，纸张与热源保持距离。",
        "objects": ["灶台", "水槽", "锅", "纸巾盒"],
        "ground_truth": [],
        "svg": {
            "zones": [("counter", 55, 75, 500, 150), ("sink", 370, 110, 105, 70)],
            "objects": [
                ("灶台", "stove", 185, 145, "#111827"),
                ("锅", "pan", 190, 125, "#64748b"),
                ("纸巾", "paper", 470, 135, "#f8fafc"),
            ],
        },
    },
    {
        "id": "S06",
        "title": "客厅高处边缘花瓶",
        "scene_type": "客厅",
        "summary": "花瓶放在高柜边缘，下方是人员活动区域。",
        "objects": ["高柜", "花瓶", "沙发", "地毯"],
        "ground_truth": [
            {
                "type": "坠物风险",
                "objects": ["花瓶", "高柜"],
                "location": "客厅高柜外侧边缘",
                "level": "中",
                "reason": "易碎重物位于高处边缘，受碰撞后可能坠落。",
                "suggestion": "将花瓶移至柜面内侧或低处稳定位置。",
            }
        ],
        "svg": {
            "zones": [("cabinet", 395, 55, 145, 215), ("sofa", 70, 215, 230, 95), ("rug", 95, 330, 390, 70)],
            "objects": [
                ("花瓶", "vase", 505, 78, "#a855f7"),
                ("边缘", "edge", 505, 105, "#ef4444"),
            ],
        },
    },
    {
        "id": "S07",
        "title": "实验室化学品暴露",
        "scene_type": "实验室",
        "summary": "化学品瓶未收纳，放在实验台边缘且标签朝外。",
        "objects": ["实验台", "化学品", "护目镜", "柜子"],
        "ground_truth": [
            {
                "type": "危险物暴露",
                "objects": ["化学品瓶"],
                "location": "实验台前侧边缘",
                "level": "高",
                "reason": "危险化学品处于开放区域，容易被误碰或误用。",
                "suggestion": "将化学品放入专用柜，并补充标签和安全提示。",
            }
        ],
        "svg": {
            "zones": [("lab bench", 70, 105, 430, 145), ("cabinet", 505, 80, 75, 185)],
            "objects": [
                ("化学品", "bottle", 138, 170, "#10b981"),
                ("化学品", "bottle", 185, 170, "#f43f5e"),
                ("护目镜", "goggles", 285, 175, "#64748b"),
            ],
        },
    },
    {
        "id": "S08",
        "title": "走廊杂物堆积",
        "scene_type": "走廊",
        "summary": "纸箱和椅子占据走廊中央，影响多人通行。",
        "objects": ["纸箱", "椅子", "走廊", "门"],
        "ground_truth": [
            {
                "type": "通行/绊倒风险",
                "objects": ["纸箱", "椅子"],
                "location": "走廊中央通道",
                "level": "高",
                "reason": "杂物占据主要通道，影响通行和紧急疏散。",
                "suggestion": "将杂物移到储物区，保持走廊净宽。",
            }
        ],
        "svg": {
            "zones": [("corridor", 105, 55, 400, 330), ("door", 40, 105, 85, 105), ("door", 495, 105, 85, 105)],
            "objects": [
                ("纸箱", "box", 275, 220, "#f59e0b"),
                ("椅子", "chair", 335, 245, "#0f766e"),
                ("纸箱", "box", 240, 275, "#d97706"),
            ],
        },
    },
    {
        "id": "S09",
        "title": "宿舍垃圾堆积",
        "scene_type": "宿舍",
        "summary": "垃圾袋和外卖盒堆在桌下，影响卫生和管理状态。",
        "objects": ["垃圾袋", "外卖盒", "书桌", "地面"],
        "ground_truth": [
            {
                "type": "清洁度异常",
                "objects": ["垃圾袋", "外卖盒"],
                "location": "书桌下方地面",
                "level": "低",
                "reason": "生活垃圾未及时清理，可能产生异味并影响卫生。",
                "suggestion": "及时清理垃圾，保持地面和桌下区域整洁。",
            }
        ],
        "svg": {
            "zones": [("desk", 75, 80, 300, 150), ("bed", 410, 80, 145, 175)],
            "objects": [
                ("垃圾袋", "trash", 135, 275, "#334155"),
                ("外卖盒", "box", 195, 292, "#f97316"),
                ("纸团", "paper", 252, 292, "#f8fafc"),
            ],
        },
    },
    {
        "id": "S10",
        "title": "儿童可触达刀具",
        "scene_type": "客厅",
        "summary": "水果刀放在矮茶几边缘，处于儿童可触达位置。",
        "objects": ["刀具", "茶几", "沙发", "玩具"],
        "ground_truth": [
            {
                "type": "危险物暴露",
                "objects": ["水果刀"],
                "location": "客厅矮茶几边缘",
                "level": "高",
                "reason": "锋利刀具位于儿童活动区域且容易触达。",
                "suggestion": "立即将刀具收纳到高处或带锁抽屉。",
            }
        ],
        "svg": {
            "zones": [("sofa", 70, 85, 260, 90), ("coffee table", 180, 220, 230, 100), ("toy area", 430, 230, 100, 90)],
            "objects": [
                ("水果刀", "knife", 230, 245, "#ef4444"),
                ("玩具", "toy", 465, 262, "#22c55e"),
            ],
        },
    },
    {
        "id": "S11",
        "title": "水壶电源线旁积水",
        "scene_type": "厨房",
        "summary": "电热水壶旁有积水，电源线经过潮湿区域。",
        "objects": ["电热水壶", "电源线", "积水", "插座"],
        "ground_truth": [
            {
                "type": "触电风险",
                "objects": ["积水", "电源线", "电热水壶"],
                "location": "厨房台面右侧",
                "level": "高",
                "reason": "积水接近带电设备和电源线，存在漏电或短路风险。",
                "suggestion": "擦干台面积水，检查电源线并远离潮湿区域。",
            }
        ],
        "svg": {
            "zones": [("counter", 55, 75, 500, 150), ("sink", 100, 110, 105, 70)],
            "objects": [
                ("电热水壶", "kettle", 410, 140, "#64748b"),
                ("积水", "water", 372, 175, "#38bdf8"),
                ("电源线", "wire", 395, 170, "#111827"),
                ("插座", "socket", 500, 140, "#475569"),
            ],
        },
    },
    {
        "id": "S12",
        "title": "桌下半遮挡电线",
        "scene_type": "实验室",
        "summary": "桌下电线横跨通道但部分被桌腿遮挡，单视角容易漏检。",
        "objects": ["电线", "实验台", "椅子", "通道"],
        "ground_truth": [
            {
                "type": "通行/绊倒风险",
                "objects": ["电线"],
                "location": "实验台前方桌下通道",
                "level": "中",
                "reason": "电线横跨脚部通行区域，且被桌腿遮挡不易发现。",
                "suggestion": "使用线槽固定电线，并清理脚下通道。",
            }
        ],
        "svg": {
            "zones": [("lab bench", 65, 105, 430, 145), ("walkway", 90, 280, 425, 90)],
            "objects": [
                ("椅子", "chair", 180, 260, "#0f766e"),
                ("电线", "wire", 250, 305, "#111827"),
                ("桌腿遮挡", "leg", 300, 230, "#475569"),
            ],
        },
    },
]


MOCK_RESULTS = {
    "S01": {"has_risk": False, "risks": []},
    "S02": {
        "has_risk": True,
        "risks": [
            {
                "type": "触电风险",
                "objects": ["水杯", "插座"],
                "location": "书桌右侧靠墙区域",
                "level": "高",
                "reason": "液体容器靠近插座，触发液体靠近电源的规则。",
                "suggestion": "移动水杯并保持插座周围干燥。",
            }
        ],
    },
    "S03": {
        "has_risk": True,
        "risks": [
            {
                "type": "通行/绊倒风险",
                "objects": ["箱子", "门"],
                "location": "门口",
                "level": "中",
                "reason": "箱子占据出入口，可能影响通行。",
                "suggestion": "清理门口箱子。",
            }
        ],
    },
    "S04": {
        "has_risk": True,
        "risks": [
            {
                "type": "火灾风险",
                "objects": ["纸巾", "塑料袋", "灶台"],
                "location": "灶台周围",
                "level": "高",
                "reason": "易燃物靠近热源，触发火灾风险规则。",
                "suggestion": "将纸巾和塑料袋移开。",
            }
        ],
    },
    "S05": {
        "has_risk": True,
        "risks": [
            {
                "type": "火灾风险",
                "objects": ["纸巾", "灶台"],
                "location": "厨房台面",
                "level": "低",
                "reason": "模型把远处纸巾误判为靠近灶台。",
                "suggestion": "保持纸巾远离热源。",
            }
        ],
        "note": "失败案例：正常厨房被误检为火灾风险。",
    },
    "S06": {
        "has_risk": True,
        "risks": [
            {
                "type": "坠物风险",
                "objects": ["花瓶"],
                "location": "高柜边缘",
                "level": "中",
                "reason": "花瓶位于高处边缘，可能掉落。",
                "suggestion": "移到柜面内侧或低处。",
            }
        ],
    },
    "S07": {
        "has_risk": True,
        "risks": [
            {
                "type": "危险物暴露",
                "objects": ["化学品瓶"],
                "location": "实验台",
                "level": "中",
                "reason": "危险品未收纳，处于开放位置。",
                "suggestion": "收纳到专用柜。",
            }
        ],
        "note": "轻微失败：风险类别正确，但等级低估。",
    },
    "S08": {
        "has_risk": True,
        "risks": [
            {
                "type": "通行/绊倒风险",
                "objects": ["纸箱", "椅子"],
                "location": "走廊中央",
                "level": "高",
                "reason": "杂物占据主要通道。",
                "suggestion": "清理走廊杂物。",
            }
        ],
    },
    "S09": {
        "has_risk": True,
        "risks": [
            {
                "type": "清洁度异常",
                "objects": ["垃圾袋", "外卖盒"],
                "location": "书桌下方",
                "level": "低",
                "reason": "垃圾堆积影响卫生。",
                "suggestion": "及时清理垃圾。",
            }
        ],
    },
    "S10": {
        "has_risk": True,
        "risks": [
            {
                "type": "危险物暴露",
                "objects": ["水果刀"],
                "location": "茶几边缘",
                "level": "高",
                "reason": "刀具处于儿童可触达区域。",
                "suggestion": "收纳到安全位置。",
            }
        ],
    },
    "S11": {
        "has_risk": True,
        "risks": [
            {
                "type": "触电风险",
                "objects": ["积水", "电热水壶", "电源线"],
                "location": "厨房台面右侧",
                "level": "高",
                "reason": "水和电器、电源线距离过近。",
                "suggestion": "擦干积水并整理电源线。",
            }
        ],
    },
    "S12": {
        "has_risk": False,
        "risks": [],
        "note": "失败案例：半遮挡电线导致漏检。",
    },
}


def zone_svg(kind: str, x: int, y: int, w: int, h: int) -> str:
    colors = {
        "desk": ("#d9f99d", "#65a30d"),
        "bed": ("#dbeafe", "#2563eb"),
        "door": ("#fde68a", "#d97706"),
        "counter": ("#e2e8f0", "#64748b"),
        "sink": ("#bae6fd", "#0284c7"),
        "cabinet": ("#fed7aa", "#ea580c"),
        "sofa": ("#ddd6fe", "#7c3aed"),
        "rug": ("#fecdd3", "#e11d48"),
        "lab bench": ("#ccfbf1", "#0f766e"),
        "corridor": ("#f1f5f9", "#64748b"),
        "walkway": ("#f8fafc", "#94a3b8"),
        "coffee table": ("#fef3c7", "#ca8a04"),
        "toy area": ("#dcfce7", "#16a34a"),
    }.get(kind, ("#f8fafc", "#94a3b8"))
    fill, stroke = colors
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/><text x="{x+10}" y="{y+22}" class="label">{kind}</text>'


def object_svg(label: str, kind: str, x: int, y: int, color: str) -> str:
    if kind == "cup":
        shape = f'<rect x="{x-14}" y="{y-18}" width="28" height="36" rx="7" fill="{color}" stroke="#0f172a" stroke-width="2"/><path d="M{x+14} {y-6} q18 0 8 18" fill="none" stroke="#0f172a" stroke-width="2"/>'
    elif kind == "socket":
        shape = f'<rect x="{x-16}" y="{y-13}" width="32" height="26" rx="4" fill="#f8fafc" stroke="{color}" stroke-width="2"/><circle cx="{x-6}" cy="{y}" r="2.5" fill="{color}"/><circle cx="{x+6}" cy="{y}" r="2.5" fill="{color}"/>'
    elif kind == "box":
        shape = f'<rect x="{x-24}" y="{y-20}" width="48" height="40" rx="4" fill="{color}" stroke="#78350f" stroke-width="2"/><path d="M{x-24} {y-5} H{x+24}" stroke="#78350f" stroke-width="2"/>'
    elif kind == "stove":
        shape = f'<rect x="{x-36}" y="{y-22}" width="72" height="44" rx="8" fill="{color}"/><circle cx="{x-15}" cy="{y}" r="10" fill="#f8fafc"/><circle cx="{x+16}" cy="{y}" r="10" fill="#f8fafc"/>'
    elif kind == "flame":
        shape = f'<path d="M{x} {y+22} C{x-20} {y+5}, {x-2} {y-4}, {x-8} {y-24} C{x+12} {y-8}, {x+25} {y+2}, {x} {y+22} Z" fill="{color}"/>'
    elif kind == "paper":
        shape = f'<rect x="{x-22}" y="{y-16}" width="44" height="32" rx="2" fill="{color}" stroke="#94a3b8" stroke-width="2"/><path d="M{x-14} {y-3} H{x+12} M{x-14} {y+7} H{x+8}" stroke="#94a3b8" stroke-width="2"/>'
    elif kind == "bag":
        shape = f'<path d="M{x-24} {y+18} L{x-16} {y-14} Q{x} {y-32} {x+16} {y-14} L{x+24} {y+18} Z" fill="{color}" stroke="#0284c7" stroke-width="2"/>'
    elif kind == "vase":
        shape = f'<path d="M{x-12} {y-22} H{x+12} C{x+4} {y-4}, {x+24} {y+20}, {x} {y+30} C{x-24} {y+20}, {x-4} {y-4}, {x-12} {y-22} Z" fill="{color}" stroke="#581c87" stroke-width="2"/>'
    elif kind == "bottle":
        shape = f'<rect x="{x-10}" y="{y-28}" width="20" height="18" rx="3" fill="#e2e8f0" stroke="#0f172a" stroke-width="2"/><rect x="{x-17}" y="{y-10}" width="34" height="44" rx="7" fill="{color}" stroke="#0f172a" stroke-width="2"/><text x="{x}" y="{y+15}" text-anchor="middle" class="tiny">!</text>'
    elif kind == "goggles":
        shape = f'<circle cx="{x-15}" cy="{y}" r="13" fill="none" stroke="{color}" stroke-width="4"/><circle cx="{x+15}" cy="{y}" r="13" fill="none" stroke="{color}" stroke-width="4"/><path d="M{x-2} {y} H{x+2}" stroke="{color}" stroke-width="4"/>'
    elif kind == "chair":
        shape = f'<rect x="{x-22}" y="{y-20}" width="44" height="34" rx="6" fill="{color}" stroke="#134e4a" stroke-width="2"/><path d="M{x-16} {y+14} V{y+34} M{x+16} {y+14} V{y+34}" stroke="#134e4a" stroke-width="3"/>'
    elif kind == "trash":
        shape = f'<path d="M{x-22} {y+22} L{x-12} {y-20} H{x+14} L{x+22} {y+22} Z" fill="{color}" stroke="#0f172a" stroke-width="2"/><path d="M{x-10} {y-18} Q{x} {y-32} {x+12} {y-18}" fill="none" stroke="#0f172a" stroke-width="2"/>'
    elif kind == "knife":
        shape = f'<path d="M{x-35} {y+4} L{x+20} {y-8} L{x+42} {y-2} L{x+16} {y+9} Z" fill="{color}" stroke="#7f1d1d" stroke-width="2"/><rect x="{x-42}" y="{y}" width="22" height="8" rx="3" fill="#292524"/>'
    elif kind == "toy":
        shape = f'<circle cx="{x}" cy="{y}" r="22" fill="{color}" stroke="#166534" stroke-width="2"/><circle cx="{x-8}" cy="{y-5}" r="3" fill="#0f172a"/><circle cx="{x+8}" cy="{y-5}" r="3" fill="#0f172a"/>'
    elif kind == "kettle":
        shape = f'<rect x="{x-24}" y="{y-22}" width="48" height="48" rx="12" fill="{color}" stroke="#334155" stroke-width="2"/><path d="M{x+24} {y-6} q24 3 4 24 M{x-14} {y-26} H{x+14}" fill="none" stroke="#334155" stroke-width="4"/>'
    elif kind == "water":
        shape = f'<ellipse cx="{x}" cy="{y}" rx="38" ry="14" fill="{color}" opacity="0.7" stroke="#0284c7" stroke-width="2"/>'
    elif kind == "wire":
        shape = f'<path d="M{x-65} {y+16} C{x-25} {y-15}, {x+22} {y+42}, {x+70} {y}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>'
    elif kind == "line":
        shape = f'<path d="M{x} {y} L{x+32} {y-5}" stroke="{color}" stroke-width="4" stroke-dasharray="6 5"/><circle cx="{x}" cy="{y}" r="6" fill="{color}"/><circle cx="{x+32}" cy="{y-5}" r="6" fill="{color}"/>'
    elif kind == "edge":
        shape = f'<path d="M{x-40} {y} H{x+30}" stroke="{color}" stroke-width="5" stroke-dasharray="8 6"/>'
    elif kind == "leg":
        shape = f'<rect x="{x-12}" y="{y-20}" width="24" height="95" fill="{color}" opacity="0.86"/>'
    elif kind == "book":
        shape = f'<rect x="{x-26}" y="{y-16}" width="52" height="32" rx="3" fill="{color}" stroke="#14532d" stroke-width="2"/><path d="M{x} {y-16} V{y+16}" stroke="#14532d" stroke-width="2"/>'
    elif kind == "pan":
        shape = f'<circle cx="{x}" cy="{y}" r="24" fill="{color}" stroke="#334155" stroke-width="2"/><path d="M{x+20} {y} H{x+62}" stroke="#334155" stroke-width="6" stroke-linecap="round"/>'
    else:
        shape = f'<circle cx="{x}" cy="{y}" r="20" fill="{color}" stroke="#0f172a" stroke-width="2"/>'
    return f'<g>{shape}<text x="{x}" y="{y+52}" text-anchor="middle" class="object-label">{label}</text></g>'


def scene_svg(scene: dict) -> str:
    zones = "\n".join(zone_svg(*zone) for zone in scene["svg"]["zones"])
    objects = "\n".join(object_svg(*obj) for obj in scene["svg"]["objects"])
    risks = scene["ground_truth"]
    badge = "正常" if not risks else "风险"
    badge_color = "#16a34a" if not risks else "#dc2626"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 430" width="640" height="430" role="img" aria-label="{scene["title"]}">
  <defs>
    <style>
      .title {{ font: 700 22px "Microsoft YaHei", Arial, sans-serif; fill: #0f172a; }}
      .label {{ font: 600 13px "Microsoft YaHei", Arial, sans-serif; fill: #334155; }}
      .object-label {{ font: 700 14px "Microsoft YaHei", Arial, sans-serif; fill: #0f172a; }}
      .tiny {{ font: 800 18px Arial, sans-serif; fill: #fff; }}
      .summary {{ font: 500 13px "Microsoft YaHei", Arial, sans-serif; fill: #475569; }}
    </style>
  </defs>
  <rect width="640" height="430" rx="18" fill="#f8fafc"/>
  <rect x="24" y="48" width="592" height="348" rx="12" fill="#fff" stroke="#cbd5e1" stroke-width="2"/>
  <text x="30" y="30" class="title">{scene["id"]} {scene["title"]}</text>
  <rect x="548" y="12" width="68" height="28" rx="14" fill="{badge_color}"/>
  <text x="582" y="31" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="14" font-weight="700" fill="#fff">{badge}</text>
  {zones}
  {objects}
  <text x="34" y="415" class="summary">{scene["summary"]}</text>
</svg>
'''


def public_scene(scene: dict) -> dict:
    return {
        "id": scene["id"],
        "title": scene["title"],
        "scene_type": scene["scene_type"],
        "summary": scene["summary"],
        "objects": scene["objects"],
        "image": f"assets/scenes/{scene['id']}.svg",
        "ground_truth": scene["ground_truth"],
    }


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    scenes = []
    for scene in SCENES:
        (ASSETS / f"{scene['id']}.svg").write_text(scene_svg(scene), encoding="utf-8")
        scenes.append(public_scene(scene))

    (DATA / "risk_rules.json").write_text(json.dumps(RISK_RULES, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "mock_vlm_results.json").write_text(json.dumps(MOCK_RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")

    data_js = (
        "window.RISK_RULES = "
        + json.dumps(RISK_RULES, ensure_ascii=False, indent=2)
        + ";\nwindow.DEMO_SCENES = "
        + json.dumps(scenes, ensure_ascii=False, indent=2)
        + ";\nwindow.MOCK_RESULTS = "
        + json.dumps(MOCK_RESULTS, ensure_ascii=False, indent=2)
        + ";\n"
    )
    (ROOT / "data.js").write_text(data_js, encoding="utf-8")
    print(f"Generated {len(scenes)} scenes in {ROOT}")


if __name__ == "__main__":
    main()
