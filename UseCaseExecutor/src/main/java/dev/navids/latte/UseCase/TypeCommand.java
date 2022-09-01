package dev.navids.latte.UseCase;

import android.util.Log;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;

import dev.navids.latte.LatteService;

public class TypeCommand extends LocatableCommand {
    public String getText() {
        return text;
    }

    private String text;


    TypeCommand(JSONObject stepJson) {
        super(stepJson);
        String text = "";
        if (stepJson.containsKey("action_args")) {
            JSONArray args = (JSONArray) stepJson.get("action_args");
            text = String.valueOf(args.get(0));
        }
        this.text = text;
        Log.i(LatteService.TAG, "Type Step: " + this.getTargetWidgetInfo() + " " + this.text);
    }

    public static boolean isTypeStep(String action){
        return action.equals("send_keys");
    }

    @Override
    public String toString() {
        return String.format("TypeStep{State=%s,WidgetTarget=%s,Text=%s}", getState(), getTargetWidgetInfo(), text);
    }
}
