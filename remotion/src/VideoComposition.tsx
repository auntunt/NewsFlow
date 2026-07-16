// src/VideoComposition.tsx
// 主合成：波浪背景 + 封面字 + 字幕 + 音频
import React from "react";
import { AbsoluteFill, Audio, Sequence, useVideoConfig, staticFile } from "remotion";
import { WaveBackground } from "./WaveBackground";
import { CoverTitle } from "./CoverTitle";
import { CaptionOverlay, CaptionSegment } from "./CaptionOverlay";

export interface VideoProps {
  audioSrc: string;        // 音频文件路径（相对于 public/ 或绝对路径）
  coverText: string;       // 封面大字，如 "AI工具偷走了我的密钥"
  segments: CaptionSegment[];  // 字幕段落+词级时间戳
  coverDurationSec?: number;   // 封面显示时长（秒），默认5
  accountName?: string;    // 账号名，显示在封面
}

export const VideoComposition: React.FC<VideoProps> = ({
  audioSrc,
  coverText,
  segments,
  coverDurationSec = 5,
  accountName = "AI 挖矿日记",
}) => {
  const { fps } = useVideoConfig();
  const coverFrames = Math.round(coverDurationSec * fps);

  return (
    <AbsoluteFill style={{ background: "#050510" }}>
      {/* 1. 背景动画（全程） */}
      <WaveBackground />

      {/* 2. 音频 */}
      {audioSrc && (
        <Audio src={staticFile(audioSrc)} startFrom={0} />
      )}

      {/* 3. 封面字（开头 coverDurationSec 秒） */}
      <Sequence durationInFrames={coverFrames}>
        <CoverTitle
          text={coverText}
          durationFrames={coverFrames}
          accountName={accountName}
        />
      </Sequence>

      {/* 4. 字幕（封面结束后出现） */}
      <Sequence from={coverFrames}>
        <CaptionOverlay segments={segments} />
      </Sequence>

      {/* 5. 账号标签（全程右上角） */}
      <div
        style={{
          position: "absolute",
          top: 72,
          right: 52,
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: "rgba(10,10,40,0.6)",
          border: "1px solid rgba(150,100,255,0.25)",
          borderRadius: 40,
          padding: "10px 22px",
          backdropFilter: "blur(10px)",
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "#00ff88",
            boxShadow: "0 0 6px #00ff88",
          }}
        />
        <span
          style={{
            fontFamily:
              '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
            fontSize: 28,
            color: "rgba(255,255,255,0.85)",
            fontWeight: 600,
          }}
        >
          {accountName}
        </span>
      </div>

      {/* 6. 底部 hashtag 区域（最后8秒出现） */}
      <EndHashtags coverFrames={coverFrames} segments={segments} />
    </AbsoluteFill>
  );
};

// 片尾 hashtag 淡入
const EndHashtags: React.FC<{
  coverFrames: number;
  segments: CaptionSegment[];
}> = ({ coverFrames, segments }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const showFrom = durationInFrames - Math.round(8 * fps);

  return (
    <Sequence from={Math.max(showFrom, coverFrames)}>
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 16,
          flexWrap: "wrap",
          padding: "0 40px",
        }}
      >
        {["#AI安全", "#开发者必看", "#科技热点"].map((tag, i) => (
          <span
            key={i}
            style={{
              fontFamily:
                '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
              fontSize: 28,
              color: "rgba(150,180,255,0.7)",
              fontWeight: 500,
            }}
          >
            {tag}
          </span>
        ))}
      </div>
    </Sequence>
  );
};
