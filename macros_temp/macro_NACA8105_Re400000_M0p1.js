// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, 101, 0.05, 0.0, 0.08, 1.0, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber(0.1);
Polar.Analyze(400000, 400000, 400000, -10.0, 10.0, 1.0, 1.0, 1.0, 0, false);
Polar.Save("/home/nevilcp/ML_Aero/results/NACA8105_Re400000_M0p1_polar.xml");
JavaFoil.Exit();
