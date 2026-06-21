# video-stitch · 视频拼接工具

> 拼接视频，加转场，加文字，一条命令搞定。
> 基于 ffmpeg，零 Python 依赖。

## 快速开始

```bash
pip install video-stitch

# 拼接三个视频
video-stitch -o final.mp4 clip1.mp4 clip2.mp4 clip3.mp4

# 加交叉淡入淡出和淡入淡出
video-stitch -o final.mp4 --crossfade 0.5 --fade-in 1 --fade-out 1.5 *.mp4

# 加标题和水印
video-stitch -o final.mp4 --title "我的讲座" --watermark "霜言制作" *.mp4

# 不同分辨率自动规范化
video-stitch -o final.mp4 --target-resolution 1920x1080 *.mp4

# 用 recipe 文件
video-stitch --recipe my-project.json

# 预览不执行
video-stitch --dry-run -o final.mp4 --crossfade 0.5 *.mp4

# 查看视频信息
video-stitch --probe clip1.mp4
```

## 环境要求

- Python >= 3.9
- ffmpeg >= 4.3（需支持 xfade 滤镜）
- 别无其他依赖

## 功能

- 多段视频拼接 + 交叉淡入淡出转场
- 不同分辨率自动统一（letterbox，不裁剪不拉伸）
- 逐段裁剪
- 片头标题 + 全程水印
- 片头/片尾淡入淡出
- JSON recipe 文件（保存配置，可复用）
- dry-run 预览模式
- probe 视频信息查看

## 许可证

MIT
