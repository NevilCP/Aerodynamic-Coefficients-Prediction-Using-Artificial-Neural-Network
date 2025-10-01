// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, 101, 0.05, 0.0, 0.05, 7.0, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber(0.2);
Polar.Analyze(400000, 400000, 400000, -10.0, 10.0, 1.0, 1.0, 1.0, 0, false);
Polar.Save("/home/nevilcp/ML_Aero/results/NACA5705_Re400000_M0p2_polar.xml");
JavaFoil.Exit();
