package dev.navids.latte.controller;

import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.zip.Deflater;

import dev.navids.latte.ActionUtils;
import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.LatteService;
import dev.navids.latte.UseCase.ClickCommand;
import dev.navids.latte.UseCase.FocusCommand;
import dev.navids.latte.UseCase.NextCommand;
import dev.navids.latte.UseCase.PreviousCommand;
import dev.navids.latte.UseCase.SelectCommand;
import dev.navids.latte.UseCase.TypeCommand;

public class TalkBackActionPerformer extends BaseActionPerformer {
    static class TalkBackActionCallback implements ActionUtils.ActionCallback{
        private ExecutorCallback callback;
        TalkBackActionCallback(ExecutorCallback callback){
            if (callback == null)
                this.callback = new DummyExecutorCallback();
            this.callback = callback;
        }
        @Override
        public void onCompleted(AccessibilityNodeInfo nodeInfo) {
            callback.onCompleted(ActualWidgetInfo.createFromA11yNode(nodeInfo));
        }

        @Override
        public void onError(String message) {
            callback.onError(message);
        }
    }

    private boolean isNotFocused(ActualWidgetInfo actualWidgetInfo) {
        if(!ActionUtils.isFocusedNodeTarget(actualWidgetInfo.getA11yNodeInfo())){
            Log.e(LatteService.TAG, String.format("The focused node %s is different from target node %s", LatteService.getInstance().getAccessibilityFocusedNode(), actualWidgetInfo));
            return true;
        }
        return false;
    }

    @Override
    public boolean executeClick(ClickCommand clickStep, ActualWidgetInfo actualWidgetInfo) {
        if (isNotFocused(actualWidgetInfo))
            return false;
        return ActionUtils.performDoubleTap();
    }

    @Override
    public boolean executeType(TypeCommand typeStep, ActualWidgetInfo actualWidgetInfo) {
        if (isNotFocused(actualWidgetInfo))
            return false;
        return super.executeType(typeStep, actualWidgetInfo);
    }

    @Override
    public boolean executeFocus(FocusCommand focusStep, ActualWidgetInfo actualWidgetInfo) {
        if (isNotFocused(actualWidgetInfo))
            return false;
        return super.executeFocus(focusStep, actualWidgetInfo);
    }

    @Override
    public void navigateNext(NextCommand nextStep, ExecutorCallback callback) {
        ActionUtils.swipeRight(new TalkBackActionCallback(callback));
    }

    @Override
    public void navigatePrevious(PreviousCommand previousStep, ExecutorCallback callback) {
        ActionUtils.swipeLeft(new TalkBackActionCallback(callback));
    }

    @Override
    public void navigateSelect(SelectCommand selectCommand, ExecutorCallback callback) {
        if(callback == null)
            callback = new DummyExecutorCallback();
        AccessibilityNodeInfo focusedNode = LatteService.getInstance().getAccessibilityFocusedNode();
        ExecutorCallback finalCallback = callback;
        ActionUtils.performDoubleTap(new ActionUtils.ActionCallback() {
            @Override
            public void onCompleted(AccessibilityNodeInfo nodeInfo) {
                finalCallback.onCompleted(ActualWidgetInfo.createFromA11yNode(focusedNode));
            }

            @Override
            public void onError(String message) {
                finalCallback.onError(message);
            }
        });
    }
}
