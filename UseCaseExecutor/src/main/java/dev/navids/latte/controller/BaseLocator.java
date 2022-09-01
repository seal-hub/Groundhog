package dev.navids.latte.controller;

import android.util.Log;

import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.ConceivedWidgetInfo;
import dev.navids.latte.LatteService;

public class BaseLocator extends AbstractLocator {
    @Override
    protected LocatorResult locateAttempt(ConceivedWidgetInfo targetWidget)
    {
        ActualWidgetInfo actualWidgetInfo = findActualWidget(targetWidget);
        if(actualWidgetInfo == null){
            Log.i(LatteService.TAG, "The target widget could not be found at this moment!");
            return new LocatorResult(LocatorStatus.WAITING);
        }
        return new LocatorResult(actualWidgetInfo);
    }
}
