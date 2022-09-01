package dev.navids.latte;

import android.graphics.Rect;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.simple.JSONObject;

import java.util.ArrayList;
import java.util.List;

public class ActualWidgetInfo extends WidgetInfo {
    AccessibilityNodeInfo node;
    public ActualWidgetInfo(String resourceId, String contentDescription, String text, String clsName, AccessibilityNodeInfo node) {
        super(resourceId, contentDescription, text, clsName);
        this.node = node;

    }

    public static ActualWidgetInfo createFromA11yNode(AccessibilityNodeInfo node){
        return createFromA11yNode(node, false);
    }

    /**
     * @param fix_text "If it's true, it will create content description or text for parent views like Layout
     */
    public static ActualWidgetInfo createFromA11yNode(AccessibilityNodeInfo node, boolean fix_text){
        if (node == null){
            return null;
        }
        String resourceId = String.valueOf(node.getViewIdResourceName());
        String contentDescription = String.valueOf(node.getContentDescription());
        String text = String.valueOf(node.getText());
        String clsName = String.valueOf(node.getClassName());
        if(fix_text) {
            if (clsName.endsWith("Layout")) {
                if (text.equals("null") && contentDescription.equals("null")) {
                    String tmp = Utils.getFirstText(node);
                    if (tmp != null)
                        text = tmp;
                    else {
                        tmp = Utils.getFirstContentDescription(node);
                        if (tmp != null)
                            contentDescription = tmp;
                    }
                }
            }
        }
        ActualWidgetInfo widgetInfo = new ActualWidgetInfo(resourceId, contentDescription, text, clsName, node);
        widgetInfo.setXpath(widgetInfo.getXpath());
        return widgetInfo;
    }

    public AccessibilityNodeInfo getA11yNodeInfo() {
        return node;
    }


    @Override
    public String getXpath() {
        if(this.hasAttr("xpath"))
            return this.getAttr("xpath");
        List<String> names = new ArrayList<>();
        AccessibilityNodeInfo it = node;
        names.add(0, String.valueOf(it.getClassName()));
        while(it.getParent() != null){

            int count = 0;
            int length = 0;
            String itClsName = String.valueOf(it.getClassName());
            for(int i=0; i<it.getParent().getChildCount(); i++) {
                // TODO: possibility of ArrayIndexOutOfBoundsException

                AccessibilityNodeInfo child = it.getParent().getChild(i);
                if (child == null)
                    continue;
                String childClsName = String.valueOf(child.getClassName());
                if (!LatteService.considerInvisibleNodes && !child.isVisibleToUser())
                    continue;
                if (itClsName.equals(childClsName))
                    length++;
                if (child.equals(it)) {
                    count = length;
                }
            }
            if(length > 1)
                names.set(0, String.format("%s[%d]", names.get(0), count));
            it = it.getParent();
            names.add(0, String.valueOf(it.getClassName()));
            //            xpath = String.valueOf(it.getClassName()) + "/" + xpath;
        }
        String xpath = "/"+String.join("/", names);
        return xpath;
    }

    @Override
    public boolean hasSimilarAttribute(WidgetInfo other, String attributeName) {
        if(other instanceof ConceivedWidgetInfo)
            return other.hasSimilarAttribute(this, attributeName);
        return super.hasSimilarAttribute(other, attributeName);
    }

    @Override
    public boolean isSimilar(WidgetInfo other) {
        if(other instanceof ConceivedWidgetInfo)
            return other.isSimilar(this);
        return super.isSimilar(other);
    }

    @Override
    public boolean isSimilar(WidgetInfo other, List<String> myMaskedAttributes) {
        if(other instanceof ConceivedWidgetInfo)
            return other.isSimilar(this, myMaskedAttributes);
        return super.isSimilar(other, myMaskedAttributes);
    }

    @Override
    public String completeToString(boolean has_xpath) {
        String base_path = super.completeToString(has_xpath);
        Rect boundBox = new Rect();
        node.getBoundsInScreen(boundBox);
        String str = String.format("%s, bounds= [%d,%d][%d,%d]",base_path, boundBox.left, boundBox.top, boundBox.right, boundBox.bottom);
        return str;
    }

    @Override
    public JSONObject getJSONCommand(String located_by, boolean skip, String action){
        JSONObject result = super.getJSONCommand(located_by, skip, action);
        if (result == null)
            return result;
        Rect boundBox = new Rect();
        node.getBoundsInScreen(boundBox);
        result.put("bounds", String.format("[%d,%d][%d,%d]", boundBox.left, boundBox.top, boundBox.right, boundBox.bottom));
        return result;
    }

    @Override
    public String toString() {
        return "ActualWidgetInfo{"
                + super.toString()
                + "}";
    }
}
