import { describe, expect, it } from "vitest";
import { parseChannels, parsePoints, validateAll } from "./parse";
import { SAMPLES } from "./samples";

describe("内置样例自洽性", () => {
  for (const [key, s] of Object.entries(SAMPLES)) {
    it(`样例 ${key} 可解析并通过前端校验`, () => {
      const p = parsePoints(s.points);
      const c = parseChannels(s.channels);
      expect(p.errors).toEqual([]);
      expect(c.errors).toEqual([]);
      expect(validateAll(p.points, s.root, c.channels)).toEqual([]);
      // 每个样例点引用、通道标识无重复
      expect(new Set(p.points).size).toBe(p.points.length);
      expect(new Set(c.channels.map((x) => x.id)).size).toBe(c.channels.length);
    });
  }

  it("三入口环样例正是环收缩同优裁决场景", () => {
    const s = SAMPLES.threeEntryCycle;
    const c = parseChannels(s.channels).channels;
    const ids = new Set(c.map((x) => x.id));
    for (const id of ["e0", "e1", "e2", "e3", "e4", "e5"]) {
      expect(ids.has(id)).toBe(true);
    }
  });
});
