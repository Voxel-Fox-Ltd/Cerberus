package Logging

import (
	"fmt"
	"os"
	"time"
)

/*
	Log handling goes here
	Current logging style = [TIME] SEV | MESSAGE
*/

// The log file, you must run LogInit()!
var LogFile *os.File = nil;

func LogInit(){
	LogToConsole(LogMessage{"Starting Cerberus!",Verbose})
	os.Mkdir("Logs", os.ModePerm);
	logFileName := "Log-"+time.Now().Format("2006-01-02")+".txt";
	l, Err := os.OpenFile("Logs/"+logFileName, os.O_RDWR | os.O_CREATE | os.O_APPEND, 711); // 711 seems appropriate might give 766, 611, or just 777 a try too. 

	// To not have a import cycle and a edge case I'll be doing error check here seperately
	// If you can avoid this, please do!
	if Err!=nil{
		LogToConsole(LogMessage{"Failed to create a log file! Aborting...",Critical});
		os.Exit(1);
	}

	LogFile = l;
	Log(LogMessage{"Successfuly created a log file named \""+logFileName+"\"",Verbose});
}

func LogClose(){
	LogFile.Close();
	LogToConsole(LogMessage{"Closed Log file!",Verbose});
}

// Log command works for both console and file, it should be prefered when possible
func Log(message LogMessage){
	LogToFile(message);
	LogToConsole(message);
}

func LogToFile(message LogMessage){
	LogFile.WriteString(fmt.Sprintln(GetLogTime(),message.Severity,"|",message.Text));
}

func LogToConsole(message LogMessage){
	// ANSI Colours!
	sev := fmt.Sprintf("%s%s%s",GetANSI[message.Severity],message.Severity,ANSI_Clear);

	//[TIME] SEV | MESSAGE
	fmt.Println(GetLogTime(),sev,"|",message.Text);
}

func GetLogTime() string{
	// ISO 8601 RFC3339 specifications
	// YYYY-MM-DDTHH:mm:SS+UTC 
	return "["+time.Now().Format(time.RFC3339)+"]";
}