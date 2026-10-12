import java.util.Properties
import java.io.FileInputStream

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.hilt.android)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.typebridge.mobile"
    compileSdk = 34
    buildToolsVersion = "34.0.0"

    defaultConfig {
        applicationId = "com.typebridge.mobile"
        minSdk = 26
        targetSdk = 34
        versionCode = 2
        versionName = "1.0.1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // Load signing credentials from keystore.properties (never committed to Git)
    // For CI: use KEYSTORE_PATH, KEYSTORE_STORE_PASSWORD, KEYSTORE_KEY_ALIAS, KEYSTORE_KEY_PASSWORD env vars
    val keystorePropsFile = rootProject.file("keystore.properties")
    val keystoreProps = Properties()
    if (keystorePropsFile.exists()) {
        keystoreProps.load(FileInputStream(keystorePropsFile))
    }

    signingConfigs {
        create("release") {
            val ksPath = keystoreProps.getProperty("storeFile")
                ?: System.getenv("KEYSTORE_PATH")
                ?: "typebridge-release.keystore"
            val ksFile = file(ksPath)
            if (ksFile.exists()) {
                storeFile = ksFile
            }
            storePassword = keystoreProps.getProperty("storePassword")
                ?: System.getenv("KEYSTORE_STORE_PASSWORD")
                ?: ""
            keyAlias = keystoreProps.getProperty("keyAlias")
                ?: System.getenv("KEYSTORE_KEY_ALIAS")
                ?: "typebridge"
            keyPassword = keystoreProps.getProperty("keyPassword")
                ?: System.getenv("KEYSTORE_KEY_PASSWORD")
                ?: ""
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = true
            enableV4Signing = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            val ks = signingConfigs.getByName("release")
            if (ks.storeFile?.exists() == true) {
                signingConfig = ks
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            val ks = signingConfigs.getByName("release")
            if (ks.storeFile?.exists() == true) {
                signingConfig = ks
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }
}

dependencies {
    // Core
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.constraintlayout)

    // Navigation
    implementation(libs.androidx.navigation.fragment)
    implementation(libs.androidx.navigation.ui)

    // Lifecycle / ViewModel
    implementation(libs.androidx.lifecycle.viewmodel)
    implementation(libs.androidx.lifecycle.runtime)

    // Room
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    // DataStore
    implementation(libs.androidx.datastore)

    // Hilt
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)

    // Networking
    implementation(libs.okhttp)
    implementation(libs.gson)

    // Security / Crypto
    implementation(libs.bouncycastle)
    implementation(libs.security.crypto)

    // QR Code scanning
    implementation(libs.zxing.android)
}
