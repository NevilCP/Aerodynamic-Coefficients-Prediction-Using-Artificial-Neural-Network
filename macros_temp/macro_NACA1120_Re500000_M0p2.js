// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, 101, 0.2, 0.0, 0.01, 1.0, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber(0.2);
Polar.Analyze(500000, 500000, 500000, -10.0, 10.0, 1.0, 1.0, 1.0, 0, false);
Polar.Save("/home/nevilcp/ML_Aero/results/NACA1120_Re500000_M0p2_polar.xml");
JavaFoil.Exit();
