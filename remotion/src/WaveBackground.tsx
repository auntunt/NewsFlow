// src/WaveBackground.tsx
// 深色背景 + 蓝紫渐变光晕流动波浪
import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export const WaveBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // 多层光晕，不同速度和相位
  const orbs = [
    { x: 30, y: 25, r: 480, color: "#1a1aff", speed: 0.18, phase: 0 },
    { x: 75, y: 70, r: 420, color: "#7b2fff", speed: 0.12, phase: 2.1 },
    { x: 15, y: 75, r: 360, color: "#0066ff", speed: 0.22, phase: 1.0 },
    { x: 85, y: 20, r: 400, color: "#cc00ff", speed: 0.15, phase: 3.5 },
    { x: 50, y: 50, r: 300, color: "#0033cc", speed: 0.08, phase: 0.5 },
  ];

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "#050510",
        overflow: "hidden",
      }}
    >
      {/* 渐变光晕层 */}
      {orbs.map((orb, i) => {
        const ox = orb.x + Math.sin(t * orb.speed + orb.phase) * 12;
        const oy = orb.y + Math.cos(t * orb.speed * 0.7 + orb.phase) * 10;
        const pulse = 0.28 + Math.sin(t * orb.speed * 1.3 + orb.phase) * 0.06;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${ox}%`,
              top: `${oy}%`,
              width: orb.r * 2,
              height: orb.r * 2,
              transform: "translate(-50%, -50%)",
              borderRadius: "50%",
              background: `radial-gradient(circle, ${orb.color}${Math.round(pulse * 255).toString(16).padStart(2, "0")} 0%, transparent 70%)`,
              filter: "blur(60px)",
              mixBlendMode: "screen",
            }}
          />
        );
      })}

      {/* 波浪扫描线 */}
      {[0, 1, 2].map((i) => {
        const yPos = ((t * 120 * (i * 0.3 + 0.7) + i * 640) % 1920) - 100;
        return (
          <div
            key={`wave-${i}`}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: yPos,
              height: 1,
              background:
                "linear-gradient(90deg, transparent, rgba(100,150,255,0.15), rgba(180,100,255,0.12), rgba(100,150,255,0.15), transparent)",
              filter: "blur(1px)",
            }}
          />
        );
      })}

      {/* 网格纹理叠加 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(100,130,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(100,130,255,0.025) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
          opacity: 0.6,
        }}
      />

      {/* 底部渐变遮罩（保证字幕可读性）*/}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 700,
          background:
            "linear-gradient(to bottom, transparent, rgba(5,5,16,0.85) 40%, rgba(5,5,16,0.95) 100%)",
        }}
      />
    </div>
  );
};
