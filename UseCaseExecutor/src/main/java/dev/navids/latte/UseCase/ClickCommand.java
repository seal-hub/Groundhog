package dev.navids.latte.UseCase;

import android.util.Log;

import org.json.simple.JSONObject;

import dev.navids.latte.LatteService;

public class ClickCommand extends LocatableCommand {
    ClickCommand(JSONObject stepJson) {
        super(stepJson);
        Log.i(LatteService.TAG, "Clickable Step: " + this.getTargetWidgetInfo());
    }
    public static boolean isClickStep(String action){
        return action.equals("click");
    }


    @Override
    public String toString() {
        return String.format("ClickStep{State=%s,WidgetTarget=%s}", getState(), getTargetWidgetInfo());
    }
}
