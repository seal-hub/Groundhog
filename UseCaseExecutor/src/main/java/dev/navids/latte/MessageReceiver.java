package dev.navids.latte;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;
import android.util.Xml;
import android.view.accessibility.AccessibilityNodeInfo;

import com.google.android.apps.common.testing.accessibility.framework.AccessibilityCheckPreset;
import com.google.android.apps.common.testing.accessibility.framework.AccessibilityCheckResult;
import com.google.android.apps.common.testing.accessibility.framework.AccessibilityCheckResultUtils;
import com.google.android.apps.common.testing.accessibility.framework.AccessibilityHierarchyCheck;
import com.google.android.apps.common.testing.accessibility.framework.AccessibilityHierarchyCheckResult;
import com.google.android.apps.common.testing.accessibility.framework.Parameters;
import com.google.android.apps.common.testing.accessibility.framework.checks.ImageContrastCheck;
import com.google.android.apps.common.testing.accessibility.framework.checks.TextContrastCheck;
import com.google.android.apps.common.testing.accessibility.framework.checks.TouchTargetSizeCheck;
import com.google.android.apps.common.testing.accessibility.framework.uielement.AccessibilityHierarchyAndroid;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;
import org.xmlpull.v1.XmlSerializer;

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import dev.navids.latte.UseCase.RegularStepExecutor;
import dev.navids.latte.UseCase.SightedTalkBackStepExecutor;
import dev.navids.latte.UseCase.StepExecutor;
import dev.navids.latte.UseCase.UseCaseExecutor;
import dev.navids.latte.controller.Controller;

public class MessageReceiver extends BroadcastReceiver {
    static final String MESSAGE_INTENT = "dev.navids.latte.COMMAND";
    static final String MESSAGE_CODE = "command";
    static final String MESSAGE_EXTRA_CODE = "extra";

    interface MessageEvent {
        void doAction(String extra);
    }
    private Map<String, MessageEvent> messageEventMap = new HashMap<>();

    public MessageReceiver() {
        super();
        // ----------- General ----------------
        messageEventMap.put("is_live", (extra) -> Utils.createFile(String.format(Config.v().IS_LIVE_FILE_PATH_PATTERN, extra), "I'm alive " + extra));
        messageEventMap.put("log", (extra) -> Utils.getAllA11yNodeInfo(true));
        messageEventMap.put("invisible_nodes", (extra) -> LatteService.considerInvisibleNodes = (extra.equals("true")));
        messageEventMap.put("report_a11y_issues", (extra) -> {
            Context context2 = LatteService.getInstance().getApplicationContext();
            Set<AccessibilityHierarchyCheck> contrastChecks = new HashSet<>(Arrays.asList(
                    AccessibilityCheckPreset.getHierarchyCheckForClass(TextContrastCheck.class),
                    AccessibilityCheckPreset.getHierarchyCheckForClass(ImageContrastCheck.class)
            ));
            Set<AccessibilityHierarchyCheck> touchTargetChecks = new HashSet<>(Arrays.asList(
                    AccessibilityCheckPreset.getHierarchyCheckForClass(TouchTargetSizeCheck.class)
            ));
            Set<AccessibilityHierarchyCheck> checks =
                    AccessibilityCheckPreset.getAccessibilityHierarchyChecksForPreset(
                            AccessibilityCheckPreset.LATEST);
            if(extra.equals("contrast"))
                checks = contrastChecks;
            else if(extra.equals("touch"))
                checks = touchTargetChecks;
            AccessibilityNodeInfo rootNode = LatteService.getInstance().getRootInActiveWindow();
            AccessibilityHierarchyAndroid hierarchy = AccessibilityHierarchyAndroid.newBuilder(rootNode, context2).build();
            List<AccessibilityHierarchyCheckResult> results = new ArrayList<>();
            for (AccessibilityHierarchyCheck check : checks) {
                Parameters params = new Parameters();
                params.putCustomTouchTargetSize(39);
                results.addAll(check.runCheckOnHierarchy(hierarchy, null, params));
            }
            List<AccessibilityHierarchyCheckResult> returnedResult = AccessibilityCheckResultUtils.getResultsForType(
                    results, AccessibilityCheckResult.AccessibilityCheckResultType.ERROR);
            returnedResult.addAll(AccessibilityCheckResultUtils.getResultsForType(
                    results, AccessibilityCheckResult.AccessibilityCheckResultType.WARNING));
//            Log.i(LatteService.TAG, "Issue Size: " + returnedResult.size() + " " + results.size());
            StringBuilder report_jsonl = new StringBuilder();
            for (AccessibilityHierarchyCheckResult res: returnedResult) {
                ATFWidgetInfo widgetInfo = ATFWidgetInfo.createFromViewHierarchyElement(res);
                if (widgetInfo == null)
                    continue;
                JSONObject jsonCommand = widgetInfo.getJSONCommand("", false, "");
                String jsonCommandStr = jsonCommand != null ? jsonCommand.toJSONString() : "Error";
                report_jsonl.append(jsonCommandStr).append("\n");
            }
            Utils.createFile(Config.v().ATF_ISSUES_FILE_PATH, report_jsonl.toString());
        });
        messageEventMap.put("capture_layout", (extra) -> {
            try {
                XmlSerializer serializer = Xml.newSerializer();
                StringWriter stringWriter = new StringWriter();
                serializer.setOutput(stringWriter);
                serializer.startDocument("UTF-8", true);
                serializer.startTag("", "hierarchy");
                serializer.attribute("", "rotation", "0"); // TODO:
                Utils.dumpNodeRec(serializer, 0);
                serializer.endTag("", "hierarchy");
                serializer.endDocument();
                Utils.createFile(Config.v().LAYOUT_FILE_PATH, stringWriter.toString());
            } catch (IOException e) {
                e.printStackTrace();
            }
        });
        // ---------------------------- TalkBack Navigation -----------
        messageEventMap.put("nav_next", (extra) -> TalkBackNavigator.v().changeFocus(null, false));
        messageEventMap.put("nav_prev", (extra) -> TalkBackNavigator.v().changeFocus(null, true));
        messageEventMap.put("nav_select", (extra) -> TalkBackNavigator.v().selectFocus(null));
        messageEventMap.put("nav_current_focus", (extra) -> TalkBackNavigator.v().currentFocus());
        messageEventMap.put("tb_a11y_tree", (extra) -> TalkBackNavigator.v().logTalkBackTreeNodeList(null));
        messageEventMap.put("nav_clear_history", (extra) -> TalkBackNavigator.v().clearHistory());
        messageEventMap.put("nav_api_focus", (extra) -> SightedTalkBackStepExecutor.apiFocus = (extra.equals("true")));
        messageEventMap.put("nav_interrupt", (extra) -> TalkBackNavigator.v().interrupt());
        // --------------------------- UseCase Executor ----------------
        messageEventMap.put("controller_set", (extra) -> {
            LatteService.getInstance().getSelectedController().interrupt();
            LatteService.getInstance().getSelectedController().clearResult();
            Controller controller = LatteService.getInstance().getController(extra);
            if (controller != null) {
                Log.i(LatteService.TAG, "The controller " + extra + " is selected!");
                LatteService.getInstance().setSelectedController(controller);
            }
            else
                Log.e(LatteService.TAG, "The controller " + extra + " could not be found!");
        });
        messageEventMap.put("controller_execute", (extra) -> LatteService.getInstance().getSelectedController().executeCommand(extra));
        messageEventMap.put("controller_interrupt", (extra) -> LatteService.getInstance().getSelectedController().interrupt());
        messageEventMap.put("controller_reset", (extra) -> {
            LatteService.getInstance().getSelectedController().interrupt();
            LatteService.getInstance().getSelectedController().clearResult();
        });
        // --------------------------- UseCase Executor ----------------
        messageEventMap.put("enable", (extra) -> UseCaseExecutor.v().enable());
        messageEventMap.put("disable", (extra) -> UseCaseExecutor.v().disable());
        messageEventMap.put("init", (extra) -> {
            String usecase_path = extra;
            File file = new File(usecase_path);
            JSONParser jsonParser = new JSONParser();
            JSONArray commandsJson = null;
            try (FileReader reader = new FileReader(file)) {
                // TODO: tons of refactor!
                //Read JSON file
                Object obj = jsonParser.parse(reader);
                commandsJson = (JSONArray) obj;
                UseCaseExecutor.v().init(commandsJson);
            } catch (IOException | ParseException e) {
                e.printStackTrace();
            }
        });
        messageEventMap.put("start", (extra) -> UseCaseExecutor.v().start());
        messageEventMap.put("stop", (extra) -> UseCaseExecutor.v().stop());
        messageEventMap.put("step_clear", (extra) -> UseCaseExecutor.v().clearHistory());
        messageEventMap.put("step_execute", (extra) -> UseCaseExecutor.v().initiateCustomStep(extra));
        messageEventMap.put("step_interrupt", (extra) -> UseCaseExecutor.v().interruptCustomStepExecution());
        messageEventMap.put("set_delay", (extra) -> UseCaseExecutor.v().setDelay(Long.parseLong(extra)));
        messageEventMap.put("set_step_executor", (extra) -> {
            StepExecutor stepExecutor = LatteService.getInstance().getStepExecutor(extra);
            if(stepExecutor != null) {
                if(extra.equals("talkback"))
                    RegularStepExecutor.is_physical = false;
                UseCaseExecutor.v().setStepExecutor(stepExecutor);
            }
        });
        messageEventMap.put("set_physical_touch", (extra) -> {
            RegularStepExecutor.is_physical = extra.equals("true");
            Log.i(LatteService.TAG, String.format("RegularStepExecutor %suse physical touch", RegularStepExecutor.is_physical ? "" : "does NOT "));
        });
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        String message = intent.getStringExtra(MESSAGE_CODE);
        String extra = intent.getStringExtra(MESSAGE_EXTRA_CODE);
        // De-sanitizing extra value ["\s\,]
        extra = extra.replace("__^__", "\"")
                .replace("__^^__", " ")
                .replace("__^^^__", ",")
                .replace("__^_^__", "'")
                .replace("__^-^__", "+")
                .replace("__^^^^__", "|")
                .replace("__^_^^__", "$")
                .replace("__^-^^__", "*")
                .replace("__^^_^__", "&")
                .replace("__^^-^__", "[")
                .replace("__^^^^^__", "]"); // TODO: Configurable

        if (message == null || extra == null) {
            Log.e(LatteService.TAG, "The command or extra message is null!");
            return;
        }
        Log.i(LatteService.TAG, String.format("The command %s received!", message + (extra.equals("NONE") ? "" : " - " + extra)));
        try {
            if (message.equals("sequence")) {
                try {
                    JSONParser jsonParser = new JSONParser();
                    JSONArray commandsJson = null;
                    Object obj = null;
                    obj = jsonParser.parse(extra);
                    commandsJson = (JSONArray) obj;
                    for (int i = 0; i < commandsJson.size(); i++) {
                        JSONObject commandJson = (JSONObject) commandsJson.get(i);
                        String commandStr = (String) commandJson.getOrDefault("command", "NONE");
                        String extraStr = (String) commandJson.getOrDefault("extra", "NONE");
                        if (messageEventMap.containsKey(commandStr)) {
                            Log.i(LatteService.TAG, String.format("Executing command %s with extraStr %s!", commandStr, extraStr));
                            messageEventMap.get(commandStr).doAction(extraStr);
                        }
                    }

                } catch (ParseException e) {
                    e.printStackTrace();
                }
            } else {
                if (messageEventMap.containsKey(message))
                    messageEventMap.get(message).doAction(extra);
            }
        }
        catch (Exception e){
            Log.e(LatteService.TAG, "Exception happens during command receiver execution", e);
        }
    }
}
