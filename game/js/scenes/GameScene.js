/**
 * GameScene - 主游戏场景
 *
 * 负责：房间渲染、家具放置、机器人控制、碰撞检测、风险触发、VLM调用、HUD
 */
class GameScene extends Phaser.Scene {
  constructor() {
    super("GameScene");
  }

  create() {
    // 加载所有场景配置
    this.allScenes = {};
    var sceneIds = ["dormitory", "corridor", "kitchen", "living_room", "laboratory"];
    sceneIds.forEach(function (id) {
      var cfg = this.cache.json.get(id);
      if (cfg) this.allScenes[id] = cfg;
    }.bind(this));

    // 回退：如果没有加载到任何场景配置，使用内嵌配置
    if (Object.keys(this.allScenes).length === 0) {
      this.allScenes["dormitory"] = DORMITORY_CONFIG;
    }

    // 全局游戏状态（跨房间）
    this.risksFound = 0;
    this.risksChecked = 0;
    this.currentRiskZone = null;
    this.isInspecting = false;
    this.patrolStartTime = Date.now();
    this.checkedZones = new Set();
    this.inspectionResults = [];
    this.currentSceneId = "dormitory";

    // 计算所有房间的风险区域总数
    this.totalRiskZones = 0;
    Object.values(this.allScenes).forEach(function (cfg) {
      this.totalRiskZones += (cfg.risk_zones || []).length;
    }.bind(this));

    // API 基础路径
    this.apiBase = this.getApiBase();

    // 加载初始场景
    this.loadScene("dormitory");

    // 隐藏加载屏
    var loading = document.getElementById("loadingScreen");
    if (loading) loading.style.display = "none";

    // 提示信息
    this.showTip("使用 WASD 或方向键移动 | 走到红色区域自动检测 | 走到门口按 E 切换房间");
  }

  /** 加载场景 */
  loadScene(sceneId) {
    // 清除当前场景的所有对象
    if (this.sceneConfig) {
      // 清除物理组
      if (this.wallGroup) this.wallGroup.clear(true, true);
      if (this.furnitureGroup) this.furnitureGroup.clear(true, true);
      // 清除所有非机器人、非HUD的游戏对象
      this.children.list.forEach(function (child) {
        if (child !== this.robot &&
            child !== this.hudBg &&
            child !== this.hudRoom &&
            child !== this.hudRisks &&
            child !== this.hudChecked &&
            child !== this.hudTime &&
            child !== this.hudTip &&
            child !== this.scanRing &&
            child !== this.tipBg &&
            !child.__isPersistent) {
          child.destroy();
        }
      }.bind(this));
    }

    this.currentSceneId = sceneId;
    this.sceneConfig = this.allScenes[sceneId];
    if (!this.sceneConfig) {
      console.error("Scene not found:", sceneId);
      return;
    }

    // 重置当前场景的局部状态
    this.currentRiskZone = null;
    this.riskZones = this.sceneConfig.risk_zones || [];
    this.riskZoneRects = [];
    this.riskZoneGraphics = [];
    this.doors = this.sceneConfig.doors || [];
    this.doorRects = [];

    // 渲染场景
    this.drawFloor();
    this.drawWalls();
    this.drawFurniture();
    this.drawRiskZones();
    this.drawDoors();

    // 如果是首次加载，创建机器人和HUD
    if (!this.robot) {
      this.createRobot();
      this.setupCollisions();
      this.setupInput();
      this.createHUD();
    } else {
      // 切换房间：重置机器人位置
      var spawn = this.sceneConfig.spawn_point || { x: 400, y: 400 };
      this.robot.body.reset(spawn.x, spawn.y);
      this.robot.setVelocity(0, 0);
      // 重新设置碰撞
      this.setupCollisions();
    }

    // 更新 HUD 显示当前房间
    if (this.hudRoom) {
      this.hudRoom.setText("📍 " + this.sceneConfig.scene_name);
    }
    if (this.hudChecked) {
      this.hudChecked.setText("✓ 已检测: " + this.risksChecked + "/" + this.totalRiskZones);
    }

    // 显示房间切换提示
    this.showTip("进入：" + this.sceneConfig.scene_name);
  }

  getApiBase() {
    if (window.location.port === "8000") return "";
    return "http://localhost:8000";
  }

  /** 绘制木地板 */
  drawFloor() {
    var w = this.sceneConfig.width;
    var h = this.sceneConfig.height;
    var ts = this.sceneConfig.tile_size || 32;
    for (var x = 0; x < w; x++) {
      for (var y = 0; y < h; y++) {
        this.add.image(x * ts, y * ts, "floor").setOrigin(0, 0);
      }
    }
  }

  /** 绘制墙壁 */
  drawWalls() {
    var walls = this.sceneConfig.walls || [];
    this.wallGroup = this.physics.add.staticGroup();

    walls.forEach(function (w) {
      // 渲染墙壁
      var wall = this.add.rectangle(
        w.x + w.width / 2,
        w.y + w.height / 2,
        w.width,
        w.height,
        0x4a4a5a
      );
      wall.setStrokeStyle(2, 0x2a2a3a);

      // 物理碰撞体
      var body = this.physics.add.staticImage(
        w.x + w.width / 2,
        w.y + w.height / 2
      );
      body.setSize(w.width, w.height);
      body.setDisplaySize(w.width, w.height);
      body.setVisible(false);
      body.refreshBody();
      this.wallGroup.add(body);
    }, this);
  }

  /** 绘制家具 */
  drawFurniture() {
    this.furnitureGroup = this.physics.add.staticGroup();
    var furniture = this.sceneConfig.furniture || [];

    furniture.forEach(function (f) {
      // 用 Graphics 绘制家具
      var g = this.add.graphics();
      var color = this.parseColor(f.color || "#888888");

      // 阴影
      g.fillStyle(0x000000, 0.2);
      g.fillRoundedRect(f.x + 2, f.y + 3, f.width, f.height, 4);

      // 主体
      g.fillStyle(color, 1);
      g.fillRoundedRect(f.x, f.y, f.width, f.height, 4);

      // 边框
      g.lineStyle(2, 0x000000, 0.3);
      g.strokeRoundedRect(f.x, f.y, f.width, f.height, 4);

      // 高光
      g.fillStyle(0xffffff, 0.15);
      g.fillRoundedRect(f.x + 2, f.y + 2, f.width - 4, 6, 2);

      // 标签
      if (f.label) {
        var fontSize = f.width < 50 ? 10 : 12;
        var label = this.add.text(
          f.x + f.width / 2,
          f.y + f.height / 2,
          f.label,
          {
            fontSize: fontSize + "px",
            color: "#ffffff",
            fontStyle: "bold",
            stroke: "#000000",
            strokeThickness: 2,
          }
        );
        label.setOrigin(0.5, 0.5);
      }

      // 碰撞体（仅 collidable 家具）
      if (f.collidable) {
        var body = this.physics.add.staticImage(
          f.x + f.width / 2,
          f.y + f.height / 2
        );
        body.setSize(f.width, f.height);
        body.setVisible(false);
        body.refreshBody();
        this.furnitureGroup.add(body);
      }
    }, this);
  }

  /** 绘制风险区域 */
  drawRiskZones() {
    this.riskZones = this.sceneConfig.risk_zones || [];
    this.riskZoneGraphics = [];
    this.riskZoneRects = [];

    this.riskZones.forEach(function (rz, idx) {
      // 风险区域可视化（半透明红色）
      var g = this.add.graphics();
      g.fillStyle(0xef4444, 0.1);
      g.fillRect(rz.x, rz.y, rz.width, rz.height);
      g.lineStyle(2, 0xef4444, 0.4);
      g.strokeRect(rz.x, rz.y, rz.width, rz.height);

      // 虚线边框
      g.lineStyle(2, 0xef4444, 0.6);
      var dashLen = 6;
      var gapLen = 4;
      // 上下边
      for (var dx = 0; dx < rz.width; dx += dashLen + gapLen) {
        var w = Math.min(dashLen, rz.width - dx);
        g.strokeRect(rz.x + dx, rz.y, w, 0);
        g.strokeRect(rz.x + dx, rz.y + rz.height, w, 0);
      }

      // 风险类型标签
      var label = this.add.text(
        rz.x + rz.width / 2,
        rz.y - 8,
        "⚠ " + rz.risk_type,
        {
          fontSize: "11px",
          color: "#ef4444",
          fontStyle: "bold",
          stroke: "#000000",
          strokeThickness: 2,
        }
      );
      label.setOrigin(0.5, 1);

      // 脉冲效果
      this.tweens.add({
        targets: g,
        alpha: 0.4,
        duration: 1000,
        yoyo: true,
        repeat: -1,
        ease: "Sine.easeInOut",
      });

      this.riskZoneGraphics.push({ graphic: g, label: label, config: rz, index: idx });
      this.riskZoneRects.push(
        new Phaser.Geom.Rectangle(rz.x, rz.y, rz.width, rz.height)
      );
    }, this);
  }

  /** 绘制门 */
  drawDoors() {
    var doors = this.doors || [];
    this.doorRects = [];

    doors.forEach(function (door) {
      // 门洞区域 - 绿色发光
      var g = this.add.graphics();
      g.fillStyle(0x22c55e, 0.15);
      g.fillRect(door.x, door.y, 32, 80);
      g.lineStyle(2, 0x22c55e, 0.6);
      g.strokeRect(door.x, door.y, 32, 80);
      g.setDepth(5);

      // 门标签
      var label = this.add.text(
        door.x + 16,
        door.y + 40,
        "🚪\n" + (door.label || ""),
        {
          fontSize: "10px",
          color: "#22c55e",
          fontStyle: "bold",
          align: "center",
          stroke: "#000000",
          strokeThickness: 2,
        }
      );
      label.setOrigin(0.5, 0.5);
      label.setDepth(6);

      // 脉冲动画
      this.tweens.add({
        targets: g,
        alpha: 0.5,
        duration: 800,
        yoyo: true,
        repeat: -1,
        ease: "Sine.easeInOut",
      });

      this.doorRects.push({
        rect: new Phaser.Geom.Rectangle(door.x, door.y, 32, 80),
        door: door
      });
    }, this);
  }

  /** 创建机器人 */
  createRobot() {
    var spawn = this.sceneConfig.spawn_point || { x: 400, y: 400 };
    this.robot = this.physics.add.sprite(spawn.x, spawn.y, "robot_down");
    this.robot.setSize(20, 24);
    this.robot.setCollideWorldBounds(true);
    this.robot.setDepth(10);

    // 行走动画
    this.robotDirection = "down";
    this.isMoving = false;

    // 机器人头顶光圈
    this.robotGlow = this.add.graphics();
    this.robotGlow.setDepth(9);

    // 机器人扫描范围指示
    this.scanRing = this.add.graphics();
    this.scanRing.setDepth(8);
  }

  /** 设置碰撞 */
  setupCollisions() {
    if (this.wallGroup) {
      this.physics.add.collider(this.robot, this.wallGroup);
    }
    if (this.furnitureGroup) {
      this.physics.add.collider(this.robot, this.furnitureGroup);
    }

    // 世界边界
    this.physics.world.setBounds(32, 32, 800 - 64, 600 - 64);
  }

  /** 设置键盘输入 */
  setupInput() {
    this.cursors = this.input.keyboard.createCursorKeys();
    this.wasd = this.input.keyboard.addKeys({
      up: Phaser.Input.Keyboard.KeyCodes.W,
      down: Phaser.Input.Keyboard.KeyCodes.S,
      left: Phaser.Input.Keyboard.KeyCodes.A,
      right: Phaser.Input.Keyboard.KeyCodes.D,
    });

    // E 键交互
    this.input.keyboard.on("keydown-E", function () {
      if (this.isInspecting) return;

      // 优先检查是否在门附近
      var nearDoor = this.checkDoorProximity();
      if (nearDoor) {
        this.enterDoor(nearDoor);
        return;
      }

      // 其次检查风险区域手动触发
      if (this.currentRiskZone) {
        this.triggerInspection(this.currentRiskZone);
      }
    }, this);
  }

  /** 检查是否在门附近 */
  checkDoorProximity() {
    if (!this.doorRects) return null;
    for (var i = 0; i < this.doorRects.length; i++) {
      if (this.doorRects[i].rect.contains(this.robot.x, this.robot.y)) {
        return this.doorRects[i].door;
      }
    }
    // 扩大检测范围（门附近 30px 内）
    for (var j = 0; j < this.doorRects.length; j++) {
      var r = this.doorRects[j].rect;
      var expanded = new Phaser.Geom.Rectangle(r.x - 20, r.y - 20, r.width + 40, r.height + 40);
      if (expanded.contains(this.robot.x, this.robot.y)) {
        return this.doorRects[j].door;
      }
    }
    return null;
  }

  /** 进入门（切换房间） */
  enterDoor(door) {
    this.showTip("前往：" + (door.label || door.target_scene));
    this.time.delayedCall(200, function () {
      this.loadScene(door.target_scene);
    }.bind(this));
  }

  /** 每帧更新 */
  update() {
    this.handleMovement();
    this.updateRobotGlow();
    this.checkRiskZones();
    this.checkDoorHint();
  }

  /** 检查门附近并显示提示 */
  checkDoorHint() {
    var nearDoor = this.checkDoorProximity();
    if (nearDoor) {
      this.hudTip.setText("按 E 前往 " + (nearDoor.label || nearDoor.target_scene));
    } else if (this.currentRiskZone) {
      this.hudTip.setText("按 E 手动检测 | 红色区域自动检测中");
    } else {
      this.hudTip.setText("WASD/方向键移动 | 走到红色区域自动检测 | 走到门口按 E 切换房间");
    }
  }

  /** 处理移动 */
  handleMovement() {
    var speed = 180;
    var vx = 0;
    var vy = 0;

    if (this.cursors.left.isDown || this.wasd.left.isDown) {
      vx = -speed;
      this.robotDirection = "left";
    } else if (this.cursors.right.isDown || this.wasd.right.isDown) {
      vx = speed;
      this.robotDirection = "right";
    }

    if (this.cursors.up.isDown || this.wasd.up.isDown) {
      vy = -speed;
      this.robotDirection = "up";
    } else if (this.cursors.down.isDown || this.wasd.down.isDown) {
      vy = speed;
      this.robotDirection = "down";
    }

    // 对角线移动归一化
    if (vx !== 0 && vy !== 0) {
      vx *= 0.707;
      vy *= 0.707;
    }

    this.robot.setVelocity(vx, vy);
    this.isMoving = vx !== 0 || vy !== 0;

    // 切换方向纹理
    if (this.isMoving) {
      var texKey = "robot_" + this.robotDirection;
      if (this.robot.texture.key !== texKey) {
        this.robot.setTexture(texKey);
      }

      // 行走弹跳效果
      var bounce = Math.sin(this.time.now * 0.012) * 1.5;
      this.robot.setOffset(0, -bounce);
    }
  }

  /** 更新机器人头顶光圈 */
  updateRobotGlow() {
    this.robotGlow.clear();
    var pulse = 0.5 + Math.sin(this.time.now * 0.003) * 0.3;

    this.robotGlow.fillStyle(0x3b82f6, pulse * 0.2);
    this.robotGlow.fillCircle(this.robot.x, this.robot.y, 30);

    this.robotGlow.lineStyle(1, 0x60a5fa, pulse * 0.4);
    this.robotGlow.strokeCircle(this.robot.x, this.robot.y, 25);
  }

  /** 检查是否在风险区域内 */
  checkRiskZones() {
    if (this.isInspecting) return;

    var robotPoint = new Phaser.Geom.Point(this.robot.x, this.robot.y);
    var inZone = null;

    for (var i = 0; i < this.riskZoneRects.length; i++) {
      if (this.riskZoneRects[i].contains(this.robot.x, this.robot.y)) {
        inZone = this.riskZones[i];
        break;
      }
    }

    if (inZone && (!this.currentRiskZone || this.currentRiskZone.id !== inZone.id)) {
      // 进入新风险区域
      this.currentRiskZone = inZone;
      this.onEnterRiskZone(inZone);
    } else if (!inZone && this.currentRiskZone) {
      // 离开风险区域
      this.currentRiskZone = null;
      this.onLeaveRiskZone();
    }

    // 更新扫描环
    this.scanRing.clear();
    if (this.currentRiskZone) {
      var ringPulse = 0.3 + Math.sin(this.time.now * 0.008) * 0.2;
      this.scanRing.lineStyle(2, 0xef4444, ringPulse);
      this.scanRing.strokeCircle(this.robot.x, this.robot.y, 40);
      this.scanRing.lineStyle(1, 0xef4444, ringPulse * 0.5);
      this.scanRing.strokeCircle(this.robot.x, this.robot.y, 55);
    }
  }

  /** 进入风险区域 */
  onEnterRiskZone(zone) {
    // 高亮该区域
    var gData = this.riskZoneGraphics.find(function (g) {
      return g.config.id === zone.id;
    });
    if (gData) {
      this.tweens.add({
        targets: gData.graphic,
        alpha: 0.8,
        duration: 300,
      });
    }

    // 如果该区域还没检查过，自动触发
    if (!this.checkedZones.has(zone.id)) {
      this.showTip("⚠ 进入风险区域：" + zone.risk_type + "，正在启动检测...");
      // 延迟 500ms 自动触发检测
      this.time.delayedCall(500, function () {
        if (this.currentRiskZone && this.currentRiskZone.id === zone.id && !this.isInspecting) {
          this.triggerInspection(zone);
        }
      }, [], this);
    } else {
      this.showTip("已检测过此区域（" + zone.risk_type + "）");
    }
  }

  /** 离开风险区域 */
  onLeaveRiskZone() {
    // 恢复脉冲效果
    this.riskZoneGraphics.forEach(function (gData) {
      this.tweens.add({
        targets: gData.graphic,
        alpha: 0.4,
        duration: 300,
      });
    }, this);
  }

  /** 触发 VLM 检测 */
  triggerInspection(zone) {
    if (this.isInspecting) return;
    this.isInspecting = true;
    this.robot.setVelocity(0, 0);

    // 显示扫描中面板（含相机图片预览）
    this.showScanningPanel(zone);

    // 加载相机图片并发送给 VLM
    var self = this;
    var imagePath = zone.camera_image;

    if (!imagePath) {
      // 没有相机图片，使用 mock 模式
      this.callInspectApiWithMock(zone);
      return;
    }

    // 构建完整 URL（相对于游戏页面）
    var baseUrl = window.location.pathname.replace(/\/index\.html$/, "");
    var fullUrl = baseUrl + "/" + imagePath;

    // fetch 图片文件 -> 转 File -> 发送 API
    fetch(fullUrl)
      .then(function (res) {
        if (!res.ok) throw new Error("相机图片加载失败: " + res.status);
        return res.blob();
      })
      .then(function (blob) {
        var fileName = imagePath.split("/").pop();
        var file = new File([blob], fileName, { type: blob.type || "image/jpeg" });
        self.callInspectApi(file, zone);
      })
      .catch(function (err) {
        // 图片加载失败，降级为 mock
        console.warn("相机图片加载失败，降级为 mock:", err.message);
        self.callInspectApiWithMock(zone);
      });
  }

  /** Mock 降级调用（无相机图片时） */
  callInspectApiWithMock(zone) {
    var self = this;
    var formData = new FormData();
    // 创建一个 1x1 空白图片占位
    var canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    canvas.toBlob(function (blob) {
      var file = new File([blob], "placeholder.png", { type: "image/png" });
      formData.append("file", file);
      formData.append("provider_name", "mock");
      formData.append("prompt_id", "risk_inspection_v1");
      if (zone.mock_scene) {
        formData.append("mock_scene", zone.mock_scene);
      }
      self.sendInspectRequest(formData, zone);
    }, "image/png");
  }

  /** 调用 /api/inspect（使用真实 provider） */
  callInspectApi(file, zone) {
    var settings = window.GAME_SETTINGS || {};
    var provider = settings.provider || "mock";
    var apiKey = settings.apiKey || "";
    var promptId = settings.promptId || "game_inspection_v1";

    var formData = new FormData();
    formData.append("file", file);
    formData.append("provider_name", provider);
    formData.append("prompt_id", promptId);

    if (apiKey) {
      formData.append("api_key", apiKey);
    }

    // mock 模式下传入 scene 获取预设结果
    if (provider === "mock" && zone && zone.mock_scene) {
      formData.append("mock_scene", zone.mock_scene);
    }

    this.sendInspectRequest(formData, zone);
  }

  /** 发送 API 请求 */
  sendInspectRequest(formData, zone) {
    var self = this;
    fetch(self.apiBase + "/api/inspect", {
      method: "POST",
      body: formData,
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        self.onInspectionComplete(data, zone);
      })
      .catch(function (err) {
        self.onInspectionError(err.message, zone);
      });
  }

  /** 检测完成 */
  onInspectionComplete(data, zone) {
    this.isInspecting = false;
    this.checkedZones.add(zone.id);
    this.risksChecked++;

    var success = data.success;
    var riskData = data.data || {};
    var hasRisk = riskData.has_risk || false;

    if (hasRisk) {
      this.risksFound++;
    }

    // 记录检测结果用于汇总
    this.inspectionResults.push({
      zone: zone,
      success: success,
      hasRisk: hasRisk,
      risks: riskData.risks || [],
      provider: data.provider || (window.GAME_SETTINGS || {}).provider || "mock"
    });

    // 更新 HUD
    this.updateHUD();

    // 显示结果面板
    this.showRiskResult(data, zone);
  }

  /** 检查是否全部巡逻完成 */
  isPatrolComplete() {
    return this.checkedZones.size >= this.totalRiskZones;
  }

  /** 显示巡逻完成汇总 */
  showPatrolSummary() {
    var panel = document.getElementById("riskPanel");
    var overlay = document.getElementById("risk-overlay");
    var total = this.totalRiskZones;
    var checked = this.risksChecked;
    var found = this.risksFound;
    var safe = checked - found;

    var html = '<h2>📋 巡逻完成 - 汇总报告</h2>';
    html += '<p style="color:#64748b;font-size:13px;margin-bottom:16px;">巡逻范围：全栋建筑 | 完成时间：' + this.formatTime() + '</p>';

    // 统计卡片
    html += '<div style="display:flex;gap:12px;margin-bottom:16px;">';
    html += '<div style="flex:1;background:#0f172a;border-radius:8px;padding:16px;text-align:center;">';
    html += '<div style="font-size:28px;font-weight:700;color:#3b82f6;">' + checked + '</div>';
    html += '<div style="font-size:12px;color:#64748b;">已检测区域</div></div>';
    html += '<div style="flex:1;background:#0f172a;border-radius:8px;padding:16px;text-align:center;">';
    html += '<div style="font-size:28px;font-weight:700;color:#dc2626;">' + found + '</div>';
    html += '<div style="font-size:12px;color:#64748b;">发现风险</div></div>';
    html += '<div style="flex:1;background:#0f172a;border-radius:8px;padding:16px;text-align:center;">';
    html += '<div style="font-size:28px;font-weight:700;color:#22c55e;">' + safe + '</div>';
    html += '<div style="font-size:12px;color:#64748b;">安全区域</div></div>';
    html += '</div>';

    // 详细结果列表
    html += '<h3 style="color:#e2e8f0;font-size:15px;margin-bottom:10px;">检测详情</h3>';
    this.inspectionResults.forEach(function (r, i) {
      var zone = r.zone;
      var statusBadge = r.success
        ? (r.hasRisk
          ? '<span class="risk-badge high">有风险</span>'
          : '<span class="risk-badge safe">安全</span>')
        : '<span class="risk-badge medium">检测失败</span>';

      html += '<div class="risk-item">';
      html += '<p><strong>区域 ' + (i + 1) + '：</strong>' + this.escapeHtml(zone.risk_type) + ' ' + statusBadge + '</p>';
      html += '<p style="font-size:12px;color:#64748b;">' + this.escapeHtml(zone.description) + '</p>';
      if (r.hasRisk && r.risks.length > 0) {
        var risk = r.risks[0];
        html += '<p style="font-size:12px;"><strong>等级：</strong>' + this.escapeHtml(risk.level || "") + ' | <strong>物体：</strong>' + this.escapeHtml((risk.objects || []).join("、")) + '</p>';
      }
      html += '</div>';
    }.bind(this));

    html += '<button class="close-btn" onclick="document.getElementById(\'risk-overlay\').classList.remove(\'active\');location.reload();">完成巡逻</button>';
    panel.innerHTML = html;
    overlay.classList.add("active");
  }

  /** 格式化巡逻时间 */
  formatTime() {
    var elapsed = Math.floor((Date.now() - this.patrolStartTime) / 1000);
    var min = Math.floor(elapsed / 60);
    var sec = elapsed % 60;
    return min + "分" + sec + "秒";
  }

  /** 检测出错 */
  onInspectionError(message, zone) {
    this.isInspecting = false;
    this.showTip("检测失败：" + message + "，请确认后端服务已启动");
  }

  /** 显示扫描中面板 */
  showScanningPanel(zone) {
    var panel = document.getElementById("riskPanel");
    var overlay = document.getElementById("risk-overlay");
    var settings = window.GAME_SETTINGS || {};
    var providerName = settings.provider || "mock";

    var html = '<h2>🔍 正在检测：' + this.escapeHtml(zone.risk_type) + "</h2>";
    html += '<p style="color:#64748b;font-size:13px;margin-bottom:12px;">区域：' + this.escapeHtml(zone.description) + " | Provider: " + this.escapeHtml(providerName) + "</p>";

    // 相机图片预览
    if (zone.camera_image) {
      var baseUrl = window.location.pathname.replace(/\/index\.html$/, "");
      html += '<div class="camera-view">';
      html += '<div class="camera-label">📷 摄像头画面</div>';
      html += '<img src="' + baseUrl + "/" + zone.camera_image + '" alt="camera view" />';
      html += '</div>';
    }

    html += '<div class="scanning">';
    html += '<div class="spinner"></div>';
    html += "<p>机器人正在分析摄像头画面...<br>";
    html += '<small style="color:#475569;">' + this.escapeHtml(zone.prompt_hint || zone.description) + "</small></p>";
    html += '<div class="scan-bar"></div>';
    html += "</div>";

    panel.innerHTML = html;
    overlay.classList.add("active");
  }

  /** 显示检测结果 */
  showRiskResult(data, zone) {
    var panel = document.getElementById("riskPanel");
    var overlay = document.getElementById("risk-overlay");
    var riskData = data.data || {};
    var risks = riskData.risks || [];
    var hasRisk = riskData.has_risk || false;
    var settings = window.GAME_SETTINGS || {};
    var providerName = settings.provider || "mock";

    var html = '<h2>';

    if (!data.success) {
      html += "❌ 检测失败";
    } else if (hasRisk) {
      var level = risks[0] ? risks[0].level : "中";
      var levelClass = level === "高" ? "high" : level === "中" ? "medium" : "low";
      html += '⚠ 发现风险 <span class="risk-badge ' + levelClass + '">' + this.escapeHtml(level) + '风险</span>';
    } else {
      html += '✅ 未发现风险 <span class="risk-badge safe">安全</span>';
    }

    html += "</h2>";
    html += '<p style="color:#64748b;font-size:13px;margin-bottom:12px;">区域：' + this.escapeHtml(zone.description) + " | Provider: " + this.escapeHtml(data.provider || providerName) + "</p>";

    // 相机图片
    if (zone.camera_image) {
      var baseUrl = window.location.pathname.replace(/\/index\.html$/, "");
      html += '<div class="camera-view">';
      html += '<div class="camera-label">📷 摄像头画面</div>';
      html += '<img src="' + baseUrl + "/" + zone.camera_image + '" alt="camera view" />';
      html += '</div>';
    }

    if (!data.success) {
      html += '<div class="risk-item"><p>' + this.escapeHtml(data.error || "未知错误") + "</p></div>";
    } else if (risks.length === 0) {
      html += '<div class="risk-item"><p>该区域未检测到安全风险。</p></div>';
    } else {
      risks.forEach(
        function (r) {
          var lc = r.level === "高" ? "high" : r.level === "中" ? "medium" : "low";
          html += '<div class="risk-item">' +
            '<p><span class="risk-badge ' + lc + '">' + this.escapeHtml(r.level || "") + '</span> <strong>' + this.escapeHtml(r.type || "") + "</strong></p>" +
            '<p><strong>相关物体：</strong>' + this.escapeHtml((r.objects || []).join("、")) + "</p>" +
            '<p><strong>位置：</strong>' + this.escapeHtml(r.location || "") + "</p>" +
            '<p><strong>依据：</strong>' + this.escapeHtml(r.reason || "") + "</p>" +
            '<p><strong>建议：</strong>' + this.escapeHtml(r.suggestion || "") + "</p>" +
            "</div>";
        }.bind(this)
      );
    }

    // 证据充分性
    var evidence = riskData.evidence_sufficiency;
    if (evidence) {
      html += '<p style="color:#64748b;font-size:12px;margin-top:8px;">证据充分性：' + this.escapeHtml(evidence) + "</p>";
    }

    // 根据是否全部检测完，显示不同按钮
    if (this.isPatrolComplete()) {
      html += '<button class="close-btn" onclick="window.__showPatrolSummary()">查看巡逻汇总</button>';
      var self = this;
      window.__showPatrolSummary = function () {
        self.showPatrolSummary();
      };
    } else {
      html += '<p style="color:#64748b;font-size:12px;text-align:center;margin-top:8px;">剩余 ' + (this.totalRiskZones - this.checkedZones.size) + ' 个区域待检测</p>';
      html += '<button class="close-btn" onclick="document.getElementById(\'risk-overlay\').classList.remove(\'active\')">继续巡逻</button>';
    }
    panel.innerHTML = html;
    overlay.classList.add("active");
  }

  /** 创建 HUD */
  createHUD() {
    // 顶部状态栏背景
    var hudBg = this.add.graphics();
    hudBg.fillStyle(0x0f172a, 0.85);
    hudBg.fillRect(0, 0, 800, 36);
    hudBg.setDepth(100);

    // 房间名
    this.hudRoom = this.add.text(10, 10, "📍 " + this.sceneConfig.scene_name, {
      fontSize: "13px",
      color: "#e2e8f0",
      fontStyle: "bold",
    });
    this.hudRoom.setDepth(101);

    // 风险计数
    this.hudRisks = this.add.text(200, 10, "⚠ 风险发现: 0", {
      fontSize: "13px",
      color: "#fbbf24",
      fontStyle: "bold",
    });
    this.hudRisks.setDepth(101);

    // 已检查区域
    this.hudChecked = this.add.text(360, 10, "✓ 已检测: 0/" + this.totalRiskZones, {
      fontSize: "13px",
      color: "#22c55e",
      fontStyle: "bold",
    });
    this.hudChecked.setDepth(101);

    // 巡逻时间
    this.hudTime = this.add.text(560, 10, "⏱ 00:00", {
      fontSize: "13px",
      color: "#94a3b8",
    });
    this.hudTime.setDepth(101);

    // 定时更新时间
    this.time.addEvent({
      delay: 1000,
      callback: this.updatePatrolTime,
      callbackScope: this,
      loop: true,
    });

    // 底部操作提示
    var tipBg = this.add.graphics();
    tipBg.fillStyle(0x0f172a, 0.85);
    tipBg.fillRect(0, 568, 800, 32);
    tipBg.setDepth(100);

    this.hudTip = this.add.text(10, 575, "WASD/方向键移动 | 走到红色区域自动检测", {
      fontSize: "12px",
      color: "#64748b",
    });
    this.hudTip.setDepth(101);
  }

  /** 更新 HUD 数据 */
  updateHUD() {
    if (this.hudRisks) {
      this.hudRisks.setText("⚠ 风险发现: " + this.risksFound);
    }
    if (this.hudChecked) {
      this.hudChecked.setText("✓ 已检测: " + this.risksChecked + "/" + this.totalRiskZones);
    }
  }

  /** 更新巡逻时间 */
  updatePatrolTime() {
    var elapsed = Math.floor((Date.now() - this.patrolStartTime) / 1000);
    var min = Math.floor(elapsed / 60);
    var sec = elapsed % 60;
    if (this.hudTime) {
      this.hudTime.setText(
        "⏱ " + (min < 10 ? "0" : "") + min + ":" + (sec < 10 ? "0" : "") + sec
      );
    }
  }

  /** 显示提示信息 */
  showTip(text) {
    if (this.hudTip) {
      this.hudTip.setText(text);
      // 3秒后恢复默认提示
      this.time.delayedCall(3000, function () {
        if (this.hudTip) {
          this.hudTip.setText("WASD/方向键移动 | 走到红色区域自动检测");
        }
      }, [], this);
    }
  }

  /** 解析颜色字符串 */
  parseColor(str) {
    if (typeof str !== "string") return 0x888888;
    str = str.replace("#", "");
    return parseInt(str, 16);
  }

  /** HTML 转义 */
  escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
}
