This Trujillo_Gonzalez_2022__DATA_README.txt file was generated on 20-04-2022 by Alejandro Trujillo-Gonzalez


GENERAL INFORMATION

1. Title of Dataset: Data from: Detection of Khapra Beetle environmental DNA using portable technologies in Australian biosecurity.

2. Author Information
	Corresponding Investigator 
		Name: Dr Alejandro Trujillo-Gonzalez
		Institution: University of Canberra, Canberra, Australian Capital Territory
		Email: alejandro.Trujillogonzalez@canberra.edu.au

	Co-investigator 1
		Name: Dr David N. Thuo
		Institution: The Commonwealth Scientific and Industrial Research Organisation, Canberra, Australian Capital Territory

	Co-investigator 2
		Name: Dr Uday Divi
		Institution: Biosecurity Strategy and Reform Division, Department of Agriculture, Water, and the Environment, Canberra, Australian Capital Territory

	Co-investigator 3
		Name: Dr Kate Sparks
		Institution: Science and Surveillance Group, Biosecurity Plant Division, Department of Agriculture, Water and the Environment, Canberra, Australian Capital Territory

	Co-investigator 4
		Name: Dr Thomas Wallenius
		Institution: Science and Surveillance Group, Biosecurity Plant Division, Department of Agriculture, Water and the Environment, Canberra, Australian Capital Territory

	Co-investigator 4
		Name: Prof Dianne Gleeson
		Institution: University of Canberra, Canberra, Australian Capital Territory


3. Date of data collection: August and November 2020

4. Geographic location of data collection: Canberra, Australian Capital Territory, Australia

5. Funding sources that supported the collection of the data: Department of Agriculture, Water and the Environment, Award: 182020

6. Recommended citation for this dataset: RTrujillo-González, Alejandro et al. (2022), Detection of Khapra Beetle environmental DNA using portable technologies in Australian biosecurity, Dryad, Dataset, https://doi.org/10.5061/dryad.jwstqjq96set


DATA & FILE OVERVIEW

1. Description of dataset

These data contains amplification data for dust and airborne environmental DNA samples collected during Australian biosecurity responses for Khapra beetle in Australia by vacuuming. Samples were tested using probe-based species-specific assays optimised to detect Trogoderma granarium DNA traces in environmental matrices and one LAMP assay designed to confirm the identity of khapra beetle in fiend conditions. Environmental DNA amplified using benchtop and portable real time PCR technologies.

detailed location data has not been included in the dataset as it contains sensitive and potentially identifying information.
 


2. File List: 
	File 1 Name: Amplification_data_khapra_05012022_dryad.csv
	File 1 Description: Amplification data achieved using two probe-based species specific assays for khapra beetle in benchtop (ViiA7 Real-Time PCR system, Thermo Fisher Scientific) and portable (Franklin Real-time PCR Thermocycler, Biomeme).

	File 2 Name: Sample_metadata.csv
	File 2 Description: Sample metadata including collection location, method, extraction technique and date of collection.

METHODOLOGICAL INFORMATION

Environmental DNA sampling at confirmed T. granarium detection sites was subject to government approval and access, occurring where biosecurity response measures had already been initiated by DAWE under the Emergency Plant Pest Response Deed. As such, testing of eDNA collection methods and portable technologies was opportunistic, and subject to available timeframes within which approval was given to sample each location. Samples were collected from two separate ACT retail stores that had received and stored goods infested with khapra beetle in August (Tuggeranong, Canberra) and November (Fyshwick, Canberra) of 2020. 

Samples collected in this study were tested for the presence of T. granarium eDNA using two published probe-based assays and one LAMP assay . The Olson assay targeted a 248 bp fragment of the 16s gene region , while the Furui assay targeted an 83 bp fragment of the ND6 (NADH dehydrogenase VI region). The LAMP assay was designed to detect a 234 bp fragment in the 16S gene region of T. granarium and was tested against eDNA. 


Modified Olson assay
der16SF4	CTAAAATTGAAAATTTCTATACT
der16SR1	CTAGCCTGCTCCCTGATTGA		
P1		FAM- TGACTGTGCGAAGGTAGCAT-QSY		

Furui assay
Furui F		CAGCCTTATATGACTTCTCATACC
Furui R		GATTTCATGTTGGGAATGATG		
Furui P		FAM- GCAAATGGTGGCGAGTGTTGTC-QSY		

LAMP assay	
Khapra_F3	GGTAATTTAATCTTATAATCACAAGATGG
Khapra_B3	AACTGGAATGAATGGTTGGACGAA		
Khapra_FIP	TTGTTAGTATAGAAATTTTCAATTTTAGGATCATCTAATCATAAATCAATGTTTCA		
Khapra_BIP	TTTAACAATTAAAGAAATAATAAAACTCTTGATTACTGTCTCTTTTTTATTTTG		
Khapra_Floop	TTAATTTGGTTGGGGTGACTA		
Khapra_Bloop	CGTCTTTTAAAAAAATTTGAGCC		

Probe-based assay conditions

Each TaqMan assay was optimised for use in a ViiA™ 7 Real-Time PCR System (Applied Biosystems, Australia) and in a Franklin™ Real Time Thermocycler (Biomeme Inc., USA) to test eDNA. Each reaction in the ViiA™ 7 Real-Time PCR System consisted of 10 µL TaqMan Environmental Master Mix 2.0 (ThermoFisher), 1 µL of each of primer and probe (10 µM) for the Olson assay or 0.8 µL (10 µM) for the Furui assay, 5 µL of template, and PCR water for a total volume of 20 µL. Reactions in the Franklin™ Real Time thermocycler consisted of 10 µL of 2x LyoDNA 2.0 + IPC Master mix (Biomeme, Inc.), 1 µL of each of primer and probe (10 µM) for the Olson assay or 0.8 µL (10 µM) for the Furui assay, 5 µL of template and PCR water for a total volume of 20 µL (Supplementary 2). 

Cycling conditions differed between platforms. In the ViiA™ 7 Real-Time PCR System, conditions for the Olson assay were: 95 °C (10 min), followed by 50 cycles of 95 °C (20 s), 50 °C (1 min) and 72°C (30 s) ramping at 2.42 °C/s, followed by a final holding stage at 4 °C. Conditions for the Furui assay were: 95 °C (10 min), followed by 45 cycles of 95 °C (20 s) and 60 °C (20 s) ramping at 2.42 °C/s, followed by a final holding stage at 4 °C. In the Franklin™ Real Time Thermocycler, conditions for both assays were optimised for field-based operational use. Cycling conditions for the Olson assay were optimised as follows: 95 °C (2 min), followed by 50 cycles of 95 °C (10 s) and 50 °C (30 s). Conditions for the Furui assay were 95 °C (2 min), followed by 45 cycles of 95 °C (20 s) and 60 °C (10 s). Samples in both platforms were run in triplicate with positive and non-template controls. All positive controls in this study were genomic DNA extracted from confirmed T. granarium larvae or adults collected by biosecurity officers during each event. 

LAMP assay conditions

Reactions were undertaken in a handheld Genie III machine (OptiGene, UK) at the University of Canberra. Each reaction consisted of 14 µL Isothermal Master Mix Iso-001 (Geneworks, Australia), 10 µL of primer mix [14] and 1 µL of eDNA or DNA template for a total volume of 25 µL. Each run in the Genie III consisted of 6 technical replicates of the eDNA positive sample, one positive DNA controls and one non-template control. Isothermal amplifications conditions were 65 °C for 25 mins followed by a ramping step from 98 °C to 73 °C at 0.05 °C/s.

DATA-SPECIFIC INFORMATION FOR: Amplification_data_khapra_05012022_dryad

1. Number of variables: 8

2. Number of cases/rows: 766

3. Variable List: 
	SAMPLE ID: sample unique identifier
	Sample type: Differentiation between environmental samples and field controls; Dust sample/Field control
	Location: sample collection location; Tuggeranong/Fyshwick/Kambah/gDNA positive
	Cq: cycle threshold values of amplified qPCR technical replicates; no. cycles
	Assay: probe-based assay used to amplify the sample; FURUI/OLSON
	METHOD: sample collection method; Vacuumed sample/Airborne sample
	extraction: eDNA extraction method used to process the sample; Biomeme/Qiagen BT/EtoHQiagen BT
	machine: thermocycler used to amplify the sample; Franklin/ViiA7

4. Missing data codes: 
	None

5. Abbreviations used: 
	Undetermined; amplification was not detected

6. Other relevant information: 
	The LAMP assay failed to detect khapra beetle traces in environmental matrices and was excluded from further testing.


DATA-SPECIFIC INFORMATION FOR: Sample_metadata.csv

1. Number of variables: 6

2. Number of cases/rows: 90

3. Variable List: 
	SAMPLE ID: sample unique identifier
	Location: sample collection location; Tuggeranong/Fyshwick/Kambah/CSIRO Collection
	Sample type: Differentiation between environmental samples, field controls, eDNA positive samples and specimens for genomic DNA controls; Dust sample/Airborne sample/Field control/eDNA Positive control/Specimen/Infested box inside freezer
	collection method: sample collection method;Vaccumed sample-DAWE dust buster/Vaccumed sample-Sartorius Cellulose nitrate 1.2 um/Specimen larvae/bug/Vaccumed sample-DAWE
	Extraction technique: eDNA extraction method used to process the sample; Dneasy blood and tissue kit/Biomeme M1 sample prep-High DNA/Stored in 100% ethanol. Dneasy blood and tissue kit
	Date: sample collection date
	
4. Missing data codes: 
	None

5. Abbreviations used: 
	Not applicable 

6. Other relevant information: 
	

