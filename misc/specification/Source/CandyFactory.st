PROGRAM program0
  VAR
    StartConveyorBelt : BOOL := FALSE;
    StopConveyorBelt : BOOL := FALSE;
    CandyCall : BOOL := FALSE;
    ConveyorRun : BOOL := FALSE;
    ConveyorVelocity : INT := 0;
    ExtractorStart : BOOL := FALSE;
    ExtractorRunning : BOOL := FALSE;
    ExtractorDone : BOOL := FALSE;
    SelectedCandy : INT := 0;
    DetectedCandy : INT := 0;
    ExtractorDoneTON : TON;
    ExtractorDoneTimer : TIME := T#1961ms;
  END_VAR

  ConveyorRun := (StartConveyorBelt OR ConveyorRun) AND NOT StopConveyorBelt AND NOT ExtractorRunning;

  IF SelectedCandy = DetectedCandy AND NOT (SelectedCandy = 0 AND DetectedCandy = 0) AND ConveyorRun THEN
      SelectedCandy := 0;
      CandyCall := TRUE;
  ELSE
      CandyCall := FALSE;
  END_IF;

  ExtractorDoneTON(
       IN := ExtractorRunning,
       PT := ExtractorDoneTimer,
       Q => ExtractorDone);

  IF CandyCall THEN
      StopConveyorBelt := TRUE;
      ConveyorRun := FALSE;
      ExtractorStart := TRUE;
      ExtractorRunning := TRUE;
  ELSE
      ExtractorStart := FALSE;
  END_IF;

  IF ExtractorDone THEN
      ExtractorDone := FALSE;
      ExtractorRunning := FALSE;
      StopConveyorBelt := FALSE;
  END_IF;
END_PROGRAM


CONFIGURATION config

  RESOURCE resource1 ON PLC
    TASK TaskMain(INTERVAL := T#50ms,PRIORITY := 0);
    PROGRAM inst0 WITH TaskMain : program0;
  END_RESOURCE
END_CONFIGURATION
