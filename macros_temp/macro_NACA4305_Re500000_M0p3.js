// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, 101, 0.05, 0.0, 0.04, 3.0, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber(0.3);
Polar.Analyze(500000, 500000, 500000, -10.0, 10.0, 1.0, 1.0, 1.0, 0, false);
Polar.Save("/home/nevilcp/ML_Aero/results/NACA4305_Re500000_M0p3_polar.xml");
JavaFoil.Exit();
