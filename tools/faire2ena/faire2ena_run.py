from typing import Dict, List, Tuple
from datetime import datetime
from argparse import ArgumentParser
import pandas as pd
import xml.etree.ElementTree as ET
import re


def parse_ena_receipt(receipt_file: str) -> Dict[str, str]:
    """
    Parse ENA sample receipt XML to extract alias -> accession mapping.
    
    Args:
        receipt_file: Path to the ENA receipt XML file
        
    Returns:
        dict: Mapping of sample alias to ENA accession (ERS...)
    """
    tree = ET.parse(receipt_file)
    root = tree.getroot()
    
    alias_to_accession = {}
    
    for sample in root.findall('.//SAMPLE'):
        alias = sample.get('alias')
        accession = sample.get('accession')
        if alias and accession:
            alias_to_accession[alias] = accession
    
    print(f"INFO: Loaded {len(alias_to_accession)} sample accessions from receipt")
    return alias_to_accession


def generate_experiment_xml(run_data: Dict[str, str], sample_accession: str,
                            study_accession: str, experiment_alias: str,
                            center_name: str, instrument_model: str) -> str:
    """
    Generate ENA EXPERIMENT XML for a single run.
    
    Args:
        run_data: Dictionary with run metadata
        sample_accession: ENA sample accession (ERS...)
        study_accession: ENA study accession (PRJ...)
        experiment_alias: Unique alias for this experiment
        center_name: Sequencing center name
        instrument_model: Sequencing instrument model
        
    Returns:
        str: XML string for EXPERIMENT
    """
    xml_parts = []
    xml_parts.append(f'  <EXPERIMENT alias="{experiment_alias}" center_name="{center_name}">')
    xml_parts.append(f'    <TITLE>{experiment_alias}</TITLE>')
    xml_parts.append(f'    <STUDY_REF accession="{study_accession}"/>')
    xml_parts.append('    <DESIGN>')
    xml_parts.append('      <DESIGN_DESCRIPTION>eDNA metabarcoding</DESIGN_DESCRIPTION>')
    xml_parts.append(f'      <SAMPLE_DESCRIPTOR accession="{sample_accession}"/>')
    xml_parts.append('      <LIBRARY_DESCRIPTOR>')
    
    # Library name
    lib_id = run_data.get('lib_id', experiment_alias)
    xml_parts.append(f'        <LIBRARY_NAME>{lib_id}</LIBRARY_NAME>')
    
    # Library strategy - typically AMPLICON for eDNA
    xml_parts.append('        <LIBRARY_STRATEGY>AMPLICON</LIBRARY_STRATEGY>')
    xml_parts.append('        <LIBRARY_SOURCE>METAGENOMIC</LIBRARY_SOURCE>')
    xml_parts.append('        <LIBRARY_SELECTION>PCR</LIBRARY_SELECTION>')
    xml_parts.append('        <LIBRARY_LAYOUT>')
    xml_parts.append('          <PAIRED/>')
    xml_parts.append('        </LIBRARY_LAYOUT>')
    
    # Library construction protocol
    protocol_parts = []
    if 'lib_conc' in run_data and run_data['lib_conc'] and not pd.isna(run_data['lib_conc']):
        lib_conc = run_data['lib_conc']
        lib_conc_unit = run_data.get('lib_conc_unit', 'ng/uL')
        protocol_parts.append(f"Library concentration: {lib_conc} {lib_conc_unit}")
    
    if 'lib_conc_meth' in run_data and run_data['lib_conc_meth'] and not pd.isna(run_data['lib_conc_meth']):
        protocol_parts.append(f"Quantification method: {run_data['lib_conc_meth']}")
    
    if protocol_parts:
        protocol = '; '.join(protocol_parts)
        xml_parts.append(f'        <LIBRARY_CONSTRUCTION_PROTOCOL>{protocol}</LIBRARY_CONSTRUCTION_PROTOCOL>')
    
    xml_parts.append('      </LIBRARY_DESCRIPTOR>')
    xml_parts.append('    </DESIGN>')
    xml_parts.append('    <PLATFORM>')
    xml_parts.append('      <ILLUMINA>')
    xml_parts.append(f'        <INSTRUMENT_MODEL>{instrument_model}</INSTRUMENT_MODEL>')
    xml_parts.append('      </ILLUMINA>')
    xml_parts.append('    </PLATFORM>')
    xml_parts.append('  </EXPERIMENT>')
    
    return '\n'.join(xml_parts)


def generate_run_xml(run_data: Dict[str, str], experiment_alias: str,
                     run_alias: str, center_name: str) -> str:
    """
    Generate ENA RUN XML for a single run.
    
    Args:
        run_data: Dictionary with run metadata
        experiment_alias: Alias of the associated experiment
        run_alias: Unique alias for this run
        center_name: Sequencing center name
        
    Returns:
        str: XML string for RUN
    """
    xml_parts = []
    xml_parts.append(f'  <RUN alias="{run_alias}" center_name="{center_name}">')
    xml_parts.append(f'    <EXPERIMENT_REF refname="{experiment_alias}"/>')
    xml_parts.append('    <DATA_BLOCK>')
    xml_parts.append('      <FILES>')
    
    # Forward read
    filename1 = run_data.get('filename', '')
    checksum1 = run_data.get('checksum_filename', '')
    if filename1:
        xml_parts.append(f'        <FILE filename="{filename1}" filetype="fastq" ')
        xml_parts.append(f'              checksum_method="MD5" checksum="{checksum1}"/>')
    
    # Reverse read
    filename2 = run_data.get('filename2', '')
    checksum2 = run_data.get('checksum_filename2', '')
    if filename2:
        xml_parts.append(f'        <FILE filename="{filename2}" filetype="fastq" ')
        xml_parts.append(f'              checksum_method="MD5" checksum="{checksum2}"/>')
    
    xml_parts.append('      </FILES>')
    xml_parts.append('    </DATA_BLOCK>')
    xml_parts.append('  </RUN>')
    
    return '\n'.join(xml_parts)


def process_run_metadata(input_df: pd.DataFrame, receipt_file: str, 
                        study_accession: str, center_name: str,
                        experiment_output: str, run_output: str,
                        instrument_model: str = "Illumina NovaSeq 6000",
                        assay_filter: str = None):
    """
    Process run metadata and generate EXPERIMENT and RUN XML files.
    
    Args:
        input_df: DataFrame with run metadata
        receipt_file: Path to ENA sample receipt XML
        study_accession: ENA study accession (PRJ...)
        center_name: Sequencing center name
        experiment_output: Output file for EXPERIMENT XML
        run_output: Output file for RUN XML
        instrument_model: Sequencing instrument model
        assay_filter: Optional assay name to add as suffix to experiment/run names
    """
    # Parse the receipt to get sample accessions
    alias_to_accession = parse_ena_receipt(receipt_file)
    
    # Info message if assay suffix is being used
    if assay_filter:
        print(f"INFO: Adding assay suffix '_{assay_filter}' to all experiment and run names")
    
    experiment_xml_parts = []
    run_xml_parts = []
    
    skipped_samples = []
    
    for idx, row in input_df.iterrows():
        samp_name = row.get('samp_name', '')
        lib_id = row.get('lib_id', '')
        
        if pd.isna(samp_name) or not samp_name:
            continue
            
        # Check if we have a sample accession for this sample
        if samp_name not in alias_to_accession:
            skipped_samples.append(samp_name)
            continue
        
        sample_accession = alias_to_accession[samp_name]
        
        # Use lib_id as the experiment/run alias (or samp_name if lib_id is missing)
        if lib_id and not pd.isna(lib_id):
            experiment_alias = lib_id
        else:
            experiment_alias = samp_name
            
        # Add assay suffix if specified
        if assay_filter:
            experiment_alias = f"{experiment_alias}_{assay_filter}"
            
        run_alias = f"{experiment_alias}_run"
        
        # Convert row to dict for easier access
        run_data = row.to_dict()
        
        # Generate EXPERIMENT XML
        exp_xml = generate_experiment_xml(
            run_data, 
            sample_accession,
            study_accession,
            experiment_alias,
            center_name,
            instrument_model
        )
        experiment_xml_parts.append(exp_xml)
        
        # Generate RUN XML
        run_xml = generate_run_xml(
            run_data,
            experiment_alias,
            run_alias,
            center_name
        )
        run_xml_parts.append(run_xml)
    
    # Write EXPERIMENT XML
    with open(experiment_output, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<EXPERIMENT_SET>\n')
        f.write('\n'.join(experiment_xml_parts))
        f.write('\n</EXPERIMENT_SET>\n')
    
    print(f"INFO: Generated EXPERIMENT XML with {len(experiment_xml_parts)} experiments -> {experiment_output}")
    
    # Write RUN XML
    with open(run_output, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<RUN_SET>\n')
        f.write('\n'.join(run_xml_parts))
        f.write('\n</RUN_SET>\n')
    
    print(f"INFO: Generated RUN XML with {len(run_xml_parts)} runs -> {run_output}")
    
    if skipped_samples:
        print(f"WARNING: Skipped {len(skipped_samples)} samples without accessions:")
        for samp in skipped_samples[:10]:  # Show first 10
            print(f"  - {samp}")
        if len(skipped_samples) > 10:
            print(f"  ... and {len(skipped_samples) - 10} more")


if __name__ == "__main__":
    parser = ArgumentParser(
        prog='FAIRe2ENA-Run',
        description='Writes EXPERIMENT and RUN XML files for submission to ENA'
    )
    
    parser.add_argument('-i', '--input_file', 
                       help='Path of the FAIRe-formatted Excel file',
                       required=True)
    parser.add_argument('-r', '--receipt_file',
                       help='Path to ENA sample submission receipt XML',
                       required=True)
    parser.add_argument('-s', '--study_accession',
                       help='ENA study accession (e.g., PRJEB12345)',
                       required=True)
    parser.add_argument('-c', '--center_name',
                       help='Name of the sequencing centre for ENA submission',
                       required=True)
    parser.add_argument('-e', '--experiment_output',
                       help='Output file for EXPERIMENT XML',
                       default='ena_experiments.xml')
    parser.add_argument('-o', '--run_output',
                       help='Output file for RUN XML',
                       default='ena_runs.xml')
    parser.add_argument('-m', '--instrument_model',
                       help='Sequencing instrument model',
                       default='Illumina NovaSeq 6000')
    parser.add_argument('-a', '--assay',
                       help='Assay name to append to experiment/run names (e.g., 16S, COI, 18S)',
                       default=None)
    
    args = parser.parse_args()
    
    # Read the run metadata from the Excel file
    df = pd.read_excel(args.input_file, sheet_name='experimentRunMetadata', skiprows=2)
    
    process_run_metadata(
        df,
        args.receipt_file,
        args.study_accession,
        args.center_name,
        args.experiment_output,
        args.run_output,
        args.instrument_model,
        args.assay
    )
