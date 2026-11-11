Processed 12S fish eDNA sequences and visual census data

Data collected and processed by Laetitia Mathon, Virginie Marques, David Mouillot, Camille Albouy, Marco Andrello, Florian Baletaud, Giomar H. Borrero-Pérez, Tony Dejean, Graham J. Edgar, Jonathan Grondin, Pierre-Edouard Guerin, Régis Hocdé, Jean-Baptiste Juhel, Kadarusman, Eva Maire, Matthew McLean, Andrea Polanco F., Laurent Pouyaud, Rick D. Stuart-Smith, Hagi Yulia Sugeha, Alice Valentini, Laurent Vigliola, Indra B Vimono, Loïc Pellissier, Stéphanie Manel

Contact : Laetitia Mathon, laetitia.mathon@gmail.com, CEFE Montpellier, France

######################################################################################################################

This dataset contains fish eDNA sequences from the 12S mitochondrial gene. eDNA has been collected in 100 stations, 25 sites, in 5 tropical marine regions. Data collection was performed between 2017 and 2020.

Raw sequences have been processed through a bioinformatic pipeline, merged, demultiplexed, dereplicated, clustered as OTUs (operational taxonomic units) and assigned to a taxa.


The codes to analyse the data can be found at : https://github.com/virginiemarques/Global_eDNA.
The data are used to study the patterns of tropical fish distributions across spatial scales, using two different methodologies, eDNA and visual census. 

######################################################################################################################

- metadata/Metadata_eDNA_global_V6 a metadata file with all information regarding eDNA sampling. For each filter, we specify the sample code, date, station, site, province, country, project, sample type, volume, depth of sampling, habitat and coordinates.

The data folder contains the eDNA data.

- data/swarm/eparses/Eparses_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples collected in the Eparses region.
- data/swarm/eparses/Eparses_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples collected in the Eparses region.
- data/swarm/eparses/Blank_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the blanks (empty wells in the sequencing plate).
- data/swarm/eparses/Blank_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the blanks (empty wells in the sequencing plate).
- data/swarm/eparses/Other_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in samples belonging to other projects (other projects sequenced in the same batch as Eparses samples).
- data/swarm/eparses/Other_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in samples belonging to other projects (other projects sequenced in the same batch as Eparses samples).
- data/swarm/eparses/metadata/all_samples.csv : sequencing information for each sample relative to the Eparse project (the plate position, the run, the marker and the project). This file is used for the cleaning of sequencing errors.


- data/swarm/fakarava/Fakarava_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples collected in the Fakarava region.
- data/swarm/fakarava/Fakarava_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples collected in the Fakarava region.
- data/swarm/fakarava/Malpelo_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples collected in the Malpelo region.
- data/swarm/fakarava/Malpelo_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples collected in the Malpelo region.
- data/swarm/fakarava/Other_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in samples belonging to other projects (other projects sequenced in the same batch as Fakarava/Malpelo samples).
- data/swarm/fakarava/Other_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in samples belonging to other projects (other projects sequenced in the same batch as Fakarava/Malpelo samples).
- data/swarm/fakarava/metadata/all_samples.csv : sequencing information for each sample relative to the Fakarava/Malpelo project (the plate position, the run, the marker and the project). This file is used for the cleaning of sequencing errors.


- data/swarm/guadeloupe/Guadeloupe_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples collected in the Guadeloupe region.
- data/swarm/guadeloupe/Guadeloupe_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples collected in the Guadeloupe region.
- data/swarm/guadeloupe/Other_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in samples belonging to other projects (other projects sequenced in the same batch as Guadeloupe samples).
- data/swarm/guadeloupe/Other_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in samples belonging to other projects (other projects sequenced in the same batch as Guadeloupe samples).
- data/swarm/guadeloupe/metadata/all_samples.csv : sequencing information for each sample relative to the Guadeloupe project (the plate position, the run, the marker and the project). This file is used for the cleaning of sequencing errors.


- data/swarm/lengguru/Lengguru_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples collected in the Lengguru region.
- data/swarm/lengguru/Lengguru_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples collected in the Lengguru region.
- data/swarm/lengguru/Other_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in samples belonging to other projects (other projects sequenced in the same batch as Lengguru samples).
- data/swarm/lengguru/Other_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in samples belonging to other projects (other projects sequenced in the same batch as Lengguru samples).
- data/swarm/lengguru/metadata/all_samples.csv : sequencing information for each sample relative to the Lengguru project (the plate position, the run, the marker and the project). This file is used for the cleaning of sequencing errors.


- data/swarm/providencia/providencia_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples collected in the providencia region.
- data/swarm/providencia/providencia_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples collected in the providencia region.
- data/swarm/providencia/santamarta_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples belonging to the santamarta projects sequenced in the same batch as providencia samples.
- data/swarm/providencia/santamarta_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples belonging to the santamarta projects sequenced in the same batch as providencia samples.
- data/swarm/providencia/metadata/all_samples.csv : sequencing information for each sample relative to the providencia project (the plate position, the run, the marker and the project). This file is used for the cleaning of sequencing errors.


- data/swarm/santamarta/providencia_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples detected in the samples belonging to the providencia projects sequenced in the same batch as santamarta samples.
- data/swarm/santamarta/providencia_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) detected in the samples detected in the samples belonging to the providencia projects sequenced in the same batch as santamarta samples.
- data/swarm/santamarta/santamarta_teleo_ecotag_ncbi_motu.csv : information for the taxonomic assignment of each MOTU (best match, identity, family, genus, species, order) detected in the samples collected in the santamarta region.
- data/swarm/santamarta/santamarta_teleo_table_motu.csv : information for the detection of each MOTU (name of the amplicon, length of the sequence, total number of reads, number of reads in each sample) collected in the santamarta region.
- data/swarm/santamarta/metadata/all_samples.csv : sequencing information for each sample relative to the santamarta project (the plate position, the run, the marker and the project). This file is used for the cleaning of sequencing errors.
