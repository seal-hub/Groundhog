package dev.navids.latte.controller;

import android.os.Bundle;
import android.view.accessibility.AccessibilityNodeInfo;

import dev.navids.latte.ActionUtils;
import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.UseCase.ClickCommand;
import dev.navids.latte.UseCase.FocusCommand;
import dev.navids.latte.UseCase.NextCommand;
import dev.navids.latte.UseCase.PreviousCommand;
import dev.navids.latte.UseCase.SelectCommand;
import dev.navids.latte.UseCase.TypeCommand;

public class BaseActionPerformer extends AbstractActionPerformer {

    @Override
    public boolean executeClick(ClickCommand clickStep, ActualWidgetInfo actualWidgetInfo) {
        return actualWidgetInfo.getA11yNodeInfo().performAction(AccessibilityNodeInfo.ACTION_CLICK);
    }

    @Override
    public boolean executeType(TypeCommand typeStep, ActualWidgetInfo actualWidgetInfo) {
        Bundle arguments = new Bundle();
        arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, typeStep.getText());
        return actualWidgetInfo.getA11yNodeInfo().performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);
    }

    @Override
    public boolean executeFocus(FocusCommand focusStep, ActualWidgetInfo actualWidgetInfo) {
        return ActionUtils.focusOnNode(actualWidgetInfo.getA11yNodeInfo());
    }

    @Override
    public void navigateNext(NextCommand nextStep, ExecutorCallback callback) {

    }

    @Override
    public void navigatePrevious(PreviousCommand previousStep, ExecutorCallback callback) {

    }

    @Override
    public void navigateSelect(SelectCommand selectCommand, ExecutorCallback callback) {
        
    }
}
