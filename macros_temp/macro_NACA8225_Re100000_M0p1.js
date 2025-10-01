// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, 101, 0.25, 0.0, 0.08, 2.0, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber(0.1);
Polar.Analyze(100000, 100000, 100000, -10.0, 10.0, 1.0, 1.0, 1.0, 0, false);
Polar.Save("/home/nevilcp/ML_Aero/results/NACA8225_Re100000_M0p1_polar.xml");
JavaFoil.Exit();
