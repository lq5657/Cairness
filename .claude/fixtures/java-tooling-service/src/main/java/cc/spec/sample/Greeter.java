package cc.spec.sample;

public final class Greeter {
    private Greeter() {
    }

    public static String greet(String name) {
        String cleaned = name.strip();
        if (cleaned.isEmpty()) {
            throw new IllegalArgumentException("name is required");
        }
        return "hello, " + cleaned;
    }
}
