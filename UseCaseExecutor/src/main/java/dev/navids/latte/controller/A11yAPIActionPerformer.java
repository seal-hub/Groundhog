package dev.navids.latte.controller;

import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.LatteService;
import dev.navids.latte.UseCase.ClickCommand;

public class A11yAPIActionPerformer extends BaseActionPerformer {
    @Override
    public boolean executeClick(ClickCommand clickStep, ActualWidgetInfo actualWidgetInfo) {
        AccessibilityNodeInfo clickableNode = actualWidgetInfo.getA11yNodeInfo();
        while (clickableNode != null && !clickableNode.isClickable())
            clickableNode = clickableNode.getParent();
        if (clickableNode == null) {
            Log.e(LatteService.TAG, "The widget is not clickable.");
            return false;
        }
        return clickableNode.performAction(AccessibilityNodeInfo.ACTION_CLICK);
    }
}
