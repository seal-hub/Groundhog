package dev.navids.latte.UseCase;

import android.util.Log;

import org.json.simple.JSONObject;

import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.ConceivedWidgetInfo;
import dev.navids.latte.Config;
import dev.navids.latte.LatteService;

public abstract class LocatableCommand extends Command {
    private final ConceivedWidgetInfo targetWidget;

    public ActualWidgetInfo getActedWidget() {
        return actedWidget;
    }

    public void setActedWidget(ActualWidgetInfo actedWidget) {
        this.actedWidget = actedWidget;
    }

    private ActualWidgetInfo actedWidget = null;

    public int getNumberOfLocatingAttempts() {
        return numberOfLocatingAttempts;
    }

    int numberOfLocatingAttempts = 0;

    public void increaseLocatingAttempts() {
        numberOfLocatingAttempts += 1;
    }

    public boolean reachedMaxLocatingAttempts() {
        return numberOfLocatingAttempts >= Config.v().MAX_LOCATING_ATTEMPT;
    }

    public int getNumberOfActingAttempts() {
        return numberOfActingAttempts;
    }

    int numberOfActingAttempts = 0;

    public void increaseActingAttempts() {
        numberOfActingAttempts += 1;
    }

    public boolean reachedMaxActingAttempts() {
        return numberOfActingAttempts >= Config.v().MAX_ACTING_ATTEMPT;
    }

    LocatableCommand(JSONObject stepJson) {
        super(stepJson);
        Object obj = stepJson.getOrDefault("target", null);
        if (obj != null)
            targetWidget = ConceivedWidgetInfo.createFromJson((JSONObject) obj);
        else if (stepJson.containsKey("xpath")) { // Backward Compatibility
            targetWidget = ConceivedWidgetInfo.createFromJson(stepJson);
        } else {
            Log.e(LatteService.TAG, "The target widget is null!");
            targetWidget = new ConceivedWidgetInfo("", "", "", "", "", "");
        }
    }

    public static boolean isLocatableAction(String action) {
        return action.equals("click") || action.equals("send_keys");
    }

    public ConceivedWidgetInfo getTargetWidgetInfo() {
        return targetWidget;
    }

    @Override
    public JSONObject getJSON() {
        JSONObject jsonObject = super.getJSON();
        jsonObject.put("targetWidget", targetWidget.getJSONCommand("", false, ""));
        jsonObject.put("actedWidget", actedWidget == null ? null : actedWidget.getJSONCommand("", false, ""));
        jsonObject.put("locatingAttempts", getNumberOfLocatingAttempts());
        return jsonObject;
    }
}
