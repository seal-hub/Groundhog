package dev.navids.latte;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Context;
import android.graphics.Path;
import android.graphics.Point;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.Handler;
import android.util.Log;
import android.util.Pair;
import android.view.Display;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

public class ActionUtils {
    public interface ActionCallback{
        void onCompleted(AccessibilityNodeInfo nodeInfo);
        void onError(String message);
    };
    private static Map<Integer, String> pendingActions = new HashMap<>();
    private static int pendingActionId = 0;
    public static boolean isActionPending(){
        return pendingActions.size() > 0;
    }
    public static void interrupt(){
        pendingActions.clear(); // TODO: Do we need to cancel the pending actions somehow?
    }

    static class DefaultGestureCallback extends AccessibilityService.GestureResultCallback {
        private ActionCallback actionCallback = null;
        DefaultGestureCallback(ActionCallback actionCallback){
            this.actionCallback = actionCallback;
        }
        DefaultGestureCallback(){this(null);};

        @Override
        public void onCompleted(GestureDescription gestureDescription) {
            Log.i(LatteService.TAG, "Complete Gesture " + gestureDescription.toString());
            if (actionCallback != null)
                actionCallback.onCompleted(null);
            super.onCompleted(gestureDescription);
        }

        @Override
        public void onCancelled(GestureDescription gestureDescription) {
            Log.i(LatteService.TAG, "Cancel Gesture " + gestureDescription.toString());
            if (actionCallback != null)
                actionCallback.onError("The gesture is cancelled");
            super.onCancelled(gestureDescription);
        }
    };

    public static boolean isFocusedNodeTarget(AccessibilityNodeInfo similarNode) {
        return isFocusedNodeTarget(Collections.singletonList(similarNode));
    }

    public static boolean isFocusedNodeTarget(List<AccessibilityNodeInfo> similarNodes) {
        if(similarNodes.size() == 0)
            return false;
        AccessibilityNodeInfo targetNode = similarNodes.get(0); // TODO: This strategy works even we found multiple similar widgets
        AccessibilityNodeInfo firstReachableNode = targetNode;
        boolean isSimilar = firstReachableNode != null && firstReachableNode.equals(LatteService.getInstance().getAccessibilityFocusedNode());
        if(!isSimilar) {
            AccessibilityNodeInfo it = targetNode;
            while (it != null) {
                if (it.isClickable()) {
                    firstReachableNode = it;
                    break;
                }
                it = it.getParent();
            }
            Log.i(LatteService.TAG, "-- FIRST REACHABLE NODE IS " + firstReachableNode);
            isSimilar = firstReachableNode != null && firstReachableNode.equals(LatteService.getInstance().getAccessibilityFocusedNode());
        }
        return isSimilar;
    }

    public static Pair<Integer, Integer> getClickableCoordinate(AccessibilityNodeInfo node){
        return getClickableCoordinate(node, true);
    }

    public static Pair<Integer, Integer> getClickableCoordinate(AccessibilityNodeInfo node, boolean excludeDescendantsBounds){
        int x, y;
        if(excludeDescendantsBounds)
        {
            // Find All Descendants of the node
            List<AccessibilityNodeInfo> descendants = new ArrayList<>();
            descendants.add(node);
            for (int i = 0; i < descendants.size(); i++) {
                AccessibilityNodeInfo child = descendants.get(i);
                for (int j = 0; j < child.getChildCount(); j++)
                    descendants.add(child.getChild(j));
            }
            descendants.remove(0);
            // ----
            Rect nodeBox = new Rect();
            node.getBoundsInScreen(nodeBox);
            int firstDescendantLeft = nodeBox.right;
            int lastDescendantRight = nodeBox.left;
            int firstDescendantTop = nodeBox.bottom;
            int lastDescendantBottom = nodeBox.top;
            for (AccessibilityNodeInfo child : descendants) {
                if(!child.isClickable())
                    continue;
                Rect box = new Rect();
                child.getBoundsInScreen(box);
                firstDescendantLeft = Integer.min(firstDescendantLeft, box.left);
                lastDescendantRight = Integer.max(lastDescendantRight, box.right);
                firstDescendantTop = Integer.min(firstDescendantTop, box.top);
                lastDescendantBottom = Integer.max(lastDescendantBottom, box.bottom);
            }
            Log.i(LatteService.TAG, " -------> " + nodeBox + " " + firstDescendantLeft + " " + lastDescendantRight + " " + firstDescendantTop + " " + lastDescendantBottom);
            if(firstDescendantLeft > nodeBox.left)
                x = (firstDescendantLeft+ nodeBox.left) / 2;
            else if(lastDescendantRight < nodeBox.right)
                x = (lastDescendantRight + nodeBox.right) / 2;
            else
                x = nodeBox.centerX();
            if(firstDescendantTop > nodeBox.top)
                y = (firstDescendantTop+nodeBox.top) / 2;
            else if(lastDescendantBottom < nodeBox.bottom)
                y = (firstDescendantTop+nodeBox.top) / 2;
            else
                y = nodeBox.centerY();
        }
        else {
            Rect box = new Rect();
            node.getBoundsInScreen(box);
            x = box.centerX();
            y = box.centerY();
        }
        return new Pair<>(x,y);
    }

    public static boolean performTap(Pair<Integer, Integer> coordinates){ return performTap(coordinates.first, coordinates.second); }
    public static boolean performTap(int x, int y){ return performTap(x, y, Config.v().TAP_DURATION); }
    public static boolean performTap(int x, int y, int duration){ return performTap(x, y, 0, duration); }
    public static boolean performTap(int x, int y, int startTime, int duration){ return performTap(x, y, startTime, duration, new DefaultGestureCallback()); }
    public static boolean performTap(int x, int y, int startTime, int duration, AccessibilityService.GestureResultCallback callback){
        if(x < 0 || y < 0)
            return false;
        GestureDescription.Builder gestureBuilder = new GestureDescription.Builder();
        Path swipePath = new Path();
        swipePath.moveTo(x, y);
        gestureBuilder.addStroke(new GestureDescription.StrokeDescription(swipePath, startTime, duration));
        GestureDescription gestureDescription = gestureBuilder.build();
        Log.i(LatteService.TAG, "Execute Gesture " + gestureDescription.toString());
        return LatteService.getInstance().dispatchGesture(gestureDescription, callback, null);
    }

    public static boolean performType(AccessibilityNodeInfo node, String message){
        Log.i(LatteService.TAG, "performType");
        Bundle arguments = new Bundle();
        arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, message);
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);
    }

    public static boolean performDoubleTap(){
        return performDoubleTap(new DefaultGestureCallback(null));
    }
    public static boolean performDoubleTap(ActionCallback callback){
        return performDoubleTap(new DefaultGestureCallback(callback));
    }
    public static boolean performDoubleTap(final AccessibilityService.GestureResultCallback callback){
        Log.i(LatteService.TAG, "performDoubleTap");
        try {
            Thread.sleep(300); // TODO: What is this?
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        return performDoubleTap(0, 0, callback);
    }
    public static boolean performDoubleTap(int x, int y, final AccessibilityService.GestureResultCallback callback){ return performDoubleTap(x, y, Config.v().TAP_DURATION, callback); }
    public static boolean performDoubleTap(int x, int y, int duration, final AccessibilityService.GestureResultCallback callback){ return performDoubleTap(x, y, 0, duration, callback); }
    public static boolean performDoubleTap(final int x, final int y, final int startTime, final int duration, final AccessibilityService.GestureResultCallback callback){
        AccessibilityService.GestureResultCallback newClickCallBack = new AccessibilityService.GestureResultCallback() {
            @Override
            public void onCompleted(GestureDescription gestureDescription) {
                Log.i(LatteService.TAG, "Complete Gesture " + gestureDescription.getStrokeCount());
                super.onCompleted(gestureDescription);
                try {
                    Thread.sleep(Config.v().DOUBLE_TAP_BETWEEN_TIME);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
                performTap(x, y, startTime, duration, callback);
            }

            @Override
            public void onCancelled(GestureDescription gestureDescription) {
                Log.i(LatteService.TAG, "Cancel Gesture");
                super.onCancelled(gestureDescription);
                if(callback != null)
                    callback.onCancelled(gestureDescription);
            }
        };
        return performTap(x, y, startTime, duration, newClickCallBack);
    }

    private static void executeSwipeGesture(String direction, String secondDirection, AccessibilityService.GestureResultCallback callback){
        GestureDescription.Builder gestureBuilder = new GestureDescription.Builder();
        Path swipePath = new Path();
        Random random = new Random();
        int BASE = 5;
        int dx1 = random.nextInt(2 * BASE) - BASE;
        int dx2 = random.nextInt(2 * BASE) - BASE;
        int dy1 = random.nextInt(2 * BASE) - BASE;
        int dy2 = random.nextInt(2 * BASE) - BASE;
        int x1, x2, y1, y2;
        WindowManager wm = (WindowManager) LatteService.getInstance().getApplicationContext().getSystemService(Context.WINDOW_SERVICE);
        Display display = wm.getDefaultDisplay();
        Point size = new Point();
        display.getSize(size);
        int width = size.x;
        int height = size.y;
        x1 = width / 2 + dx1;
        y1 = height / 2 + dy1;
        // TODO: The const values need to be configured
        switch (direction) {
            case "right":
                x2 = width - 100 + dx2;
                y2 = y1 + dy2;
                break;
            case "left":
                x2 = 100 + dx2;
                y2 = y1 + dy2;
                break;
            case "up":
                x2 = x1 + dx1;
                y2 = 100 + dy2;
                break;
            case "down":
                x2 = x1 + dx1;
                y2 = height - 100 + dy2;
                break;
            default:
                Log.e(LatteService.TAG, "Incorrect direction " + direction);
                return;
        }

        swipePath.moveTo(x1, y1);
        swipePath.lineTo(x2, y2);
        if (!secondDirection.isEmpty())
        {
            // TODO: Generalize to all directions
            if (direction.equals("up") && secondDirection.equals("left"))
            {
                Log.i(LatteService.TAG, "Add left direction to " + Integer.toString(100+dx1) + " " +Integer.toString(y2-dy1));
                swipePath.lineTo(100+dx1, y2-dy1);
            }
        }
        gestureBuilder.addStroke(new GestureDescription.StrokeDescription(swipePath, 0, Config.v().GESTURE_DURATION));
        GestureDescription gestureDescription = gestureBuilder.build();
        Log.i(LatteService.TAG, "Execute Gesture " + gestureDescription.toString());
        LatteService.getInstance().dispatchGesture(gestureDescription, callback, null);
    }

    public static boolean swipeLeft(ActionCallback doneCallback){ return swipeToDirection("left", doneCallback);}
    public static boolean swipeRight(ActionCallback doneCallback){ return swipeToDirection("right", doneCallback);}
    public static boolean swipeUp(ActionCallback doneCallback){ return swipeToDirection("up", doneCallback);}
    public static boolean swipeDown(ActionCallback doneCallback){ return swipeToDirection("down", doneCallback);}
    public static boolean swipeToDirection(String direction, ActionCallback doneCallback){
        return swipeToDirection(direction, "", doneCallback);
    }
    public static boolean swipeUpThenLeft(ActionCallback doneCallback){
        return swipeToDirection("up", "left", doneCallback);
    }
    public static boolean swipeToDirection(String direction, String secondDirection, ActionCallback doneCallback){
        if(isActionPending()){
            Log.i(LatteService.TAG, String.format("Do nothing since another action is pending! (Size:%d)", pendingActions.size()));
            return false;
        }
        final int thisActionId = pendingActionId;
        pendingActionId++;
        pendingActions.put(thisActionId, "Pending: I'm going to swipe " + direction);
        AccessibilityService.GestureResultCallback callback = new AccessibilityService.GestureResultCallback() {
            @Override
            public void onCompleted(GestureDescription gestureDescription) {
                new Handler().postDelayed(() -> {
                    pendingActions.remove(thisActionId);
                    if(doneCallback != null)
                        doneCallback.onCompleted(LatteService.getInstance().getAccessibilityFocusedNode());
                }, Config.v().GESTURE_FINISH_WAIT_TIME);

            }

            @Override
            public void onCancelled(GestureDescription gestureDescription) {
                Log.i(LatteService.TAG, "Gesture is cancelled!");
                pendingActions.remove(thisActionId);
                if(doneCallback != null)
                    doneCallback.onError("Gesture is cancelled!");
            }
        };

        new Handler().postDelayed(() -> { executeSwipeGesture(direction, secondDirection, callback);}, 10);
        return true;
    }

    public static boolean a11yFocusOnNode(AccessibilityNodeInfo node){
        AccessibilityNodeInfo currentFocusedNode = LatteService.getInstance().getAccessibilityFocusedNode();
        if (currentFocusedNode != null)
            currentFocusedNode.performAction(AccessibilityNodeInfo.ACTION_CLEAR_ACCESSIBILITY_FOCUS);
        ActualWidgetInfo focusableWidget = ActualWidgetInfo.createFromA11yNode(node);
        if (focusableWidget == null) {
            Log.e(LatteService.TAG, "The requested focusing  widget is null!");
            return false;
        }
        Log.i(LatteService.TAG, "Focusing on widget: " + focusableWidget.completeToString(true));
        return node.performAction(AccessibilityNodeInfo.ACTION_ACCESSIBILITY_FOCUS);
    }

    public static boolean focusOnNode(AccessibilityNodeInfo node){
        AccessibilityNodeInfo currentFocusedNode = LatteService.getInstance().getFocusedNode();
        if (currentFocusedNode != null)
            currentFocusedNode.performAction(AccessibilityNodeInfo.ACTION_CLEAR_FOCUS);
        ActualWidgetInfo focusableWidget = ActualWidgetInfo.createFromA11yNode(node);
        if (focusableWidget == null) {
            Log.e(LatteService.TAG, "The requested focusing  widget is null!");
            return false;
        }
        Log.i(LatteService.TAG, "Focusing on widget: " + focusableWidget.completeToString(true));
        return node.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
    }
}
