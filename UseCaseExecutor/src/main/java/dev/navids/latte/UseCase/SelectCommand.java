package dev.navids.latte.UseCase;

import android.util.Log;

import org.json.simple.JSONObject;

import dev.navids.latte.LatteService;

public class SelectCommand extends NavigateCommand {

    SelectCommand(JSONObject stepJson) {
        super(stepJson);
        Log.i(LatteService.TAG, "Select Command");
    }

    public static boolean isSelectCommand(String action){
        return action.equals("select");
    }


    @Override
    public String toString() {
        return "SelectStep{" +
                "State=" + getState().name() +
                '}';
    }
}
