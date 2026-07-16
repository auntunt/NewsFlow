// src/Root.tsx
import React from "react";
import { Composition, registerRoot } from "remotion";
import { VideoComposition, VideoProps } from "./VideoComposition";

// 默认 props（用于 Remotion Studio 预览）
const defaultProps: VideoProps = {
  audioSrc: "",
  coverText: "AI工具偷走了我的密钥",
  segments: [
    {
      text: "你有没有想过",
      startMs: 5000,
      endMs: 7500,
      words: [
        { word: "你", startMs: 5000, endMs: 5400 },
        { word: "有", startMs: 5400, endMs: 5700 },
        { word: "没", startMs: 5700, endMs: 6000 },
        { word: "有", startMs: 6000, endMs: 6300 },
        { word: "想", startMs: 6300, endMs: 6800 },
        { word: "过", startMs: 6800, endMs: 7500 },
      ],
    },
    {
      text: "一个AI工具能把你的",
      startMs: 7600,
      endMs: 11000,
      words: [
        { word: "一", startMs: 7600, endMs: 7900 },
        { word: "个", startMs: 7900, endMs: 8200 },
        { word: "AI", startMs: 8200, endMs: 8700 },
        { word: "工", startMs: 8700, endMs: 9000 },
        { word: "具", startMs: 9000, endMs: 9300 },
        { word: "能", startMs: 9300, endMs: 9600 },
        { word: "把", startMs: 9600, endMs: 9900 },
        { word: "你", startMs: 9900, endMs: 10200 },
        { word: "的", startMs: 10200, endMs: 11000 },
      ],
    },
    {
      text: "SSH私钥传到别人服务器",
      startMs: 11100,
      endMs: 15000,
      words: [
        { word: "SSH", startMs: 11100, endMs: 11800 },
        { word: "私", startMs: 11800, endMs: 12200 },
        { word: "钥", startMs: 12200, endMs: 12600 },
        { word: "传", startMs: 12600, endMs: 12900 },
        { word: "到", startMs: 12900, endMs: 13200 },
        { word: "别", startMs: 13200, endMs: 13500 },
        { word: "人", startMs: 13500, endMs: 13800 },
        { word: "服", startMs: 13800, endMs: 14200 },
        { word: "务", startMs: 14200, endMs: 14600 },
        { word: "器", startMs: 14600, endMs: 15000 },
      ],
    },
  ],
  coverDurationSec: 5,
  accountName: "AI 挖矿日记",
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="NewsFlowVideo"
      component={VideoComposition}
      durationInFrames={1800}
      fps={24}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
    />
  );
};

registerRoot(RemotionRoot);
