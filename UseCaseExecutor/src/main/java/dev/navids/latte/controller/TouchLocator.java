package dev.navids.latte.controller;

import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.ConceivedWidgetInfo;

public class TouchLocator extends BaseLocator{
    @Override
    protected LocatorResult locateAttempt(ConceivedWidgetInfo targetWidget) {
        LocatorResult result = super.locateAttempt(targetWidget);
        if(result.status != LocatorStatus.COMPLETED)
            return result;
        ActualWidgetInfo actualWidgetInfo = result.actualWidgetInfo;
        if (!actualWidgetInfo.getA11yNodeInfo().isVisibleToUser())
            return new LocatorResult(LocatorStatus.FAILED, "The widget is not visible!");
        return new LocatorResult(actualWidgetInfo);
    }
}
