package dev.navids.latte;

import android.view.accessibility.AccessibilityNodeInfo;

@Deprecated
public interface Navigator {
    public AccessibilityNodeInfo nextFocus(ActionUtils.ActionCallback callback);
    public AccessibilityNodeInfo selectFocus(ActionUtils.ActionCallback callback);
    public boolean click(AccessibilityNodeInfo node, ActionUtils.ActionCallback callback);
    public AccessibilityNodeInfo locate(AccessibilityNodeInfo node, ActionUtils.ActionCallback callback);
}
