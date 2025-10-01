// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, 101, 0.35, 0.0, 0.09, 2.0, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber(0.3);
Polar.Analyze(200000, 200000, 200000, -10.0, 10.0, 1.0, 1.0, 1.0, 0, false);
Polar.Save("/home/nevilcp/ML_Aero/results/NACA9235_Re200000_M0p3_polar.xml");
JavaFoil.Exit();
