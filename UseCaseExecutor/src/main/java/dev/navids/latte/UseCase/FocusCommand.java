package dev.navids.latte.UseCase;

import android.util.Log;

import org.json.simple.JSONObject;

import dev.navids.latte.LatteService;

public class FocusCommand extends LocatableCommand {
    FocusCommand(JSONObject stepJson) {
        super(stepJson);
        Log.i(LatteService.TAG, "Focusable Step: " + this.getTargetWidgetInfo());
    }
    public static boolean isFocusStep(String action){
        return action.equals("focus");
    }


    @Override
    public String toString() {
        return String.format("FocusStep{State=%s,WidgetTarget=%s}", getState(), getTargetWidgetInfo());
    }
}
