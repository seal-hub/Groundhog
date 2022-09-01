package dev.navids.latte.UseCase;

import android.util.Log;

import java.util.List;
import java.util.Locale;

import dev.navids.latte.LatteService;

@Deprecated
public class UseCase {
    private List<Command> steps;
    int currentStepIndex = -1;
    private long startTime = -1;
    private long totalTime = 0;
    boolean isStarted(){
        return currentStepIndex > -1;
    }

    boolean isFinished(){
        getCurrentStepCommand();
        return currentStepIndex >= steps.size();
    }

    boolean start(){
        if(currentStepIndex != -1)
            return false;
        currentStepIndex = 0;
        startTime = System.currentTimeMillis();
        return true;
    }

    Command getCurrentStepCommand(){
        if (!(currentStepIndex >=0 && currentStepIndex < steps.size()))
            return null;
        while(steps.get(currentStepIndex).isDone()){
            Log.i(LatteService.TAG, "Step " + (currentStepIndex+1) + " is done!");
            currentStepIndex++;
            if(currentStepIndex >= steps.size()) {
                // All steps are done, now calculate the completion time
                totalTime = System.currentTimeMillis() - startTime;
                return null;
            }
        }
        return steps.get(currentStepIndex);
    }

    public int getStepCount(){
        return steps.size();
    }


    public UseCase(List<Command> steps) {
        this.steps = steps;
    }

    @Override
    public String toString() {
        return String.format(Locale.getDefault(), "UseCase{currentStepIndex=%d, TotalSteps=%d}", currentStepIndex, getStepCount());
    }

    public String getFinalResult(){
        long totalEvents = 0;
        int completeCount = 0;
        int unlocatedCount = 0;
        int unreachableCount = 0;
        int firstProbelmaticCommand = -1;
        int failedCount = 0;
        StringBuilder finalResult = new StringBuilder();
        for(int i=0; i<steps.size(); i++) {
            Command step = steps.get(i);
            int number_of_actions = 0;
            String actingWidget = "";
            if(step instanceof LocatableCommand){
                LocatableCommand locatableCommand = (LocatableCommand) step;
                totalEvents += locatableCommand.getNumberOfLocatingAttempts() + locatableCommand.getNumberOfActingAttempts();
                number_of_actions = locatableCommand.getNumberOfLocatingAttempts() + locatableCommand.getNumberOfActingAttempts();
                actingWidget = locatableCommand.getActedWidget().completeToString(true);
            }

            if(step.getState() != Command.CommandState.COMPLETED && firstProbelmaticCommand < 0)
                firstProbelmaticCommand = i+1;
            if(step.getState() == Command.CommandState.COMPLETED)
                completeCount++;
            else if(step.getState() == Command.CommandState.COMPLETED_BY_HELP)
                unlocatedCount++;
            else if(step.getState() == Command.CommandState.FAILED)
                failedCount++;
            String message = String.format(Locale.getDefault(),"   Step[%d] $ State: %s $ #Events: %d $ Time: %d $ ActingWidget: %s",
                    i + 1, step.getState().name(),
                    number_of_actions,
                    step.getTotalTime(),
                    actingWidget);
            finalResult.append(message).append("\n");
        }
        String message = String.format(Locale.getDefault(), "Result: %s $ Steps: %d $ Completed: %d $ Failed: %d $ Unlocatable: %d $ Unreachable: %d $ FirstProblem: %d $ TotalEvents: %d $ TotalTime: %d",
                completeCount == steps.size(),
                steps.size(),
                completeCount,
                failedCount,
                unlocatedCount,
                unreachableCount,
                firstProbelmaticCommand,
                totalEvents, totalTime);
        finalResult.append(message).append("\n");
        return finalResult.toString();

    }
}
