// src/CoverTitle.tsx
// 开头封面字：大字逐字出现 + 背景模糊卡片
import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  Sequence,
} from "remotion";

interface Props {
  text: string;
  durationFrames: number;
}

export const CoverTitle: React.FC<Props> = ({ text, durationFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 整体入场
  const enter = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 120, mass: 0.8 },
    durationInFrames: 20,
  });

  // 结尾淡出（最后15帧）
  const fadeOut = interpolate(
    frame,
    [durationFrames - 20, durationFrames - 5],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const chars = text.split("");

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeOut,
      }}
    >
      {/* 背景毛玻璃卡片 */}
      <div
        style={{
          background: "rgba(10, 10, 40, 0.65)",
          border: "1px solid rgba(150, 100, 255, 0.3)",
          borderRadius: 24,
          padding: "48px 56px",
          backdropFilter: "blur(20px)",
          boxShadow:
            "0 8px 60px rgba(100, 80, 255, 0.25), inset 0 1px 0 rgba(255,255,255,0.08)",
          transform: `scale(${0.7 + enter * 0.3}) translateY(${(1 - enter) * 60}px)`,
          maxWidth: 900,
          textAlign: "center",
        }}
      >
        {/* 顶部标签 */}
        <div
          style={{
            fontSize: 28,
            color: "#FFD700",
            fontWeight: 700,
            letterSpacing: 6,
            marginBottom: 24,
            opacity: 0.9,
            fontFamily:
              '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
          }}
        >
          AI 挖矿日记
        </div>

        {/* 封面主文字 */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: 4,
          }}
        >
          {chars.map((char, i) => {
            const charDelay = i * 3;
            const charEnter = spring({
              frame: frame - charDelay,
              fps,
              config: { damping: 10, stiffness: 250, mass: 0.5 },
              durationInFrames: 12,
            });

            return (
              <span
                key={i}
                style={{
                  fontFamily:
                    '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
                  fontSize: 96,
                  fontWeight: 900,
                  color: "#FFFFFF",
                  textShadow:
                    "0 0 30px rgba(150,100,255,0.6), 0 2px 12px rgba(0,0,0,0.8)",
                  opacity: charEnter,
                  transform: `translateY(${(1 - charEnter) * 20}px) scale(${0.8 + charEnter * 0.2})`,
                  display: "inline-block",
                  lineHeight: 1.3,
                }}
              >
                {char}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};
