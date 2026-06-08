export interface Greeter {
  greet(name: string): string;
}

export class DefaultGreeter implements Greeter {
  greet(name: string): string {
    return `Hello, ${name}!`;
  }
}

export function createGreeter(): Greeter {
  return new DefaultGreeter();
}
