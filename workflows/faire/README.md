# FAIRe workflows

Three Galaxy workflows that chain the FAIRe tools in this repository, in the order a lab uses them.
Each folder holds the workflow to import (`.ga`), its source in Galaxy's YAML format
(`.gxwf.yml`), a test (`-tests.yml`) and its test data. All three tests pass in Galaxy 25.0
(5 November 2026).

| Workflow | Inputs | Steps | Outputs |
|---|---|---|---|
| `faire-propose-mapping`: FAIRe mapper: propose a mapping | your sample table; the methods as text | profile columns; propose mapping; find primers | column profile; mapping report; crosswalk to review; mandatory terms not covered; things to decide; primer candidates |
| `faire-write-workbook`: FAIRe mapper: write and check a FAIRe workbook | the sample table; the reviewed crosswalk; values for the whole project (optional); an OTU or ASV table; project ID; assay name | apply mapping; FAIRe-fier | FAIRe workbook; apply mapping log; FAIRe-fier issues and summary |
| `faire-submission-tables`: FAIRe: check a workbook and make submission tables | a FAIRe workbook; ENA centre name | FAIRe-fier; FAIRe2NCBI BioSample; FAIRe2NCBI SRA; FAIRe2ENA samples; FAIRe2QIIME | FAIRe-fier issues and summary; NCBI BioSample and SRA tables; ENA SAMPLE and SUBMISSION XML; QIIME 2 metadata and manifests |

Between the first two, review the crosswalk (the guide in each mapper tool's help says how). After
the third, submit the samples to ENA and run *FAIRe2ENA: experiments and runs* with the receipt.
Nothing is submitted by these workflows.

For library tables, a raw and a final OTU table, or several assays, run *apply mapping* on its own:
the workflow keeps to the common case of one assay and one OTU table.

The steps name the tools by their bare IDs (`faire_mapper_apply`), as on a Galaxy with these tool
folders installed locally. Once the tools are on the ToolShed, update the IDs to the ToolShed ones
(for example by opening each workflow in Galaxy's editor and saving it), and rerun the tests.

To test (planemo, with the tool folders loaded as extra tools):

```bash
planemo test --galaxy_branch release_25.0 $(for t in tools/*/; do echo --extra_tools $t; done) \
    workflows/faire/*/*.ga
```

To edit, change the `.gxwf.yml` file and convert it: `gxwf-to-native NAME.gxwf.yml NAME.ga`
(from the gxformat2 package).
