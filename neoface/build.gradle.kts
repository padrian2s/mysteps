plugins {
    alias(libs.plugins.android.application)
}

// Watch Face Format watch face: resource-only APK (no code), published separately from the app
android {
    namespace = "com.adrianp.mysteps.neoface"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.adrianp.mysteps.neoface"
        // WFF version 4 needs Wear OS 6 (API 36)
        minSdk = 36
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }

    signingConfigs {
        create("release") {
            storeFile = file("../release-key.jks")
            storePassword = "mysteps2026"
            keyAlias = "mysteps"
            keyPassword = "mysteps2026"
        }
    }

    buildTypes {
        debug {
            isMinifyEnabled = true
        }
        release {
            isMinifyEnabled = true
            // Resources are referenced from the WFF XML only; shrinking would drop them
            isShrinkResources = false
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
