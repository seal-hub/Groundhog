package dev.navids.latte;


import androidx.annotation.Nullable;

//import org.json.JSONException;
//import org.json.JSONObject;

import org.json.simple.JSONObject;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

// TODO: Why WidgetInfo is Serializable?
public abstract class WidgetInfo implements Serializable {
    List<String> attributeNames = Arrays.asList(
            "resourceId", "contentDescription", "text", "class", "xpath");
    Map<String, String> attributes = new HashMap<>();

    public WidgetInfo(String resourceId) {
        this(resourceId, "", "", null);
    }
    public WidgetInfo(String resourceId, String contentDescription, String text, String clsName) {
        attributes.put(attributeNames.get(0), resourceId);
        attributes.put(attributeNames.get(1), contentDescription);
        attributes.put(attributeNames.get(2), text);
        attributes.put(attributeNames.get(3), clsName);
    }


    @Override
    public int hashCode() {
        int prime = 31;
        int result = 1;
        for(String attrName : attributeNames)
            result = result * prime + getAttr(attrName).hashCode();
        return result;
    }

    @Override
    public boolean equals(@Nullable Object obj) {
        if(!(obj instanceof  WidgetInfo))
            return false;
        return this.isSimilar((WidgetInfo) obj);
    }

    protected String getAttr(String attributeName){
        return attributes.getOrDefault(attributeName, "");
    }

    protected boolean hasAttr(String attributeName){
        String s = attributes.getOrDefault(attributeName, "");
        return s != null && !s.equals("") && !s.equals("null");
    }


    public boolean hasSimilarAttribute(WidgetInfo other, String attributeName)
    {
        return getAttr(attributeName).equals(other.getAttr(attributeName));
    }

    public boolean isSimilar(WidgetInfo other)
    {
        return isSimilar(other, Collections.emptyList());
    }

    public boolean isSimilar(WidgetInfo other, List<String> myMaskedAttributes)
    {
        boolean isSimilar = true;
        for(String attrName : attributeNames){
            if(myMaskedAttributes.contains(attrName))
                continue;
            boolean isSimilarAttribute = hasSimilarAttribute(other, attrName);
            if(!attrName.equals("xpath"))
                isSimilar &= isSimilarAttribute;
        }
        return isSimilar;
    }

    public void setXpath(String xpath) {
        this.attributes.put("xpath", xpath);
    }
    public abstract String getXpath();

    public String completeToString(boolean has_xpath){
        String xpath = has_xpath? " xpath= " + getXpath() : "";
        String id = hasAttr("resourceId") ? " ID= "+getAttr("resourceId")+", ": "";
        String cd = hasAttr("contentDescription") ? " CD= "+getAttr("contentDescription")+", ": "";
        String tx = hasAttr("text") ? " TX= "+getAttr("text")+", ": "";
        String cl = hasAttr("class") ? " CL= "+getAttr("class")+", ": "";
        String bound = hasAttr("class") ? " CL= "+getAttr("class")+", ": "";
        return id + cd + tx + cl + xpath;
    }

    public JSONObject getJSONCommand(String located_by, boolean skip, String action){
        JSONObject jsonCommand = new JSONObject();
        jsonCommand.put("resource_id", this.getAttr("resourceId"));
        jsonCommand.put("content_desc", this.getAttr("contentDescription"));
        jsonCommand.put("text", this.getAttr("text"));
        jsonCommand.put("class_name", this.getAttr("class"));
        jsonCommand.put("xpath", this.getAttr("xpath"));
        jsonCommand.put("located_by", located_by);
        jsonCommand.put("skip", skip);
        jsonCommand.put("action", action);
        return jsonCommand;
    }

    @Override
    public String toString() {
        return completeToString(false);
    }
}
