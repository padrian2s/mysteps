# Keep complication services (registered in manifest)
-keep class com.adrianp.mysteps.complication.** { *; }
-keep class com.adrianp.mysteps.service.** { *; }
-keep class com.adrianp.mysteps.presentation.** { *; }
-keep class com.adrianp.mysteps.tile.** { *; }

# Keep line numbers for crash reports
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
