package dev.navids.latte.UseCase;

@Deprecated
public interface StepExecutor {
    boolean executeStep(Command step);
    boolean interrupt();
}
