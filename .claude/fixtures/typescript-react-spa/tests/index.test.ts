import { describe, it, expect } from "vitest";
import { createGreeter } from "../src/index";

describe("createGreeter", () => {
  it("should return a greeting message", () => {
    const greeter = createGreeter();
    expect(greeter.greet("World")).toBe("Hello, World!");
  });

  it("should handle empty name", () => {
    const greeter = createGreeter();
    expect(greeter.greet("")).toBe("Hello, !");
  });
});
