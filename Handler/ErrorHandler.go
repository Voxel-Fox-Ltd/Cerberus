package Handler

import (
	"Cerberus/Logging"
	"syscall"
)

/*
	Anything related to error management or handling goes here.
*/

func CheckError(err error, success Logging.LogMessage, failed Logging.LogMessage){
	if err != nil {
		// Not good
		failed.Text += "\n" + err.Error()
		Logging.Log(failed);

		if failed.Severity == Logging.Critical {
			// Really not good
			Logging.Log(Logging.LogMessage{"Critical error! Aborting!!!",Logging.Critical});
			syscall.Kill(syscall.Getpid(),syscall.SIGTERM);
		}
	}
	Logging.Log(success);
	return;
}