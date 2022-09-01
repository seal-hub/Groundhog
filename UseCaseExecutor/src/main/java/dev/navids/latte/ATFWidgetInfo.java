package dev.navids.latte;

import android.graphics.Rect;
import android.view.accessibility.AccessibilityNodeInfo;

import com.google.android.apps.common.testing.accessibility.framework.AccessibilityHierarchyCheckResult;
import com.google.android.apps.common.testing.accessibility.framework.uielement.ViewHierarchyElement;

import org.json.simple.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class ATFWidgetInfo extends WidgetInfo {
    AccessibilityHierarchyCheckResult accessibilityHierarchyCheckResult;
    ViewHierarchyElement node;
    public ATFWidgetInfo(String resourceId, String contentDescription, String text, String clsName, AccessibilityHierarchyCheckResult result) {
        super(resourceId, contentDescription, text, clsName);
        this.accessibilityHierarchyCheckResult = result;
        this.node = result.getElement();

    }

    public static ATFWidgetInfo createFromViewHierarchyElement(AccessibilityHierarchyCheckResult result){
        ViewHierarchyElement node = result.getElement();
        if (node == null){
            return null;
        }
        String resourceId = String.valueOf(node.getResourceName());
        String contentDescription = String.valueOf(node.getContentDescription());
        String text = String.valueOf(node.getText());
        String clsName = String.valueOf(node.getClassName());
        ATFWidgetInfo widgetInfo = new ATFWidgetInfo(resourceId, contentDescription, text, clsName, result);
        widgetInfo.setXpath(widgetInfo.getXpath());
        return widgetInfo;
    }

    @Override
    public String getXpath() {
        if(this.hasAttr("xpath"))
            return this.getAttr("xpath");
        List<String> names = new ArrayList<>();
        ViewHierarchyElement it = node;
        names.add(0, String.valueOf(it.getClassName()));
        while(it.getParentView() != null){

            int count = 0;
            int length = 0;
            String itClsName = String.valueOf(it.getClassName());
            for(int i=0; i<it.getParentView().getChildViewCount(); i++) {
                // TODO: possibility of ArrayIndexOutOfBoundsException

                ViewHierarchyElement child = it.getParentView().getChildView(i);
                if (child == null)
                    continue;
                String childClsName = String.valueOf(child.getClassName());
                if (!child.isVisibleToUser())
                    continue;
                if (itClsName.equals(childClsName))
                    length++;
                if (child.equals(it)) {
                    count = length;
                }
            }
            if(length > 1)
                names.set(0, String.format("%s[%d]", names.get(0), count));
            it = it.getParentView();
            names.add(0, String.valueOf(it.getClassName()));
            //            xpath = String.valueOf(it.getClassName()) + "/" + xpath;
        }
        String xpath = "/"+String.join("/", names);
        return xpath;
    }

    @Override
    public boolean hasSimilarAttribute(WidgetInfo other, String attributeName) {
        throw new UnsupportedOperationException();
    }

    @Override
    public boolean isSimilar(WidgetInfo other) {
        throw new UnsupportedOperationException();
    }

    @Override
    public boolean isSimilar(WidgetInfo other, List<String> myMaskedAttributes) {
        throw new UnsupportedOperationException();
    }

    @Override
    public String completeToString(boolean has_xpath) {
        String base_path = super.completeToString(has_xpath);
        com.google.android.apps.common.testing.accessibility.framework.replacements.Rect boundBox = node.getBoundsInScreen();
        String str = String.format(Locale.US, "%s-%s-%s, bounds= [%d,%d][%d,%d]",
                accessibilityHierarchyCheckResult.getType(),
                accessibilityHierarchyCheckResult.getSourceCheckClass().getSimpleName(),
                base_path, boundBox.getLeft(), boundBox.getTop(), boundBox.getRight(), boundBox.getBottom());
        return str;
    }

    @Override
    public JSONObject getJSONCommand(String located_by, boolean skip, String action){
        JSONObject result = super.getJSONCommand(located_by, skip, action);
        if (result == null)
            return result;
        com.google.android.apps.common.testing.accessibility.framework.replacements.Rect boundBox = node.getBoundsInScreen();
        result.put("bounds", String.format("[%d,%d][%d,%d]", boundBox.getLeft(), boundBox.getTop(), boundBox.getRight(), boundBox.getBottom()));
        result.put("ATFSeverity", accessibilityHierarchyCheckResult.getType().toString());
        result.put("ATFType", accessibilityHierarchyCheckResult.getSourceCheckClass().getSimpleName());
        return result;
    }

    @Override
    public String toString() {
        return "ATFWidgetInfo{"
                + super.toString()
                + "}";
    }
}
