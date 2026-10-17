package com.kolsco.documentscanner

import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import android.service.quicksettings.TileService

class QuickToggleService : TileService() {
    override fun onClick() {
        val context = applicationContext
        val pm = context.packageManager
        val intent = pm.getLaunchIntentForPackage(context.packageName) ?: return
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        if (Build.VERSION.SDK_INT < 34) {
            startActivityAndCollapse(intent)
        } else {
            startActivityAndCollapse(PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_IMMUTABLE))
        }
    }
}