package dev.navids.latte.UseCase;

import android.os.Bundle;
import android.util.Log;
import android.util.Pair;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.List;

import dev.navids.latte.ActionUtils;
import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.LatteService;
import dev.navids.latte.Utils;

@Deprecated
public class RegularStepExecutor implements StepExecutor {

    public static boolean is_physical = false;

    @Override
    public boolean executeStep(Command step) {
        Log.i(LatteService.TAG, "Reg Executing Step " + step + " Physical Touch: " + is_physical);
        if(step.getState() != Command.CommandState.RUNNING)
            return false;
        if(step instanceof LocatableCommand){
            LocatableCommand locatableCommand = (LocatableCommand) step;
            locatableCommand.increaseLocatingAttempts();
            List<AccessibilityNodeInfo> similarNodes = Utils.findSimilarNodes(locatableCommand.getTargetWidgetInfo());
            if(similarNodes.size() != 1){
                if(similarNodes.size() == 0) {
                    Log.i(LatteService.TAG, "The target widget could not be found in current screen.");
                    Log.i(LatteService.TAG, "The target XPATH: " + locatableCommand.getTargetWidgetInfo().getXpath());
                    List<AccessibilityNodeInfo> allNodes = Utils.getAllA11yNodeInfo(false);
                    for(AccessibilityNodeInfo nodeInfo : allNodes){
                        ActualWidgetInfo actualWidgetInfo = ActualWidgetInfo.createFromA11yNode(nodeInfo);
                        if (actualWidgetInfo != null)
                            Log.i(LatteService.TAG, "\t" + actualWidgetInfo.getXpath());
                    }
                }
                else{
                    Log.i(LatteService.TAG, "There are more than one candidates for the target.");
                    for(AccessibilityNodeInfo node : similarNodes){
                        Log.i(LatteService.TAG, " Node: " + node);
                    }
                }
                if(locatableCommand.reachedMaxLocatingAttempts()) {
                    locatableCommand.setState(Command.CommandState.FAILED);
                    return false;
                }
                return true;
            }
            else {
                AccessibilityNodeInfo node = similarNodes.get(0);
                locatableCommand.increaseActingAttempts();
                ActualWidgetInfo currentNodeInfo = ActualWidgetInfo.createFromA11yNode(node);
                locatableCommand.setActedWidget(currentNodeInfo);
                if(locatableCommand instanceof ClickCommand)
                    return executeClick((ClickCommand) locatableCommand, node);
                else if(locatableCommand instanceof TypeCommand)
                    return executeType((TypeCommand) locatableCommand, node);
                else if(locatableCommand instanceof FocusCommand)
                    return executeFocus((FocusCommand) locatableCommand, node);
                else {
                    Log.e(LatteService.TAG, "This locatable step is unrecognizable " + locatableCommand);
                    locatableCommand.setState(Command.CommandState.FAILED);
                    return false;
                }
            }
        }
        else {
            Log.e(LatteService.TAG, "This step is unrecognizable " + step);
            step.setState(Command.CommandState.FAILED);
            return false;
        }
    }

    @Override
    public boolean interrupt() {
        // TODO
        return false;
    }

    private boolean executeClick(ClickCommand clickStep, AccessibilityNodeInfo node){
        if(is_physical){
            Pair<Integer, Integer> clickableCoordinate = ActionUtils.getClickableCoordinate(node, false);
            int x =clickableCoordinate.first, y = clickableCoordinate.second;
            Log.e(LatteService.TAG, String.format("Physically clicking on (%d, %d)", x, y));
            boolean clickResult = ActionUtils.performTap(x, y);
            if(!clickResult){
                Log.e(LatteService.TAG, "The location could not be clicked.");
                clickStep.setState(Command.CommandState.FAILED);
                return false;
            }
            clickStep.setState(Command.CommandState.COMPLETED);
            return true;
        }
        else{
            AccessibilityNodeInfo clickableNode = node;
            while (clickableNode != null && !clickableNode.isClickable())
                clickableNode = clickableNode.getParent();
            if (clickableNode == null || !clickableNode.isClickable()) {
                Log.e(LatteService.TAG, "The widget is not clickable.");
                clickStep.setState(Command.CommandState.FAILED);
                return false;
            }
            ActualWidgetInfo clickableWidget = ActualWidgetInfo.createFromA11yNode(clickableNode);
            boolean result = clickableNode.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            Log.i(LatteService.TAG, "Clicking on widget: " + clickableWidget.completeToString(true));
            clickStep.setState(result ? Command.CommandState.COMPLETED : Command.CommandState.FAILED);
            return result;
        }
    }

    private boolean executeFocus(FocusCommand focusStep, AccessibilityNodeInfo node){
        boolean result = ActionUtils.a11yFocusOnNode(node);
        focusStep.setState(result ? Command.CommandState.COMPLETED : Command.CommandState.FAILED);
        return result;
    }

    private boolean executeType(TypeCommand typeStep, AccessibilityNodeInfo node){
        Bundle arguments = new Bundle();
        arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, typeStep.getText());
        boolean result = node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);
        typeStep.setState(result ? Command.CommandState.COMPLETED : Command.CommandState.FAILED);
        return result;
    }
}
