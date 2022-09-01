package dev.navids.latte.UseCase;

import android.util.Log;

import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;

import dev.navids.latte.LatteService;

public abstract class Command {
    private CommandState state = CommandState.NOT_STARTED;
    private long startTime = -1;
    private long endTime = -1;
    private boolean executeByA11yAssistantService = true; // AKA skip

    Command(JSONObject stepJson){
        boolean skip = (boolean) stepJson.getOrDefault("skip", false);
        this.executeByA11yAssistantService = !skip;
    }

    public static Command createCommandFromJSON(String stepJsonString){
        JSONParser jsonParser = new JSONParser();
        try {
            JSONObject stepJSON = (JSONObject) jsonParser.parse(stepJsonString);
            return createCommandFromJSON(stepJSON);
        } catch (ParseException e) {
            e.printStackTrace();
            Log.e(LatteService.TAG, "CustomStep cannot be created " + e.getLocalizedMessage());
        }
        return null;
    }

    public static Command createCommandFromJSON(JSONObject commandJSON){
        try {
            String action = (String) commandJSON.getOrDefault("action", "UNKNOWN");
            Command command = null;
            if (SleepCommand.isSleepAction(action))
                command = new SleepCommand(commandJSON);
            else if (TypeCommand.isTypeStep(action))
                command = new TypeCommand(commandJSON);
            else if (ClickCommand.isClickStep(action))
                command = new ClickCommand(commandJSON);
            else if (FocusCommand.isFocusStep(action))
                command = new FocusCommand(commandJSON);
            else if (NextCommand.isNextAction(action))
                command = new NextCommand(commandJSON);
            else if (PreviousCommand.isPreviousAction(action))
                command = new PreviousCommand(commandJSON);
            else if (SelectCommand.isSelectCommand(action))
                command = new SelectCommand(commandJSON);
            else if (InfoCommand.isInfo(action))
                command = new InfoCommand(commandJSON);
            else
                command = null;
            return command;
        } catch (Exception e) {
            Log.e(LatteService.TAG, "Error in creating Step from Json: " + e.getMessage());
        }
        return null;
    }

    public CommandState getState() {
        return state;
    }

    public void setState(CommandState state) {
        this.state = state;
        switch (state){
            case NOT_STARTED:
                startTime = endTime = -1;
                break;
            case RUNNING:
                if(startTime == -1) {
                    startTime = System.currentTimeMillis();
                    endTime = -1;
                }
                break;
            case COMPLETED:
            case FAILED_PERFORM:
            case FAILED_LOCATE:
            case FAILED:
            case COMPLETED_BY_HELP:
                if(startTime != -1 && endTime == -1)
                    endTime = System.currentTimeMillis();
                break;
        }
    }

    public long getTotalTime(){
        return endTime - startTime;
    }

    public boolean isDone(){
        return state.equals(CommandState.COMPLETED) || state.equals(CommandState.FAILED) || state.equals(CommandState.COMPLETED_BY_HELP);
    }

    public boolean isNotStarted(){
        return state.equals(CommandState.NOT_STARTED);
    }

    public boolean shouldExecuteByA11yAssistantService() {
        return executeByA11yAssistantService;
    }

    public JSONObject getJSON(){
        JSONObject jsonObject = new JSONObject();
        jsonObject.put("duration", getTotalTime());
        jsonObject.put("type", this.getClass().getSimpleName());
        jsonObject.put("state", this.getState().name());
        return jsonObject;
    }

    public enum CommandState {
        NOT_STARTED,
        RUNNING,
        COMPLETED,
        FAILED_PERFORM,
        FAILED_LOCATE,
        FAILED,
        COMPLETED_BY_HELP
    }
}
