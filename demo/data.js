window.RISK_RULES = [
  {
    "id": "electric_shock",
    "name": "触电风险",
    "rule": "液体、积水或潮湿物体靠近插座、电器、电线时判定为触电风险。",
    "level_hint": "靠近插座或正在运行电器时为高风险。"
  },
  {
    "id": "fire",
    "name": "火灾风险",
    "rule": "纸张、布料、塑料袋等易燃物靠近灶台、电暖器、热水壶等热源时判定为火灾风险。",
    "level_hint": "易燃物与热源距离很近或热源开启时为高风险。"
  },
  {
    "id": "trip_or_block",
    "name": "通行/绊倒风险",
    "rule": "箱子、椅子、电线、杂物位于门口、走廊、主要通道时判定为通行或绊倒风险。",
    "level_hint": "阻挡出口或夜间不易观察的位置为中高风险。"
  },
  {
    "id": "falling_object",
    "name": "坠物风险",
    "rule": "重物、花瓶、箱子等放在高处边缘或不稳定堆叠时判定为坠物风险。",
    "level_hint": "位于头顶高度或人常经过区域上方时为高风险。"
  },
  {
    "id": "danger_exposure",
    "name": "危险物暴露",
    "rule": "刀具、化学品、工具等危险物处于儿童或无关人员易触达区域时判定为暴露风险。",
    "level_hint": "无收纳、无标签或靠近活动区域时为中高风险。"
  },
  {
    "id": "cleanliness",
    "name": "清洁度异常",
    "rule": "垃圾、污渍、食物残渣、杂乱堆积影响环境卫生或管理状态时判定为清洁度异常。",
    "level_hint": "影响通行或靠近电器、热源时风险升级。"
  }
];
window.DEMO_SCENES = [
  {
    "id": "S01",
    "title": "宿舍桌面正常状态",
    "scene_type": "宿舍",
    "summary": "水杯位于桌面中央，插座远离液体，通道保持畅通。",
    "objects": [
      "书桌",
      "水杯",
      "插座",
      "床",
      "门"
    ],
    "image": "assets/scenes/S01.svg",
    "ground_truth": []
  },
  {
    "id": "S02",
    "title": "水杯靠近插座",
    "scene_type": "宿舍",
    "summary": "桌角水杯靠近墙面插座，液体与电源区域距离过近。",
    "objects": [
      "水杯",
      "插座",
      "书桌",
      "床"
    ],
    "image": "assets/scenes/S02.svg",
    "ground_truth": [
      {
        "type": "触电风险",
        "objects": [
          "水杯",
          "插座"
        ],
        "location": "书桌右侧靠墙区域",
        "level": "高",
        "reason": "液体容器靠近插座，若倾倒可能导致短路或触电。",
        "suggestion": "将水杯移到远离插座的位置，并保持插座周围干燥。"
      }
    ]
  },
  {
    "id": "S03",
    "title": "门口箱子阻塞",
    "scene_type": "宿舍",
    "summary": "收纳箱堆在门口，影响出入和紧急疏散。",
    "objects": [
      "箱子",
      "门",
      "床",
      "书桌"
    ],
    "image": "assets/scenes/S03.svg",
    "ground_truth": [
      {
        "type": "通行/绊倒风险",
        "objects": [
          "箱子",
          "门"
        ],
        "location": "门口主通道",
        "level": "中",
        "reason": "箱子位于出入口，阻碍通行并可能造成绊倒。",
        "suggestion": "清理门口杂物，保持通道和出口畅通。"
      }
    ]
  },
  {
    "id": "S04",
    "title": "厨房纸张靠近灶台",
    "scene_type": "厨房",
    "summary": "纸巾和塑料袋放在灶台旁，靠近热源。",
    "objects": [
      "灶台",
      "纸巾",
      "塑料袋",
      "水槽"
    ],
    "image": "assets/scenes/S04.svg",
    "ground_truth": [
      {
        "type": "火灾风险",
        "objects": [
          "纸巾",
          "塑料袋",
          "灶台"
        ],
        "location": "厨房灶台左侧",
        "level": "高",
        "reason": "易燃物靠近热源，点火或余温可能引发燃烧。",
        "suggestion": "将纸巾和塑料袋移至远离灶台的收纳区。"
      }
    ]
  },
  {
    "id": "S05",
    "title": "厨房台面正常状态",
    "scene_type": "厨房",
    "summary": "厨具收纳整齐，纸张与热源保持距离。",
    "objects": [
      "灶台",
      "水槽",
      "锅",
      "纸巾盒"
    ],
    "image": "assets/scenes/S05.svg",
    "ground_truth": []
  },
  {
    "id": "S06",
    "title": "客厅高处边缘花瓶",
    "scene_type": "客厅",
    "summary": "花瓶放在高柜边缘，下方是人员活动区域。",
    "objects": [
      "高柜",
      "花瓶",
      "沙发",
      "地毯"
    ],
    "image": "assets/scenes/S06.svg",
    "ground_truth": [
      {
        "type": "坠物风险",
        "objects": [
          "花瓶",
          "高柜"
        ],
        "location": "客厅高柜外侧边缘",
        "level": "中",
        "reason": "易碎重物位于高处边缘，受碰撞后可能坠落。",
        "suggestion": "将花瓶移至柜面内侧或低处稳定位置。"
      }
    ]
  },
  {
    "id": "S07",
    "title": "实验室化学品暴露",
    "scene_type": "实验室",
    "summary": "化学品瓶未收纳，放在实验台边缘且标签朝外。",
    "objects": [
      "实验台",
      "化学品",
      "护目镜",
      "柜子"
    ],
    "image": "assets/scenes/S07.svg",
    "ground_truth": [
      {
        "type": "危险物暴露",
        "objects": [
          "化学品瓶"
        ],
        "location": "实验台前侧边缘",
        "level": "高",
        "reason": "危险化学品处于开放区域，容易被误碰或误用。",
        "suggestion": "将化学品放入专用柜，并补充标签和安全提示。"
      }
    ]
  },
  {
    "id": "S08",
    "title": "走廊杂物堆积",
    "scene_type": "走廊",
    "summary": "纸箱和椅子占据走廊中央，影响多人通行。",
    "objects": [
      "纸箱",
      "椅子",
      "走廊",
      "门"
    ],
    "image": "assets/scenes/S08.svg",
    "ground_truth": [
      {
        "type": "通行/绊倒风险",
        "objects": [
          "纸箱",
          "椅子"
        ],
        "location": "走廊中央通道",
        "level": "高",
        "reason": "杂物占据主要通道，影响通行和紧急疏散。",
        "suggestion": "将杂物移到储物区，保持走廊净宽。"
      }
    ]
  },
  {
    "id": "S09",
    "title": "宿舍垃圾堆积",
    "scene_type": "宿舍",
    "summary": "垃圾袋和外卖盒堆在桌下，影响卫生和管理状态。",
    "objects": [
      "垃圾袋",
      "外卖盒",
      "书桌",
      "地面"
    ],
    "image": "assets/scenes/S09.svg",
    "ground_truth": [
      {
        "type": "清洁度异常",
        "objects": [
          "垃圾袋",
          "外卖盒"
        ],
        "location": "书桌下方地面",
        "level": "低",
        "reason": "生活垃圾未及时清理，可能产生异味并影响卫生。",
        "suggestion": "及时清理垃圾，保持地面和桌下区域整洁。"
      }
    ]
  },
  {
    "id": "S10",
    "title": "儿童可触达刀具",
    "scene_type": "客厅",
    "summary": "水果刀放在矮茶几边缘，处于儿童可触达位置。",
    "objects": [
      "刀具",
      "茶几",
      "沙发",
      "玩具"
    ],
    "image": "assets/scenes/S10.svg",
    "ground_truth": [
      {
        "type": "危险物暴露",
        "objects": [
          "水果刀"
        ],
        "location": "客厅矮茶几边缘",
        "level": "高",
        "reason": "锋利刀具位于儿童活动区域且容易触达。",
        "suggestion": "立即将刀具收纳到高处或带锁抽屉。"
      }
    ]
  },
  {
    "id": "S11",
    "title": "水壶电源线旁积水",
    "scene_type": "厨房",
    "summary": "电热水壶旁有积水，电源线经过潮湿区域。",
    "objects": [
      "电热水壶",
      "电源线",
      "积水",
      "插座"
    ],
    "image": "assets/scenes/S11.svg",
    "ground_truth": [
      {
        "type": "触电风险",
        "objects": [
          "积水",
          "电源线",
          "电热水壶"
        ],
        "location": "厨房台面右侧",
        "level": "高",
        "reason": "积水接近带电设备和电源线，存在漏电或短路风险。",
        "suggestion": "擦干台面积水，检查电源线并远离潮湿区域。"
      }
    ]
  },
  {
    "id": "S12",
    "title": "桌下半遮挡电线",
    "scene_type": "实验室",
    "summary": "桌下电线横跨通道但部分被桌腿遮挡，单视角容易漏检。",
    "objects": [
      "电线",
      "实验台",
      "椅子",
      "通道"
    ],
    "image": "assets/scenes/S12.svg",
    "ground_truth": [
      {
        "type": "通行/绊倒风险",
        "objects": [
          "电线"
        ],
        "location": "实验台前方桌下通道",
        "level": "中",
        "reason": "电线横跨脚部通行区域，且被桌腿遮挡不易发现。",
        "suggestion": "使用线槽固定电线，并清理脚下通道。"
      }
    ]
  }
];
window.MOCK_RESULTS = {
  "S01": {
    "has_risk": false,
    "risks": []
  },
  "S02": {
    "has_risk": true,
    "risks": [
      {
        "type": "触电风险",
        "objects": [
          "水杯",
          "插座"
        ],
        "location": "书桌右侧靠墙区域",
        "level": "高",
        "reason": "液体容器靠近插座，触发液体靠近电源的规则。",
        "suggestion": "移动水杯并保持插座周围干燥。"
      }
    ]
  },
  "S03": {
    "has_risk": true,
    "risks": [
      {
        "type": "通行/绊倒风险",
        "objects": [
          "箱子",
          "门"
        ],
        "location": "门口",
        "level": "中",
        "reason": "箱子占据出入口，可能影响通行。",
        "suggestion": "清理门口箱子。"
      }
    ]
  },
  "S04": {
    "has_risk": true,
    "risks": [
      {
        "type": "火灾风险",
        "objects": [
          "纸巾",
          "塑料袋",
          "灶台"
        ],
        "location": "灶台周围",
        "level": "高",
        "reason": "易燃物靠近热源，触发火灾风险规则。",
        "suggestion": "将纸巾和塑料袋移开。"
      }
    ]
  },
  "S05": {
    "has_risk": true,
    "risks": [
      {
        "type": "火灾风险",
        "objects": [
          "纸巾",
          "灶台"
        ],
        "location": "厨房台面",
        "level": "低",
        "reason": "模型把远处纸巾误判为靠近灶台。",
        "suggestion": "保持纸巾远离热源。"
      }
    ],
    "note": "失败案例：正常厨房被误检为火灾风险。"
  },
  "S06": {
    "has_risk": true,
    "risks": [
      {
        "type": "坠物风险",
        "objects": [
          "花瓶"
        ],
        "location": "高柜边缘",
        "level": "中",
        "reason": "花瓶位于高处边缘，可能掉落。",
        "suggestion": "移到柜面内侧或低处。"
      }
    ]
  },
  "S07": {
    "has_risk": true,
    "risks": [
      {
        "type": "危险物暴露",
        "objects": [
          "化学品瓶"
        ],
        "location": "实验台",
        "level": "中",
        "reason": "危险品未收纳，处于开放位置。",
        "suggestion": "收纳到专用柜。"
      }
    ],
    "note": "轻微失败：风险类别正确，但等级低估。"
  },
  "S08": {
    "has_risk": true,
    "risks": [
      {
        "type": "通行/绊倒风险",
        "objects": [
          "纸箱",
          "椅子"
        ],
        "location": "走廊中央",
        "level": "高",
        "reason": "杂物占据主要通道。",
        "suggestion": "清理走廊杂物。"
      }
    ]
  },
  "S09": {
    "has_risk": true,
    "risks": [
      {
        "type": "清洁度异常",
        "objects": [
          "垃圾袋",
          "外卖盒"
        ],
        "location": "书桌下方",
        "level": "低",
        "reason": "垃圾堆积影响卫生。",
        "suggestion": "及时清理垃圾。"
      }
    ]
  },
  "S10": {
    "has_risk": true,
    "risks": [
      {
        "type": "危险物暴露",
        "objects": [
          "水果刀"
        ],
        "location": "茶几边缘",
        "level": "高",
        "reason": "刀具处于儿童可触达区域。",
        "suggestion": "收纳到安全位置。"
      }
    ]
  },
  "S11": {
    "has_risk": true,
    "risks": [
      {
        "type": "触电风险",
        "objects": [
          "积水",
          "电热水壶",
          "电源线"
        ],
        "location": "厨房台面右侧",
        "level": "高",
        "reason": "水和电器、电源线距离过近。",
        "suggestion": "擦干积水并整理电源线。"
      }
    ]
  },
  "S12": {
    "has_risk": false,
    "risks": [],
    "note": "失败案例：半遮挡电线导致漏检。"
  }
};
