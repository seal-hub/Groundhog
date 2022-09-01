package dev.navids.latte.UseCase;

import org.json.simple.JSONObject;

public class InfoCommand extends Command {


    private String question = "";
    InfoCommand(JSONObject stepJson) {
        super(stepJson);
        question = (String) stepJson.getOrDefault("question", "");
    }
    @Override
    public JSONObject getJSON() {
        JSONObject jsonObject = super.getJSON();
        jsonObject.put("result", jsonResult == null ? null : jsonResult);
        return jsonObject;
    }

    public String getQuestion() {
        return question;
    }

    public JSONObject getJsonResult() {
        return jsonResult;
    }

    public static boolean isInfo(String action){
        return action.equals("info");
    }

    public void setJsonResult(JSONObject jsonResult) {
        this.jsonResult = jsonResult;
    }

    private JSONObject jsonResult = null;
}
