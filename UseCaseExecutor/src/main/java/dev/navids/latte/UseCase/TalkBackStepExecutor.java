package dev.navids.latte.UseCase;

import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import dev.navids.latte.ActionUtils;
import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.Config;
import dev.navids.latte.LatteService;
import dev.navids.latte.TalkBackNavigator;
import dev.navids.latte.Utils;
import dev.navids.latte.WidgetInfo;

@Deprecated
public class TalkBackStepExecutor implements StepExecutor {
    private int waitAttemptsForFocusChange = 0;
    public int pendingActionId = 0;
    private List<String> maskedAttributes = Collections.emptyList();//Arrays.asList("resourceId", "xpath"); // TODO: Configurable
    private Map<Command, Map<WidgetInfo, Integer>> a11yNodeInfoTracker = new HashMap<>();
    @Override
    public boolean executeStep(Command step) {
        Log.i(LatteService.TAG, "TB Executing Step " + step);
        if(step.getState() != Command.CommandState.RUNNING)
            return false;
        if(!step.shouldExecuteByA11yAssistantService())
            return LatteService.getInstance().getStepExecutor("regular").executeStep(step);
        if(TalkBackNavigator.v().isPending()){
            Log.i(LatteService.TAG, "Do nothing since another action is pending!");
            return false;
        }
        if(step instanceof LocatableCommand) {
            LocatableCommand locatableCommand = (LocatableCommand) step;
            if (LatteService.getInstance().getAccessibilityFocusedNode() == null) {
                waitAttemptsForFocusChange++;
                handleNullFocusNode(step);
                return false;
            }
            waitAttemptsForFocusChange = 0;
            if(checkStoppingCriteria(step, locatableCommand)){
                Log.i(LatteService.TAG, "Reached Stopping Criteria!");
                return executeByRegularExecutor(step, locatableCommand);
            }
            // ------------ TODO: Need major refactor -----------------
            List<AccessibilityNodeInfo> matchedNodes = Utils.findSimilarNodes(locatableCommand.getTargetWidgetInfo());
            if(matchedNodes.size() != 1){ // TODO: Configurable, maybe we can tolerate multiple widgets with same info
                Log.i(LatteService.TAG, "The target widget is not unique. " + matchedNodes.size());
                locatableCommand.setState(Command.CommandState.FAILED);
                return false;
            }
            // matchedNodes.get(0) is our target
            List<AccessibilityNodeInfo> similarNodes = Utils.findSimilarNodes(locatableCommand.getTargetWidgetInfo(), maskedAttributes);
            if(!ActionUtils.isFocusedNodeTarget(similarNodes)){
                Log.i(LatteService.TAG, "Continue exploration!");
                TalkBackNavigator.v().performNext(null);
                return false;
            }
            // Because isFocusedNodeTarget(similarNodes) == true, the focusedNode represent similarNodes.get(0)
            if(!similarNodes.get(0).equals(matchedNodes.get(0))){
                Log.i(LatteService.TAG, "The located widget is not correct, use regular executor");
                return executeByRegularExecutor(step, locatableCommand);
            }
            locatableCommand.setActedWidget(ActualWidgetInfo.createFromA11yNode(LatteService.getInstance().getAccessibilityFocusedNode()));
            if(locatableCommand instanceof ClickCommand){
                ActionUtils.performDoubleTap();
                locatableCommand.setState(Command.CommandState.COMPLETED);
            }
            else if(locatableCommand instanceof TypeCommand){
                ActionUtils.performType(LatteService.getInstance().getAccessibilityFocusedNode(), ((TypeCommand) locatableCommand).getText());
                locatableCommand.setState(Command.CommandState.COMPLETED);
            }
            else{
                Log.e(LatteService.TAG, "This locatable step is unrecognizable " + locatableCommand);
                locatableCommand.setState(Command.CommandState.FAILED);
                return false;
            }
            return true;
        }
        else{
            Log.e(LatteService.TAG, "This step is unrecognizable " + step);
            step.setState(Command.CommandState.FAILED);
            return false;
        }
    }

    @Override
    public boolean interrupt() {
        TalkBackNavigator.v().interrupt();
        return false;
    }

    public static boolean executeByRegularExecutor(Command step, LocatableCommand locatableCommand) {
        LatteService.getInstance().getStepExecutor("regular").executeStep(step);
        if(step.getState() == Command.CommandState.COMPLETED) {
            locatableCommand.setState(Command.CommandState.COMPLETED_BY_HELP);
            return true;
        }
        locatableCommand.setState(Command.CommandState.FAILED);
        return false;
    }

    private boolean checkStoppingCriteria(Command step, LocatableCommand locatableCommand) {
        if(!a11yNodeInfoTracker.containsKey(step))
            a11yNodeInfoTracker.put(step, new HashMap<>());
        WidgetInfo focusedNodeWI = ActualWidgetInfo.createFromA11yNode(LatteService.getInstance().getAccessibilityFocusedNode());
        a11yNodeInfoTracker.get(step).put(focusedNodeWI,a11yNodeInfoTracker.get(step).getOrDefault(focusedNodeWI, 0)+1);
        locatableCommand.increaseActingAttempts();
        Log.i(LatteService.TAG, String.format("Widget %s is visited %d times", focusedNodeWI, a11yNodeInfoTracker.get(step).get(focusedNodeWI)));
        return locatableCommand.reachedMaxActingAttempts() || a11yNodeInfoTracker.get(step).get(focusedNodeWI) > Config.v().MAX_VISITED_WIDGET;
    }

    private void handleNullFocusNode(Command step) {
        if (waitAttemptsForFocusChange < Config.v().MAX_WAIT_FOR_FOCUS_CHANGE) {
            Log.i(LatteService.TAG, "Do nothing since no node is focused for " + waitAttemptsForFocusChange + " attempts.");
        }
        else if (waitAttemptsForFocusChange == Config.v().MAX_WAIT_FOR_FOCUS_CHANGE) {
            Log.i(LatteService.TAG, "Perform next to refocus!");
            TalkBackNavigator.v().performNext(null);
        }
        else if (waitAttemptsForFocusChange < Config.v().MAX_WAIT_FOR_FOCUS_CHANGE_AFTER_PERFORM_NEXT) {
            Log.i(LatteService.TAG, "Do nothing since no node is focused for " + waitAttemptsForFocusChange + " attempts. (After performing next)");
        }
        else {
            Log.i(LatteService.TAG, "Reached MAX_WAIT_FOR_FOCUS_CHANGE_AFTER_PERFORM_NEXT");
            step.setState(Command.CommandState.FAILED);
        }
    }
}
