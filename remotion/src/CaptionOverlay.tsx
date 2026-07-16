// src/CaptionOverlay.tsx
// 逐词高亮字幕，抖音/视频号爆款样式
import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

export interface Word {
  word: string;
  startMs: number;
  endMs: number;
}

export interface CaptionSegment {
  text: string;
  startMs: number;
  endMs: number;
  words: Word[];
}

interface Props {
  segments: CaptionSegment[];
  // 最多同时显示几个字
  maxCharsPerLine?: number;
}

// 当前时间找到活跃 segment
function getActiveSegment(segments: CaptionSegment[], currentMs: number) {
  for (const seg of segments) {
    if (currentMs >= seg.startMs && currentMs < seg.endMs + 400) {
      return seg;
    }
  }
  // 找最近的下一个
  for (const seg of segments) {
    if (currentMs < seg.startMs) return null;
  }
  return null;
}

export const CaptionOverlay: React.FC<Props> = ({
  segments,
  maxCharsPerLine = 12,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;

  const activeSeg = getActiveSegment(segments, currentMs);
  if (!activeSeg) return null;

  // segment 出现时的入场动画
  const segEntryFrame = Math.round((activeSeg.startMs / 1000) * fps);
  const entryProgress = spring({
    frame: frame - segEntryFrame,
    fps,
    config: { damping: 14, stiffness: 180, mass: 0.6 },
    durationInFrames: 12,
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 160,
        left: 0,
        right: 0,
        paddingLeft: 48,
        paddingRight: 48,
        transform: `translateY(${(1 - entryProgress) * 30}px)`,
        opacity: entryProgress,
      }}
    >
      {/* 字幕文字行 */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: 4,
        }}
      >
        {activeSeg.words.map((w, i) => {
          const isActive =
            currentMs >= w.startMs && currentMs < w.endMs + 120;
          const isPast = currentMs >= w.endMs + 120;

          // 当前词弹出动画
          const wordFrame = Math.round((w.startMs / 1000) * fps);
          const wordScale = isActive
            ? spring({
                frame: frame - wordFrame,
                fps,
                config: { damping: 10, stiffness: 300, mass: 0.4 },
                durationInFrames: 8,
              })
            : 1;

          return (
            <span
              key={i}
              style={{
                fontFamily:
                  '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
                fontSize: activeSeg.words.length > 10 ? 72 : 80,
                fontWeight: 900,
                letterSpacing: 2,
                lineHeight: 1.2,
                color: isActive
                  ? "#FFD700"           // 当前词：金黄色
                  : isPast
                  ? "rgba(255,255,255,0.7)"  // 已过词：半透明
                  : "rgba(255,255,255,0.95)", // 未到词：白色
                textShadow: isActive
                  ? "0 0 20px rgba(255,215,0,0.8), 0 2px 8px rgba(0,0,0,0.9)"
                  : "0 2px 8px rgba(0,0,0,0.9)",
                transform: `scale(${isActive ? wordScale * 1.08 : 1})`,
                display: "inline-block",
                transition: isActive ? "none" : "color 0.15s ease",
                WebkitTextStroke: isActive ? "0px" : "0px",
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </div>
  );
};
