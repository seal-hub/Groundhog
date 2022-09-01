package dev.navids.latte.app;

import android.view.accessibility.AccessibilityEvent;

import dev.navids.latte.LatteService;

public class MyLatteService extends LatteService {
    static String TAG = "LATTE_SERVICE_APP";
    public MyLatteService() {
    }
    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        super.onAccessibilityEvent(event);
    }
}
