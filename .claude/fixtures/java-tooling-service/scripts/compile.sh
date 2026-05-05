set -eu

if ! command -v javac >/dev/null 2>&1; then
  echo "javac is required for the Java fixture" >&2
  exit 127
fi

build_dir="${TMPDIR:-/tmp}/cc-spec-java-tooling-service/classes"
rm -rf "$build_dir"
mkdir -p "$build_dir"

javac -d "$build_dir" $(find src/main/java -name '*.java' | sort)
