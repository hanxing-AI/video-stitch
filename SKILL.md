---
name: video-stitch
description: >
  Stitch multiple video clips into one, with crossfade transitions,
  text overlays (title cards and watermarks), auto-normalization
  for mixed resolutions, trim, and fade in/out effects. Powered by
  ffmpeg with zero Python dependencies. Use when the user wants to
  combine/merge/stitch/concatenate video clips, add transitions
  between clips, add title text or watermarks to videos, or set up
  repeatable video assembly configurations.
triggers:
  - 拼接视频
  - 视频合并
  - stitch video
  - combine clips
  - combine videos
  - merge videos
  - merge clips
  - video montage
  - concatenate video
  - concatenate clips
  - 视频拼接
  - 加转场
  - add transition
  - 加字幕
  - add title
  - add watermark
  - 加水印
  - 视频剪辑拼接
version: 1.0.0
---

# Video-Stitch — 视频拼接工具

将多个视频片段拼接为一个，支持交叉淡入淡出转场、文字叠加、自动分辨率统一、裁剪和淡入淡出。

## 依赖检查

开始前确认环境可用：

```bash
bash D:/hermes/video-stitch/scripts/check-deps.sh
```

需要: Python 3.9+, ffmpeg 4.3+

## WHEN TO USE

触发本技能的场景：
- 用户要把多个视频片段合并/拼接/串联
- 用户要给视频加标题文字或水印
- 用户要设置可复用的视频拼接配置（recipe）
- 用户询问"怎么把几段视频接在一起"、"加个片头"、"做个合集"

**不要用本技能处理**：纯音频编辑、复杂的画中画合成（v2）、逐帧精确编辑（用专业剪辑软件）

## 核心流程

### 1. 理解用户意图

向用户确认：
- 几个视频文件？顺序如何？
- 需要转场效果吗？（交叉淡入淡出，还是直接硬切）
- 需要加文字吗？（片头标题 / 全程水印）
- 视频分辨率一致吗？（不一致需要规范化）
- 输出格式偏好？（默认 mp4）

### 2. 探测输入文件

用 `--probe` 快速查看视频信息，判断是否需要规范化：

```bash
video-stitch --probe clip1.mp4 clip2.mp4 clip3.mp4
```

或者使用 `video-probe` 命令：

```bash
video-probe clip1.mp4 clip2.mp4
```

### 3. 构建命令或 recipe

**一次性拼接** — 直接用 CLI 参数：

```bash
# 最简拼接（无转场）
video-stitch -o output.mp4 clip1.mp4 clip2.mp4 clip3.mp4

# 带交叉淡入淡出
video-stitch -o output.mp4 --crossfade 0.5 --fade-in 1 --fade-out 1.5 *.mp4

# 加标题和水印
video-stitch -o output.mp4 --title "我的讲座" --watermark "霜言制作" *.mp4

# 不同分辨率自动规范化
video-stitch -o output.mp4 --target-resolution 1920x1080 *.mp4
```

**可复用项目** — 使用 recipe JSON 文件：

参考 `templates/recipe-full.json` 的完整格式。创建 recipe 后：
```bash
video-stitch --recipe my-project.json
```

### 4. 执行拼接

如果用户不确定，先用 `--dry-run` 预览：
```bash
video-stitch --dry-run -o output.mp4 --crossfade 0.5 *.mp4
```

确认后去掉 `--dry-run` 正式执行。使用 `--verbose` 查看详细进度。

### 5. 验证输出

```bash
video-stitch --probe output.mp4
```

检查时长、分辨率、音频是否正确。

## 决策规则

### 何时规范化
- 用 `--probe` 检查所有输入 → 如果分辨率、帧率、或编码不同 → 启用规范化（默认开启）
- 所有输入完全一致 → 可用 `--no-normalize` 跳过以提速

### CLI vs Recipe
- **直接 CLI**：一次性任务、参数简单、不需要保存配置
- **Recipe 文件**：需要重复执行的项目、发布后的在线更新、团队协作

### 交叉淡入淡出时长
- 0.3–0.5s：快节奏剪切
- 0.5–1.0s：叙事流
- 1.0–2.0s：戏剧化过渡

### 文字叠加字体
- 如果 `--font-file` 未指定，系统自动检测常见系统字体
- Windows 中文内容需要指定中文字体文件，否则可能乱码

## Troubleshooting

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| xfade 报错: "parameters do not match" | 输入文件分辨率/像素格式不同 | 去掉 `--no-normalize`，启用规范化 |
| "No such filter: 'xfade'" | ffmpeg 版本太旧 | 需要 ffmpeg >= 4.3 |
| 中文文字不显示/乱码 | 无中文字体 | 用 `--font-file` 指定中文字体 .ttf 路径 |
| drawtext 报错: fontconfig error | fontconfig 未配置 | Windows 上会自动检测 arial.ttf；或用 `--font-file` |
| 输出无音频 | 输入有静音轨道或音频参数不一致 | 用 `--probe` 确认每个输入都有音频流 |
| 裁剪时间不对 | 时间戳格式有误 | 用秒数（如90.5）或 MM:SS（如1:30.5） |
| 输出文件太大 | CRF 太低或预设太慢 | 用默认 CRF 23 或 `--preset fast` |
| 交叉淡入淡出出现黑闪 | xfade offset 计算错误 | 减少 crossfade 时长或检查输入时长 |
| 拼接后音画不同步 | 输入时间戳不一致 | 规范化会重置时间戳；确保 `--normalize` 开启 |

## 参考

- `references/ffmpeg-filters.md` — 本工具使用的 ffmpeg 滤镜速查
- `references/troubleshooting.md` — 更详细的故障排除
- `examples/` — 完整使用示例
