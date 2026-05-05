set -eu

if ! command -v javac >/dev/null 2>&1; then
  echo "javac is required for the Java fixture" >&2
  exit 127
fi
if ! command -v java >/dev/null 2>&1; then
  echo "java is required for the Java fixture" >&2
  exit 127
fi

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
main_dir="${TMPDIR:-/tmp}/cc-spec-java-tooling-service/classes"
test_dir="${TMPDIR:-/tmp}/cc-spec-java-tooling-service/test-classes"
rm -rf "$main_dir" "$test_dir"
mkdir -p "$main_dir" "$test_dir"

cd "$root_dir"
javac -d "$main_dir" $(find src/main/java -name '*.java' | sort)
javac -cp "$main_dir" -d "$test_dir" $(find src/test/java -name '*.java' | sort)
java -cp "$main_dir:$test_dir" cc.spec.sample.GreeterTest
