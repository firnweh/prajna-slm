"""
Official NEET & JEE syllabus structured as subject > chapter > topics.
Used for lesson planning and coverage analysis.
"""

NEET_SYLLABUS = {
    "Physics": {
        "Physical World And Measurement": [
            "Physics scope and excitement", "Nature of physical laws",
            "Units of measurement", "Dimensional analysis", "Errors in measurement",
        ],
        "Kinematics": [
            "Frame of reference", "Motion in a straight line",
            "Uniform and non-uniform motion", "Uniformly accelerated motion",
            "Scalar and vector quantities", "Motion in a plane",
            "Projectile motion", "Uniform circular motion",
        ],
        "Laws Of Motion": [
            "Newton's first law", "Momentum", "Newton's second law",
            "Newton's third law", "Impulse", "Law of conservation of momentum",
            "Friction", "Circular motion and centripetal force",
        ],
        "Work Energy And Power": [
            "Work done by constant and variable forces", "Kinetic energy",
            "Work-energy theorem", "Potential energy", "Conservation of energy",
            "Power", "Collisions elastic and inelastic",
        ],
        "Rotational Motion": [
            "Centre of mass", "Moment of inertia", "Radius of gyration",
            "Torque", "Angular momentum", "Conservation of angular momentum",
            "Rolling motion",
        ],
        "Gravitation": [
            "Universal law of gravitation", "Acceleration due to gravity",
            "Gravitational potential energy", "Escape velocity",
            "Orbital velocity", "Kepler's laws", "Geostationary satellites",
        ],
        "Properties Of Solids And Liquids": [
            "Elastic behaviour", "Stress strain curve", "Young's modulus",
            "Bulk modulus", "Shear modulus", "Viscosity", "Stokes law",
            "Surface tension", "Bernoulli's theorem", "Pascal's law",
        ],
        "Thermodynamics": [
            "Thermal equilibrium", "Zeroth law", "Heat and temperature",
            "Specific heat capacity", "Calorimetry", "Latent heat",
            "Heat transfer conduction convection radiation",
            "Newton's law of cooling", "Thermal expansion",
        ],
        "Kinetic Theory Of Gases": [
            "Equation of state of perfect gas", "Kinetic theory assumptions",
            "RMS speed", "Degrees of freedom", "Law of equipartition of energy",
            "Mean free path",
        ],
        "Thermodynamics Laws": [
            "First law of thermodynamics", "Second law of thermodynamics",
            "Carnot engine", "Isothermal and adiabatic processes",
            "Reversible and irreversible processes",
        ],
        "Oscillations And Waves": [
            "Simple harmonic motion", "SHM equations",
            "Spring mass system", "Simple pendulum", "Damped oscillations",
            "Forced oscillations", "Resonance",
            "Wave motion", "Transverse and longitudinal waves",
            "Speed of sound", "Doppler effect", "Superposition of waves",
            "Standing waves", "Beats",
        ],
        "Electrostatics": [
            "Electric charges", "Coulomb's law", "Electric field",
            "Electric dipole", "Gauss's theorem", "Electric potential",
            "Capacitors", "Dielectrics",
        ],
        "Current Electricity": [
            "Ohm's law", "Drift velocity", "Resistivity",
            "Kirchhoff's laws", "Wheatstone bridge", "Metre bridge",
            "Potentiometer", "Electrical energy and power",
        ],
        "Magnetic Effects Of Current": [
            "Biot-Savart law", "Ampere's law", "Solenoid",
            "Force on moving charge in magnetic field",
            "Force between two parallel currents", "Torque on current loop",
            "Moving coil galvanometer",
        ],
        "Electromagnetic Induction": [
            "Faraday's law", "Lenz's law", "Eddy currents",
            "Self and mutual inductance", "AC generator",
        ],
        "Alternating Current": [
            "AC voltage", "LCR circuit", "Resonance",
            "Power in AC circuits", "Transformer",
        ],
        "Electromagnetic Waves": [
            "Displacement current", "Electromagnetic spectrum",
            "Properties of EM waves",
        ],
        "Optics": [
            "Reflection and refraction", "Total internal reflection",
            "Lenses thin lens formula", "Magnification", "Microscope",
            "Telescope", "Wave optics", "Interference", "Diffraction",
            "Polarisation", "Young's double slit experiment",
        ],
        "Dual Nature Of Matter": [
            "Photoelectric effect", "Einstein's equation",
            "De Broglie wavelength", "Davisson-Germer experiment",
        ],
        "Atoms And Nuclei": [
            "Rutherford's model", "Bohr model", "Hydrogen spectrum",
            "Radioactivity", "Nuclear fission and fusion",
            "Mass energy relation", "Mass defect and binding energy",
        ],
        "Electronic Devices": [
            "Semiconductors", "p-n junction diode", "LED", "Photodiode",
            "Zener diode", "Transistors", "Logic gates",
        ],
    },
    "Chemistry": {
        "Some Basic Concepts Of Chemistry": [
            "Mole concept", "Stoichiometry", "Atomic and molecular masses",
            "Percentage composition", "Empirical and molecular formula",
            "Chemical reactions and equations",
        ],
        "Structure Of Atom": [
            "Bohr's model", "Quantum numbers", "Electronic configuration",
            "Shapes of orbitals", "Aufbau principle", "Hund's rule",
            "Pauli exclusion principle", "Photoelectric effect",
        ],
        "Classification Of Elements": [
            "Modern periodic table", "Periodic trends",
            "Ionization enthalpy", "Electron gain enthalpy",
            "Electronegativity", "Atomic radii",
        ],
        "Chemical Bonding": [
            "Ionic bond", "Covalent bond", "VSEPR theory",
            "Hybridization", "Molecular orbital theory",
            "Hydrogen bonding", "Bond parameters",
        ],
        "States Of Matter": [
            "Gas laws", "Ideal gas equation", "Kinetic molecular theory",
            "Real gases", "Van der Waals equation", "Liquefaction",
        ],
        "Chemical Thermodynamics": [
            "Enthalpy", "Hess's law", "Entropy", "Gibbs free energy",
            "Spontaneity", "Internal energy", "Bond enthalpy",
        ],
        "Equilibrium": [
            "Chemical equilibrium", "Le Chatelier's principle",
            "Ionic equilibrium", "Acids and bases", "pH scale",
            "Buffer solutions", "Solubility product", "Common ion effect",
        ],
        "Redox Reactions": [
            "Oxidation and reduction", "Balancing redox reactions",
            "Oxidation number", "Electrode potential",
        ],
        "Hydrogen": [
            "Position in periodic table", "Isotopes",
            "Properties and uses", "Water structure",
        ],
        "S Block Elements": [
            "Alkali metals", "Alkaline earth metals",
            "Biological importance", "Anomalous properties of Li and Be",
        ],
        "P Block Elements": [
            "Group 13 to 18 elements", "Boron family", "Carbon family",
            "Nitrogen family", "Oxygen family", "Halogen family",
            "Noble gases", "Interhalogen compounds",
        ],
        "Organic Chemistry Basic Principles": [
            "IUPAC nomenclature", "Isomerism", "Electronic effects",
            "Inductive effect", "Resonance", "Hyperconjugation",
            "Reaction intermediates", "Types of organic reactions",
        ],
        "Hydrocarbons": [
            "Alkanes", "Alkenes", "Alkynes", "Aromatic hydrocarbons",
            "Benzene structure", "Electrophilic substitution",
        ],
        "Environmental Chemistry": [
            "Air pollution", "Water pollution", "Ozone depletion",
            "Green chemistry", "Greenhouse effect",
        ],
        "Solid State": [
            "Crystal lattices", "Unit cell", "Packing efficiency",
            "Defects in solids", "Electrical and magnetic properties",
        ],
        "Solutions": [
            "Types of solutions", "Concentration terms",
            "Colligative properties", "Raoult's law",
            "Osmotic pressure", "Van't Hoff factor",
        ],
        "Electrochemistry": [
            "Electrolytic and galvanic cells", "Nernst equation",
            "Conductance", "Kohlrausch's law", "Faraday's laws",
            "Batteries and corrosion",
        ],
        "Chemical Kinetics": [
            "Rate of reaction", "Rate law", "Order of reaction",
            "Molecularity", "Activation energy", "Arrhenius equation",
            "Collision theory",
        ],
        "Surface Chemistry": [
            "Adsorption", "Catalysis", "Colloids",
            "Emulsions", "Tyndall effect",
        ],
        "D And F Block Elements": [
            "Transition elements", "General properties",
            "Lanthanoids and actinoids", "KMnO4 and K2Cr2O7",
            "Magnetic properties",
        ],
        "Coordination Compounds": [
            "Werner's theory", "IUPAC nomenclature",
            "Isomerism in coordination compounds",
            "Crystal field theory", "Bonding in complexes",
        ],
        "Haloalkanes And Haloarenes": [
            "SN1 and SN2 reactions", "Elimination reactions",
            "Grignard reagent", "Preparation and properties",
        ],
        "Alcohols Phenols Ethers": [
            "Preparation and properties of alcohols",
            "Phenol acidity", "Ethers Williamson synthesis",
        ],
        "Aldehydes Ketones Carboxylic Acids": [
            "Nucleophilic addition", "Aldol condensation",
            "Cannizzaro reaction", "Acidity of carboxylic acids",
        ],
        "Amines": [
            "Classification", "Basicity of amines",
            "Preparation", "Diazonium salts",
        ],
        "Biomolecules": [
            "Carbohydrates", "Proteins", "Nucleic acids",
            "Vitamins", "Enzymes", "Hormones",
        ],
        "Polymers": [
            "Types of polymerization", "Natural and synthetic polymers",
            "Rubber", "Biodegradable polymers",
        ],
        "Chemistry In Everyday Life": [
            "Drugs and medicines", "Food chemistry",
            "Cleansing agents", "Chemicals in food",
        ],
    },
    "Biology": {
        "Diversity In Living World": [
            "Biological classification", "Taxonomy", "Five kingdom classification",
            "Plant kingdom", "Animal kingdom", "Viruses and viroids",
        ],
        "Structural Organisation In Plants And Animals": [
            "Morphology of flowering plants", "Anatomy of flowering plants",
            "Structural organisation in animals", "Animal tissues",
        ],
        "Cell Structure And Function": [
            "Cell theory", "Prokaryotic and eukaryotic cells",
            "Cell organelles", "Cell membrane", "Cell division mitosis meiosis",
            "Cell cycle",
        ],
        "Plant Physiology": [
            "Transport in plants", "Mineral nutrition",
            "Photosynthesis", "Respiration in plants",
            "Plant growth and development", "Transpiration",
        ],
        "Human Physiology": [
            "Digestion and absorption", "Breathing and exchange of gases",
            "Body fluids and circulation", "Excretory products",
            "Locomotion and movement", "Neural control",
            "Chemical coordination and integration", "Endocrine system",
        ],
        "Reproduction": [
            "Reproduction in organisms", "Sexual reproduction in flowering plants",
            "Human reproduction", "Reproductive health",
            "Pollination", "Fertilization",
        ],
        "Genetics And Evolution": [
            "Principles of inheritance", "Mendel's laws",
            "Chromosomal theory", "Sex determination",
            "Mutation", "Molecular basis of inheritance",
            "DNA replication", "Transcription", "Translation",
            "Gene expression regulation", "Human genome project",
            "Evolution", "Hardy-Weinberg principle",
        ],
        "Biology And Human Welfare": [
            "Health and disease", "Immunity",
            "AIDS cancer", "Drugs and alcohol abuse",
            "Microbes in human welfare", "Biocontrol agents",
        ],
        "Biotechnology": [
            "Principles of biotechnology", "Recombinant DNA technology",
            "PCR", "Gel electrophoresis", "DNA fingerprinting",
            "Biotechnology applications", "GM organisms", "Gene therapy",
        ],
        "Ecology And Environment": [
            "Organisms and populations", "Ecosystem",
            "Biodiversity", "Environmental issues",
            "Ecological succession", "Nutrient cycling",
            "Ecological pyramids", "Wildlife conservation",
        ],
    },
}


JEE_SYLLABUS = {
    "Physics": {
        "Mechanics": [
            "Kinematics", "Newton's laws of motion", "Friction",
            "Work energy power", "Centre of mass", "Momentum conservation",
            "Rotational mechanics", "Gravitation",
            "Simple harmonic motion", "Fluid mechanics",
        ],
        "Waves And Thermodynamics": [
            "Wave motion", "String waves", "Sound waves",
            "Doppler effect", "Thermal expansion", "Calorimetry",
            "KTG and thermodynamics", "Heat transfer",
        ],
        "Electromagnetism": [
            "Electrostatics", "Capacitance", "Current electricity",
            "Magnetic effect of current", "Magnetism",
            "Electromagnetic induction", "Alternating current",
            "Electromagnetic waves",
        ],
        "Optics": [
            "Geometrical optics", "Reflection", "Refraction",
            "Wave optics", "Interference", "Diffraction",
            "Polarization",
        ],
        "Modern Physics": [
            "Photoelectric effect", "Bohr model", "X-rays",
            "Nuclear physics", "Radioactivity",
            "Semiconductors", "Logic gates",
        ],
    },
    "Chemistry": {
        "Physical Chemistry": [
            "Mole concept", "Atomic structure", "Chemical bonding",
            "Gaseous state", "Chemical thermodynamics",
            "Chemical equilibrium", "Ionic equilibrium",
            "Chemical kinetics", "Electrochemistry",
            "Solutions and colligative properties", "Surface chemistry",
            "Solid state",
        ],
        "Inorganic Chemistry": [
            "Periodic table and periodicity", "s-block elements",
            "p-block elements", "d and f block elements",
            "Coordination compounds", "Metallurgy",
            "Qualitative analysis", "Hydrogen and its compounds",
        ],
        "Organic Chemistry": [
            "General organic chemistry", "Hydrocarbons",
            "Alkyl halides", "Alcohols phenols ethers",
            "Aldehydes ketones", "Carboxylic acids",
            "Amines", "Biomolecules", "Polymers",
            "Environmental chemistry", "Chemistry in everyday life",
        ],
    },
    "Mathematics": {
        "Algebra": [
            "Quadratic equations", "Complex numbers",
            "Sequences and series", "Permutations and combinations",
            "Binomial theorem", "Matrices and determinants",
            "Mathematical induction", "Sets and relations",
        ],
        "Trigonometry": [
            "Trigonometric functions", "Trigonometric equations",
            "Inverse trigonometric functions",
            "Properties of triangles",
        ],
        "Coordinate Geometry": [
            "Straight lines", "Circles", "Parabola",
            "Ellipse", "Hyperbola",
        ],
        "Calculus": [
            "Limits", "Continuity and differentiability",
            "Differentiation", "Application of derivatives",
            "Indefinite integrals", "Definite integrals",
            "Area under curves", "Differential equations",
        ],
        "Vectors And 3D": [
            "Vectors", "3D geometry", "Plane in 3D",
        ],
        "Probability And Statistics": [
            "Probability", "Conditional probability",
            "Bayes theorem", "Statistics", "Mean median mode",
            "Random variables", "Probability distributions",
        ],
    },
}
