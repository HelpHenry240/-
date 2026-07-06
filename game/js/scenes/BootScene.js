/**
 * BootScene - 加载资源、生成程序化纹理
 *
 * 不依赖外部图片文件，所有纹理用 Phaser Graphics API 在运行时生成。
 */
class BootScene extends Phaser.Scene {
  constructor() {
    super("BootScene");
  }

  preload() {
    // 加载所有场景配置 JSON
    this.load.json("dormitory", "scenes/dormitory.json");
    this.load.json("corridor", "scenes/corridor.json");
    this.load.json("kitchen", "scenes/kitchen.json");
    this.load.json("living_room", "scenes/living_room.json");
    this.load.json("laboratory", "scenes/laboratory.json");
  }

  create() {
    this.generateTextures();
    this.scene.start("GameScene");
  }

  generateTextures() {
    this.createFloorTexture();
    this.createWallTexture();
    this.createRobotTextures();
    this.createFurnitureTextures();
    this.createRiskZoneTexture();
    this.createParticleTexture();
  }

  /** 木地板纹理 32x32 */
  createFloorTexture() {
    var g = this.add.graphics();
    g.fillStyle(0x3d2f1f, 1);
    g.fillRect(0, 0, 32, 32);
    // 木纹线
    g.fillStyle(0x4a3a28, 1);
    g.fillRect(0, 0, 32, 2);
    g.fillRect(0, 15, 32, 1);
    g.fillRect(0, 30, 32, 2);
    g.fillStyle(0x352918, 1);
    g.fillRect(10, 5, 1, 10);
    g.fillRect(22, 18, 1, 12);
    g.generateTexture("floor", 32, 32);
    g.destroy();
  }

  /** 墙壁纹理 32x32 */
  createWallTexture() {
    var g = this.add.graphics();
    g.fillStyle(0x4a4a5a, 1);
    g.fillRect(0, 0, 32, 32);
    g.fillStyle(0x555566, 1);
    g.fillRect(0, 0, 32, 4);
    g.fillRect(0, 16, 32, 2);
    g.fillStyle(0x3a3a4a, 1);
    g.fillRect(0, 14, 32, 2);
    g.fillRect(0, 30, 32, 2);
    g.generateTexture("wall", 32, 32);
    g.destroy();
  }

  /** 机器人 4 方向纹理 24x32 */
  createRobotTextures() {
    var dirs = ["down", "up", "left", "right"];
    var colors = {
      body: 0x3b82f6,
      head: 0x60a5fa,
      eye: 0xfbbf24,
      dark: 0x1e3a5f,
    };

    for (var i = 0; i < dirs.length; i++) {
      var dir = dirs[i];
      var g = this.add.graphics();

      // 阴影
      g.fillStyle(0x000000, 0.2);
      g.fillEllipse(12, 30, 18, 6);

      // 身体
      g.fillStyle(colors.body, 1);
      g.fillRoundedRect(3, 12, 18, 16, 3);

      // 头部
      g.fillStyle(colors.head, 1);
      g.fillRoundedRect(5, 2, 14, 12, 3);

      // 眼睛方向不同
      g.fillStyle(colors.eye, 1);
      if (dir === "down") {
        g.fillRect(8, 6, 3, 3);
        g.fillRect(13, 6, 3, 3);
      } else if (dir === "up") {
        g.fillStyle(colors.dark, 1);
        g.fillRect(8, 4, 3, 2);
        g.fillRect(13, 4, 3, 2);
      } else if (dir === "left") {
        g.fillRect(6, 6, 3, 3);
      } else {
        g.fillRect(15, 6, 3, 3);
      }

      // 天线
      g.fillStyle(colors.dark, 1);
      g.fillRect(11, 0, 2, 3);
      g.fillStyle(0xef4444, 1);
      g.fillCircle(12, 0, 2);

      // 腿/轮子
      g.fillStyle(colors.dark, 1);
      g.fillRect(5, 28, 5, 4);
      g.fillRect(14, 28, 5, 4);

      g.generateTexture("robot_" + dir, 24, 32);
      g.destroy();
    }
  }

  /** 家具通用纹理生成器 */
  createFurnitureTextures() {
    // 创建一个白色方块作为家具基底，上色通过 tint
    var g = this.add.graphics();
    g.fillStyle(0xffffff, 1);
    g.fillRect(0, 0, 64, 64);
    // 边框
    g.lineStyle(2, 0x333333, 0.3);
    g.strokeRect(1, 1, 62, 62);
    g.generateTexture("furniture_base", 64, 64);
    g.destroy();
  }

  /** 风险区域纹理 */
  createRiskZoneTexture() {
    var g = this.add.graphics();
    g.fillStyle(0xef4444, 0.15);
    g.fillRect(0, 0, 64, 64);
    g.lineStyle(2, 0xef4444, 0.5);
    g.strokeRect(1, 1, 62, 62);
    // 虚线效果
    for (var i = 0; i < 64; i += 8) {
      g.fillStyle(0xef4444, 0.6);
      g.fillRect(i, 0, 4, 2);
      g.fillRect(i, 62, 4, 2);
      g.fillRect(0, i, 2, 4);
      g.fillRect(62, i, 2, 4);
    }
    g.generateTexture("risk_zone", 64, 64);
    g.destroy();
  }

  /** 粒子纹理（风险触发时的效果） */
  createParticleTexture() {
    var g = this.add.graphics();
    g.fillStyle(0xef4444, 1);
    g.fillCircle(4, 4, 4);
    g.generateTexture("particle", 8, 8);
    g.destroy();
  }
}
