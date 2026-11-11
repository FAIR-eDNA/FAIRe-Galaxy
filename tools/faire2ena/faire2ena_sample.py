from typing import Dict, List, Tuple
from datetime import datetime
from argparse import ArgumentParser
import pandas as pd
import re

# mandatory fields according to the checklist
MANDATORY_FIELDS = [
    'project name',
    'collection date',
    'geographic location (latitude)',
    'geographic location (longitude)',
    'geographic location (country and/or sea)',
    'broad-scale environmental context',
    'local environmental context',
    'environmental medium',
    'depth'
]
    
# Mapping dictionary: required ENA fields, sensible OceanOmics defaults
DEFAULTS_DICT = {
    'env_local_scale' : 'marine pelagic zone [ENVO:00000208]',
    'minimumDepthInMeters' : '0' # most OceanOmics samples are surface
}

# Mapping dictionary: FAIRe field -> ENA field
FAIRE_TO_ENA_MAPPING = {
    'materialSampleID': 'source material identifiers',
    
    # Collection date and location (MANDATORY)
    'eventDate': 'collection date',
    'decimalLatitude': 'geographic location (latitude)',
    'decimalLongitude': 'geographic location (longitude)',
    'geo_loc_name': 'geographic location (region and locality)',
    
    # Environmental context (MANDATORY)
    'env_broad_scale': 'broad-scale environmental context',
    'env_local_scale': 'local environmental context',
    'env_medium': 'environmental medium',
    
    # Depth (MANDATORY for water samples)
    'minimumDepthInMeters': 'depth',  
    'maximumDepthInMeters': None,  # we generally treat minimum and maximum identically
    
    'samp_collect_device': 'sample collection device',
    'samp_collect_method': 'sample collection method',
    'samp_size': 'amount or size of sample collected',
    'samp_size_unit': None,  # Combined with samp_size
    'samp_store_temp': 'sample storage temperature',
    'samp_store_loc': 'sample storage location',
    'samp_store_dur': 'sample storage duration',
    'samp_category': 'control_sample',
    
    'size_frac_low': 'sizefraction lower threshold',
    'size_frac': 'sizefraction upper threshold',
    
    'temp': 'temperature',
    'salinity': 'salinity',
    'ph': 'ph',
    'tot_depth_water_col': 'total depth of water column',
    'elev': 'elevation',
    
    'diss_oxygen': 'dissolved oxygen',
    'nitrate': 'nitrate',
    'nitrite': 'nitrite',
    'diss_inorg_carb': 'dissolved inorganic carbon',
    'diss_inorg_nitro': 'dissolved inorganic nitrogen',
    'diss_org_carb': 'dissolved organic carbon',
    'diss_org_nitro': 'dissolved organic nitrogen',
    'tot_diss_nitro': 'total dissolved nitrogen',
    'tot_inorg_nitro': 'total inorganic nitrogen',
    'tot_nitro': 'total nitrogen concentration',
    'tot_part_carb': 'total particulate carbon',
    'tot_org_carb': 'total organic carbon',
    'tot_nitro_content': 'total nitrogen content',
    'part_org_carb': 'particulate organic carbon',
    'part_org_nitro': 'particulate organic nitrogen',
    'org_carb': 'organic carbon',
    'org_matter': 'organic matter',
    'org_nitro': 'organic nitrogen',
    
    'chlorophyll': 'chlorophyll',
    'light_intensity': 'light intensity',
    'suspend_part_matter': 'suspended particulate matter',
    'tidal_stage': 'tidal stage',
    'turbidity': 'turbidity',
    'water_current': 'water current',
    
    'samp_mat_process': 'sample material processing',
    'samp_vol_we_dna_ext': 'sample volume or weight for DNA extraction',
    'nucl_acid_ext': 'nucleic acid extraction',
    'nucl_acid_ext_kit': None,  # Can be combined with nucl_acid_ext
    
    'neg_cont_type': 'negative control type',
    'pos_cont_type': 'positive control type',
    
    # OceanOmics-specific fields - TODO; decide?
    'biological_rep': 'replicate_id',  # NOT a FAIRe term - an OceanOmics term
    'site_id': None,  # Not directly mapped to ENA
    'tube_id': None,  # Not directly mapped to ENA
}

ENA_TO_FAIRE_MAPPING = {value: key for key, value in FAIRE_TO_ENA_MAPPING.items()}

# some values have units we need to add. list them here
TAG_TO_UNIT = {
        'geographic location (longitude)' : 'DD',
        'geographic location (latitude)': 'DD',
        'depth' : 'm',
        'amount or size of sample collected': 'L'
}


def combine_value_with_unit(value: str, unit: str) -> str:
    """
    Combine a measurement value with its unit.
    """
    if pd.isna(value) or pd.isna(unit):
        return 'Unknown'
    if value and unit:
        return f"{value} {unit}"
    elif value:
        return f"{value}"
    return ""


def convert_faire_to_ena(faire_data: Dict[str, str], project_name: str) -> Dict[str, str]:
    """
    Convert FAIRe metadata dictionary to ENA format.
    
    Args:
        faire_data (dict): Dictionary with FAIRe metadata fields
        project_name (str): Project name (required by ENA if not in faire_data)
        
    Returns:
        dict: Dictionary with ENA field names and values
    """
    ena_data = {}
    
    ena_data['project name'] = project_name
    
    this_is_control = False
    if faire_data['samp_category'] != 'sample':
        this_is_control = True

    for faire_field, ena_field in FAIRE_TO_ENA_MAPPING.items():
        if ena_field and faire_field in faire_data:
            value = faire_data.get(faire_field, '')
            if this_is_control and pd.isna(value):
                ena_data[ena_field] = 'missing: control sample'
            elif value and not pd.isna(value):
                ena_data[ena_field] = value
    
    if ena_data['control_sample'] == 'sample':
        ena_data['control_sample'] = 'FALSE'
    else:
        ena_data['control_sample'] = 'TRUE'

    # Special handling for combined fields
    
    min_depth = faire_data.get('minimumDepthInMeters', '')
    max_depth = faire_data.get('maximumDepthInMeters', '')
    # OceanOmics usually sets these to the same
    if (min_depth or max_depth) and not pd.isna(min_depth):
        #ena_data['depth'] = parse_depth(min_depth, max_depth)
        ena_data['depth'] = min_depth

    
    samp_size = faire_data.get('samp_size', '')
    samp_size_unit = faire_data.get('samp_size_unit', '')
    if samp_size and not this_is_control:
        ena_data['amount or size of sample collected'] = combine_value_with_unit(
            samp_size, samp_size_unit
        )

    
    dna_vol = faire_data.get('samp_vol_we_dna_ext', '')
    dna_vol_unit = faire_data.get('samp_vol_we_dna_ext_unit', '')
    if dna_vol and not this_is_control and not pd.isna(dna_vol):
        ena_data['sample volume for weight for DNA extraction'] = combine_value_with_unit(
            dna_vol, dna_vol_unit
        )
    
    geo_loc_name = faire_data.get('geo_loc_name', '')
    if not pd.isna(geo_loc_name) and geo_loc_name and not this_is_control:
        # turn Indian Ocean: Rowley Shoals, Mermaid into Indian Ocean
        ena_data['geographic location (country and/or sea)'] = geo_loc_name.split(':')[0].strip()
    elif this_is_control:
        ena_data['geographic location (country and/or sea)'] = 'missing: control sample'
    
    nucl_ext = faire_data.get('nucl_acid_ext', '')
    nucl_ext_kit = faire_data.get('nucl_acid_ext_kit', '')
    if nucl_ext and nucl_ext_kit and not pd.isna(nucl_ext):
        ena_data['nucleic acid extraction'] = f"{nucl_ext} ({nucl_ext_kit})"
    elif nucl_ext and not pd.isna(nucl_ext):
        ena_data['nucleic acid extraction'] = nucl_ext
    
    if 'replicate_id' in ena_data and not this_is_control: 
        ena_data['replicate_id'] = str(int(ena_data['replicate_id']))
    
    unit_mappings = [
        ('diss_inorg_carb', 'diss_inorg_carb_unit', 'dissolved_inorganic_carbon'),
        ('diss_inorg_nitro', 'diss_inorg_nitro_unit', 'dissolved_inorganic_nitrogen'),
        ('diss_org_carb', 'diss_org_carb_unit', 'dissolved_organic_carbon'),
        ('diss_org_nitro', 'diss_org_nitro_unit', 'dissolved_organic_nitrogen'),
        ('diss_oxygen', 'diss_oxygen_unit', 'dissolved_oxygen'),
        ('nitrate', 'nitrate_unit', 'nitrate'),
        ('nitrite', 'nitrite_unit', 'nitrite'),
    ]
    
    for value_field, unit_field, ena_field in unit_mappings:
        value = faire_data.get(value_field, '')
        unit = faire_data.get(unit_field, '')
        #if pd.isna(value):
        #    ena_data[ena_field] = 'Unknown'
        if value and not pd.isna(value):
            ena_data[ena_field] = combine_value_with_unit(value, unit)
    
    return ena_data


def validate_mandatory_fields(ena_data: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate that all mandatory ENA fields are present.
    
    Args:
        ena_data (dict): Dictionary with ENA metadata
        
    Returns:
        tuple: (bool, list) - (is_valid, missing_fields)
    """
    missing = [field for field in MANDATORY_FIELDS if field not in ena_data or not ena_data[field]]
    return len(missing) == 0, missing

def validate_date(ena_data: Dict[str, str]) -> bool:
    """
    Validates whether a given date fits the ENA date regular expression.

    Args:
        ena_data (dict): Dictionary with ENA metadata
        
    Returns:
        bool - is_valid
    """
    # ew
    ena_pattern = r"(^[12][0-9]{3}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01])(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z?([+-][0-9]{1,2})?)?)?)?(/[0-9]{4}(-[0-9]{2}(-[0-9]{2}(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z?([+-][0-9]{1,2})?)?)?)?)?$)|(^not applicable$)|(^not collected$)|(^not provided$)|(^restricted access$)|(^missing: control sample$)|(^missing: sample group$)|(^missing: synthetic construct$)|(^missing: lab stock$)|(^missing: third party data$)|(^missing: data agreement established pre-2023$)|(^missing: endangered species$)|(^missing: human-identifiable$)|(^missing$)"

    # Check if it matches ENA pattern
    if re.match(ena_pattern, ena_data['collection date']):
        return True
    else:
        return False

def generate_ena_xml(ena_data: Dict[str, str], sample_alias: str, 
                     taxon_id: str = "32644", center_name: str = "YOUR_CENTER") -> str:
    """
    Generate ENA XML string from metadata dictionary.
    
    Args:
        ena_data (dict): Dictionary with ENA metadata
        sample_alias (str): Unique identifier for the sample
        taxon_id (str): NCBI Taxonomy ID (default: 32644 for unidentified)
        center_name (str): Your center/institution name
        
    Returns:
        str: XML string formatted for ENA submission
    """
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<SAMPLE_SET>')
    xml_parts.append(f'  <SAMPLE alias="{sample_alias}" center_name="{center_name}">')
    xml_parts.append('    <SAMPLE_NAME>')
    xml_parts.append(f'      <TAXON_ID>{taxon_id}</TAXON_ID>')
    xml_parts.append('    </SAMPLE_NAME>')
    xml_parts.append('    <SAMPLE_ATTRIBUTES>')
    
    for field_name, value in sorted(ena_data.items()):
        if value:
            if field_name not in MANDATORY_FIELDS and value == 'missing: control sample':
                # skip optional fields if we have no content
                # otherwise control samples get heaps content
                continue

            # Escape XML special characters
            value_escaped = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            xml_parts.append('      <SAMPLE_ATTRIBUTE>')
            xml_parts.append(f'        <TAG>{field_name}</TAG>')
            xml_parts.append(f'        <VALUE>{value_escaped}</VALUE>')
            if field_name in TAG_TO_UNIT:
                unit = TAG_TO_UNIT[field_name]
                xml_parts.append(f'        <UNITS>{unit}</UNITS>')
            xml_parts.append('      </SAMPLE_ATTRIBUTE>')
    
    xml_parts.append('       <SAMPLE_ATTRIBUTE>')
    xml_parts.append('         <TAG>ENA-CHECKLIST</TAG>')
    xml_parts.append('         <VALUE>ERC000024</VALUE>')
    xml_parts.append('       </SAMPLE_ATTRIBUTE>')
    xml_parts.append('    </SAMPLE_ATTRIBUTES>')
    xml_parts.append('  </SAMPLE>')
    xml_parts.append('</SAMPLE_SET>')
    
    return '\n'.join(xml_parts)


def process_faire_df(input_df: pd.DataFrame, output_file: str, project_name: str, 
        taxon_id: str, center_name: str):
    samples_xml = []
         
    list_of_dicts = input_df.to_dict(orient = 'records')

    for row in list_of_dicts:
        ena_data = convert_faire_to_ena(row, project_name)
        
        is_valid, missing = validate_mandatory_fields(ena_data)
        sample_name = row.get('samp_name', 'unknown')
        
        if not is_valid:
            for m in missing:
                ena_orig = ENA_TO_FAIRE_MAPPING[m]
                new_default = DEFAULTS_DICT[ena_orig]
                ena_data[m] = new_default
                print(f"WARNING: Sample name {sample_name} missing mandatory field '{m}', setting to default '{new_default}'")

        date_is_valid = validate_date(ena_data)
        if not date_is_valid:
            print(f"WARNING: Sample name {sample_name} has invalid date {ena_data['collection date']}. Replacing with 'not provided'.")
            ena_data['collection date'] = 'not provided'
        
        sample_xml = generate_ena_xml(
            ena_data, 
            sample_name,
            taxon_id,
            center_name
        )
        
        sample_lines = sample_xml.split('\n')[2:-1]  # Skip header and closing tag
        samples_xml.extend(sample_lines)
    
    # Write combined XML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<SAMPLE_SET>\n')
        f.write('\n'.join(samples_xml))
        f.write('\n</SAMPLE_SET>\n')
    
    print(f"Generated ENA XML with {len(samples_xml)} samples -> {output_file}")


if __name__ == "__main__":
    parser = ArgumentParser(prog = 'FAIRe2ENA', description = 'Writes a sample-level XML file for submission to ENA')

    parser.add_argument('-i', '--input_file', help='Path of the FAIRe-formatted Excel file', required = True)
    parser.add_argument('-c', '--center_name', help = 'Name of the sequencing centre for ENA submission', required = True)
    parser.add_argument('-o', '--output_file', help = 'Name of the output file to submit to ENA', required = True)

    args = parser.parse_args()

    df = pd.read_excel(args.input_file, sheet_name = 'sampleMetadata', skiprows = 2)

    project_df = pd.read_excel(args.input_file, sheet_name = 'projectMetadata')
    project_name = project_df.loc[project_df['term_name'] == 'project_id', 'project_level'].values[0]
    print(f'INFO: found project ID {project_name}')

    process_faire_df(df, args.output_file, project_name, taxon_id = '408172', center_name = args.center_name)
