// JavaFoil auto-generated macro
Options.Country(1);
Geometry.CreateAirfoil(0, 101, 0.15, 0.0, 0.02, 4.0, 0.0, 0.0, 0.0, 0.0, 1);
Options.MachNumber(0.1);
Polar.Analyze(500000, 500000, 500000, -10.0, 10.0, 1.0, 1.0, 1.0, 0, false);
Polar.Save("/home/nevilcp/ML_Aero/results/NACA2415_Re500000_M0p1_polar.xml");
JavaFoil.Exit();
