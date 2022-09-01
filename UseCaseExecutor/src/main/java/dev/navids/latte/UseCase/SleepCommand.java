package dev.navids.latte.UseCase;

import android.util.Log;

import org.json.simple.JSONObject;

import dev.navids.latte.LatteService;

public class SleepCommand extends Command {
    private long sleepTime;

    SleepCommand(JSONObject stepJson) {
        super(stepJson);
        long sleepTime = Long.parseLong((String) stepJson.getOrDefault("sleep", "-1"));
        if(sleepTime == -1) {
            Log.e(LatteService.TAG, "Issue with sleep step " + stepJson);
            sleepTime = 0;
        }
        this.sleepTime = sleepTime;
        Log.i(LatteService.TAG, "Sleep Step: " + this.sleepTime);
    }

    public static boolean isSleepAction(String action){
        return action.equals("sleep");
    }

    public long getSleepTime() {
        return sleepTime;
    }

    @Override
    public String toString() {
        return "SleepStep{" +
                "State=" + getState().name() +
                "sleepTime=" + sleepTime +
                '}';
    }
}
