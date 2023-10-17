package Temp

import (
	"Cerberus/Handler"
	"Cerberus/Logging"
	"math/rand"
	"os"
	"time"

	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/opts"
	"github.com/go-echarts/go-echarts/v2/types"
)

func GraphActivity(){
	t := time.Now();
	chart := charts.NewLine();
	chart.SetGlobalOptions(
		charts.WithInitializationOpts(opts.Initialization{Theme: types.ThemeChalk}));

	chart.SetXAxis(make([]string,5000)).
		AddSeries("Points",GenerateItems()).
		SetSeriesOptions(charts.WithLineChartOpts(opts.LineChart{Smooth: true}));

	f,_ := os.Create("test.html");
	err := chart.Render(f);
	Handler.CheckError(err,Logging.LogMessage{"Took "+time.Now().Sub(t).String(),Logging.Verbose},Logging.LogMessage{"b",Logging.Error})
}

func GenerateItems() []opts.LineData{
	items := make([]opts.LineData,0);

	for i := 0;i<5000;i++{
		items = append(items, opts.LineData{Value: rand.Intn(10000)});
	}
	return items;
}
