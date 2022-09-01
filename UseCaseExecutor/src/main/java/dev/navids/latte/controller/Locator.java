package dev.navids.latte.controller;

import dev.navids.latte.ActualWidgetInfo;
import dev.navids.latte.UseCase.LocatableCommand;

public interface Locator {
    public interface LocatorCallback{
        void onCompleted(ActualWidgetInfo actualWidgetInfo);
        void onError(String message);
    }
    void locate(LocatableCommand locatableCommand, LocatorCallback callback);
    void interrupt();
}

class DummyLocatorCallback implements Locator.LocatorCallback {

    @Override
    public void onCompleted(ActualWidgetInfo actualWidgetInfo) {

    }

    @Override
    public void onError(String message) {

    }
}
