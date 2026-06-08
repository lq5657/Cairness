package cc.spec.sample;

public final class GreeterTest {
    public static void main(String[] args) {
        if (!"hello, Ada".equals(Greeter.greet(" Ada "))) {
            throw new AssertionError("greet should trim names");
        }

        try {
            Greeter.greet("  ");
            throw new AssertionError("blank names should be rejected");
        } catch (IllegalArgumentException expected) {
        }
    }
}
