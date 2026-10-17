package com.kolsco.documentscanner

import android.os.Environment
import android.os.StatFs
import java.security.MessageDigest
import java.util.Base64

class AndroidSharedUtils {
    companion object {
        fun availableStorageSpaceInBytes(useExternal: Boolean = false): Long {
            return try {
                val path = if (useExternal) {
                    Environment.getExternalStorageDirectory()
                } else {
                    Environment.getDataDirectory()
                }
                val stat = StatFs(path.path)
                stat.availableBytes
            } catch (e: Exception) {
                e.printStackTrace()
                0L
            }
        }

        fun checkAvailableStorage(
            sizeBytes: Long,
            useExternal: Boolean = false
        ): Boolean {
            return availableStorageSpaceInBytes(useExternal) > sizeBytes
        }

        fun generateCodeChallenge(codeVerifier: String): String {
            val digest = MessageDigest.getInstance("SHA-256")
                .digest(codeVerifier.toByteArray(Charsets.UTF_8))
            return Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(digest)
        }
    }
}