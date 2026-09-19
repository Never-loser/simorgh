# Simorgh for Android

The same engine as the desktop app, in a phone-sized shell. Persian first,
English one tap away. The board fills the width; underneath it, the panel
this engine exists for: every term behind the evaluation, and a check that
they sum to exactly what it searched on.

## How the engine gets onto the phone

The engine is not ported to Android and not wrapped in JNI. It is the same
C++ program, compiled for arm64 with the NDK and shipped inside the APK as
`app/src/main/jniLibs/arm64-v8a/libsimorgh.so`. The name is the whole
trick: Android extracts a `lib*.so` from an APK with the execute bit set,
which is what lets the app start it as a child process and talk UCI to it
over stdin and stdout — the same conversation the desktop front end has.
Nothing in `cpp/` knows it is on a phone.

To rebuild that binary after an engine change:

```
cmake -S cpp -B cpp/build-android \
  -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build-android
cp cpp/build-android/simorgh android/app/src/main/jniLibs/arm64-v8a/libsimorgh.so
```

`bench 9` on the desktop and on the phone visit exactly the same 1,330,953
nodes; a one-centipawn difference in evaluation would have changed that
number, so the two builds are known to search identically.

The opening book and the tuned weights are copied from `../data` by the
Gradle build, so a re-tune reaches the phone on the next build.

## Building the app

Needs a JDK 17 and the Android SDK (platform 34, build-tools 34). Point
`local.properties` at the SDK, then:

```
cd android
gradle assembleDebug
```

## What the phone measured

Search speed on a Dimensity 1200 is about 690K nodes/s, roughly a third of
a desktop core. It needs about twice the time to reach the same depth:

| budget | depth |
|---|---|
| 0.5s | 10 |
| 1s | 11 |
| 2s | 13 |
| 3s | 14 |
| 5s | 14 |
| 9s | 15 |

So the default thinking time is 2s, which lands on the same depth the
desktop reaches in one, and the time control is a set of uneven steps
rather than a slider: 5s buys nothing over 3s, and a slider would sell that
dead zone as a choice.

## Two things Compose gets wrong in Persian

Both were found on the device, not in the code. A signed number inside an
RTL layout has its sign moved to the far end, so `+0.18` draws as `0.18+`;
every number is rendered in its own left-to-right run. And a colon between
a Persian word and Latin square names is a directional run of its own and
jumps to the wrong side of them; the square lists use a space instead.

The board itself is pinned left-to-right whatever the interface language.
A chessboard is not a text run, and a1 belongs bottom-left.
