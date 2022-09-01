package dev.navids.latte;

public class Config {
    private static Config instance;
    private Config(){

    }
    public static Config v(){
        if(instance == null)
            instance = new Config();
        return instance;
    }

    public final String USECASE_RESULT_FILE_NAME = "test_result.txt";
    public final String CUSTOM_STEP_RESULT_FILE_NAME = "custom_step_result.txt";
    public final String CONTROLLER_RESULT_FILE_NAME = "controller_result.txt";
    public final String FINISH_NAVIGATION_FILE_PATH = "finish_nav_result.txt";
    public final String FINISH_ACTION_FILE_PATH = "finish_nav_action.txt";
    public final String LAYOUT_FILE_PATH = "a11y_layout.xml";
    public final String ATF_ISSUES_FILE_PATH = "aft_a11y_issues.jsonl";
    public final String IS_LIVE_FILE_PATH_PATTERN = "is_live_%s.txt";
    public final long GESTURE_DURATION = 400;
    public final long FOCUS_CHANGE_TIME = 100;
    public final long GESTURE_FINISH_WAIT_TIME = GESTURE_DURATION + FOCUS_CHANGE_TIME;
    public final long DOUBLE_TAP_BETWEEN_TIME = 100;
    public final int TAP_DURATION = 100;
    public final int MAX_LOCATING_ATTEMPT = 4;
    public final int MAX_ACTING_ATTEMPT = 50;
    public final int MAX_WAIT_FOR_FOCUS_CHANGE = 3;
    public final int MAX_WAIT_FOR_FOCUS_CHANGE_AFTER_PERFORM_NEXT = MAX_WAIT_FOR_FOCUS_CHANGE + 2;
    public final int MAX_VISITED_WIDGET = 4;
}
