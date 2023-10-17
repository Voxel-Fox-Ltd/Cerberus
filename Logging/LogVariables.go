package Logging

/*
	Log data, structs and variables are here
*/
type LogMessage struct {
	Text string
	Severity severity
}

// Max 4 characters
type severity string
const (
	Critical severity = "CRIT" // same as fatal
	Error     = "ERR"
	Warning   = "WARN"
	Info      = "INFO"
	Verbose   = "VERB" // same as Debug
)

// using 8-bit codes
type ANSI string
const (
	ANSI_Critical ANSI = "\033[48:5:196m"
	ANSI_Error         = "\033[48:5:88m"
	ANSI_Warning       = "\033[48:5:178m"
	ANSI_Info          = "\033[48:5:38m"
	ANSI_Verbose       = "\033[48:5:28m"
	ANSI_Clear         = "\033[0m"
)

// map to get severity's ansicode
var GetANSI = map[severity]ANSI{
	Critical: ANSI_Critical,
	Error:    ANSI_Error,
	Warning:  ANSI_Warning,
	Info:     ANSI_Info,
	Verbose:  ANSI_Verbose,
}