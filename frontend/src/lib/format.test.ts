import { describe, expect, it } from "vitest";
import { duration, initials, jdTitle, labelTone, personName, requiredSkills, skillName, timeAgo } from "./format";
import type { SearchResult } from "./types";

describe("skillName", () => {
  it("uses the known spelling", () => {
    expect(skillName("fastapi")).toBe("FastAPI");
    expect(skillName("PostgreSQL")).toBe("PostgreSQL");
  });
  it("title-cases unknown skills", () => {
    expect(skillName("docker compose")).toBe("Docker Compose");
  });
});

describe("personName", () => {
  it("fixes all-caps names", () => {
    expect(personName("RIYA MEHRA")).toBe("Riya Mehra");
    expect(personName("ANNE-MARIE O'NEIL")).toBe("Anne-Marie O'Neil");
  });
  it("leaves mixed case alone", () => {
    expect(personName("Priya deSouza")).toBe("Priya deSouza");
  });
  it("names the nameless", () => {
    expect(personName("")).toBe("Unnamed candidate");
  });
});

describe("initials", () => {
  it("takes first and last", () => {
    expect(initials("Priya Sharma")).toBe("PS");
    expect(initials("RIYA MEHRA")).toBe("RM");
    expect(initials("Priya Anand Sharma")).toBe("PS");
  });
  it("handles one name", () => {
    expect(initials("Cher")).toBe("C");
  });
});

describe("duration", () => {
  it("reads naturally", () => {
    expect(duration(0)).toBe("under a month");
    expect(duration(0.17)).toBe("2 mo");
    expect(duration(1)).toBe("1 yr");
    expect(duration(2.46)).toBe("2.5 yrs");
  });
});

describe("jdTitle", () => {
  it("uses the first non-empty line", () => {
    expect(jdTitle("\n\n  Junior Backend Developer \nmore")).toBe("Junior Backend Developer");
  });
  it("shortens long titles", () => {
    expect(jdTitle("x".repeat(120))).toHaveLength(78);
  });
});

describe("labelTone", () => {
  it("groups labels into three tones", () => {
    expect(labelTone("Exceptional")).toBe("strong");
    expect(labelTone("Strong")).toBe("strong");
    expect(labelTone("Good")).toBe("mid");
    expect(labelTone("Partial")).toBe("weak");
    expect(labelTone("Weak")).toBe("weak");
  });
});

describe("requiredSkills", () => {
  it("collects matched and missing across results, sorted and unique", () => {
    const results = [
      { matched_required: ["python"], missing_required: ["fastapi"] },
      { matched_required: ["fastapi", "python"], missing_required: [] },
    ] as unknown as SearchResult[];
    expect(requiredSkills(results)).toEqual(["fastapi", "python"]);
  });
});

describe("timeAgo", () => {
  const now = Date.UTC(2026, 9, 15, 12, 0, 0);
  it("counts minutes and hours", () => {
    expect(timeAgo(now - 20_000, now)).toBe("just now");
    expect(timeAgo(now - 5 * 60_000, now)).toBe("5 min ago");
    expect(timeAgo(now - 3 * 3_600_000, now)).toBe("3 hr ago");
  });
});
