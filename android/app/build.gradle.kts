plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ir.simorgh.chess"
    compileSdk = 34

    defaultConfig {
        applicationId = "ir.simorgh.chess"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1"
    }

    // The engine binary is prebuilt with the NDK and checked in under
    // jniLibs as libsimorgh.so. It is an executable, not a library: Android
    // only extracts a packaged file with the execute bit set when it is
    // named lib*.so, and that is what lets the app run it as a process and
    // hold the same UCI conversation the desktop front end has. Letting
    // Gradle drive CMake would not help -- AGP packages libraries, not
    // executables -- so the build stays out of the engine's way.
    packaging {
        jniLibs.useLegacyPackaging = true
    }

    buildFeatures { compose = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.14" }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    buildTypes {
        debug { isMinifyEnabled = false }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.09.03")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}

/**
 * The book and the tuned weights live in ../data at the repository root and
 * are the same files the desktop app and the engine's own tools read. They
 * are copied into assets at build time rather than committed twice: the
 * originals stay the single source of truth, and a re-tune or a book
 * update reaches the phone on the next build with nothing else to touch.
 */
val stageEngineData by tasks.registering(Copy::class) {
    from(rootProject.projectDir.resolve("../data")) {
        include("book.txt", "weights.txt")
    }
    into(layout.projectDirectory.dir("src/main/assets"))
}
tasks.matching { it.name.startsWith("merge") && it.name.endsWith("Assets") }
    .configureEach { dependsOn(stageEngineData) }
