# Tests of which names edna2obis: match taxa changed (changed_names() in tools/edna2obis/edna2obis_galaxy.py,
# run here through its 'changes' mode, as the app runs it), the app's join of that table to the mapping
# table (R/taxa_review.R), and the copy of the mapping table with a person's choices. The tables follow
# the columns and values edna2obis writes (WoRMS_v3_matching.py and GBIF_matching.py); the names are
# real, the IDs made up.
#   Rscript tests/test_taxa_review.R      (from the shiny folder; FAIRE_PYTHON to choose the Python)

suppressMessages(library(shiny))
source("R/helpers.R")
source("R/taxa_review.R")
py <- Sys.getenv("FAIRE_PYTHON", "python3")
# the changed names table for a mapping table, from the Galaxy tool's own code, joined as the app does
changes_of <- function(map) {
  mp <- tempfile(fileext = ".tsv"); out <- tempfile(fileext = ".tsv")
  write_mapping(map, mp)
  system2(py, c("../tools/edna2obis/edna2obis_galaxy.py", "changes", "--mapping", mp, "--changes_out", out), stdout = FALSE)
  taxa_changes(map, read_tsv(out))
}
fails <- 0
expect <- function(ok, what) { cat(if (isTRUE(ok)) "PASS" else "FAIL", what, "\n"); if (!isTRUE(ok)) fails <<- fails + 1 }

cols <- c("verbatimIdentification", "assay_name", "cleanedTaxonomy", "selected_match", "ambiguous", "replaced_unaccepted",
          "unaccepted_match", "ranks_matched", "ranks_provided", "assignment_score", "environment", "scientificName",
          "taxonRank", "scientificNameID", "higherClassification", "kingdom", "phylum", "class", "order", "family", "genus",
          "match_type_debug", "nameAccordingTo")
row <- function(v, cleaned, sel, name, rank, k = "", p = "", c = "", g = "", amb = "False", repl = "False", unacc = "False",
                type = paste0("Success_Batch_", name), id = "urn:lsid:marinespecies.org:taxname:1") {
  x <- setNames(as.list(rep("", length(cols))), cols)
  x[c("verbatimIdentification", "assay_name", "cleanedTaxonomy", "selected_match", "ambiguous", "replaced_unaccepted",
      "unaccepted_match", "scientificName", "taxonRank", "scientificNameID", "kingdom", "phylum", "class", "genus",
      "match_type_debug", "nameAccordingTo")] <-
    list(v, "COI", cleaned, sel, amb, repl, unacc, name, rank, id, k, p, c, g, type, "WoRMS")
  as.data.frame(x, stringsAsFactors = FALSE, check.names = FALSE)
}
worms <- rbind(
  # matched as given (after tidying: '_' to a space): not listed
  row("Annelida;Polychaeta;Alitta;Alitta_succinea", "Annelida;Polychaeta;Alitta;Alitta succinea", "True", "Alitta succinea",
      "Species", "Animalia", "Annelida", "Polychaeta", "Alitta"),
  # a synonym: Nereis virens is now Alitta virens; the unaccepted row is shown for transparency
  row("Annelida;Polychaeta;Nereis;Nereis virens", "Annelida;Polychaeta;Nereis;Nereis virens", "True", "Alitta virens",
      "Species", "Animalia", "Annelida", "Polychaeta", "Alitta", amb = "True", repl = "True", type = "Success_Batch_Nereis virens"),
  row("Annelida;Polychaeta;Nereis;Nereis virens", "Annelida;Polychaeta;Nereis;Nereis virens", "False", "Nereis virens",
      "Species", "Animalia", "Annelida", "Polychaeta", "Nereis", amb = "True", unacc = "True", type = "Success_Batch_Nereis virens"),
  # the species was not found, so the genus is used
  row("Arthropoda;Hexanauplia;Acartia;Acartia_sp_X1", "Arthropoda;Hexanauplia;Acartia;Acartia X", "True", "Acartia",
      "Genus", "Animalia", "Arthropoda", "Hexanauplia", "Acartia", type = "Success_Batch_Acartia"),
  # a namesake: Ochrophyta;Bacillariophyceae;Navicula matched to a namesake in another kingdom, and the diatom offered
  row("Eukaryota;Ochrophyta;Bacillariophyceae;Navicula", "Ochrophyta;Bacillariophyceae;Navicula", "True", "Navicula",
      "Genus", "Animalia", "Mollusca", "Gastropoda", "Navicula", amb = "True", id = "urn:lsid:marinespecies.org:taxname:2"),
  row("Eukaryota;Ochrophyta;Bacillariophyceae;Navicula", "Ochrophyta;Bacillariophyceae;Navicula", "False", "Navicula",
      "Genus", "Chromista", "Ochrophyta", "Bacillariophyceae", "Navicula", amb = "True", id = "urn:lsid:marinespecies.org:taxname:3"),
  # nothing found
  row("Unknown;uncultured_eukaryote", "Unknown;uncultured eukaryote", "True", "incertae sedis", "",
      type = "Failed_All_Stages_NoMatch", id = "urn:lsid:marinespecies.org:taxname:12"),
  # matched at the phylum, high up the string: a higher rank, not a disagreement
  row("Eukaryota;Arthropoda;Insecta;Diptera;Chironomidae;Chironomus;Chironomus_sp", "Arthropoda;Insecta;Diptera;Chironomidae;Chironomus",
      "True", "Arthropoda", "Phylum", "Animalia", "Arthropoda", type = "Success_Batch_Arthropoda")
)
r <- changes_of(worms)
kinds <- setNames(vapply(r$changes, `[[`, "", "kind"), vapply(r$changes, `[[`, "", "lowest"))
expect(r$n_names == 6, sprintf("six names in the table (%d)", r$n_names))
expect(!"Alitta succinea" %in% names(kinds), "a name matched as given is not listed")
expect(identical(kinds[["Nereis virens"]], "accepted"), "a synonym replaced by its accepted name")
expect(grepl("not an accepted name; WoRMS gives Alitta virens", r$changes[[which(names(kinds) == "Nereis virens")]]$why),
       "the reason names the accepted name")
expect(length(r$changes[[which(names(kinds) == "Nereis virens")]]$candidates) == 1, "the unaccepted row is not offered as a choice")
expect(identical(kinds[["Acartia X"]], "higher"), "a species not found, matched at the genus")
expect(identical(kinds[["Navicula"]], "disagrees"), "a namesake in another kingdom is flagged first")
nav <- r$changes[[which(names(kinds) == "Navicula")]]
expect(length(nav$candidates) == 2 && grepl("Chromista, Ochrophyta", nav$labels[2]), "both Naviculas offered, with their groups")
expect(grepl("several|candidates", nav$why), "the namesake's reason also says there were two candidates")
expect(identical(kinds[["uncultured eukaryote"]], "not_found"), "no match: incertae sedis")
expect(identical(kinds[["Chironomus"]], "higher"), "a match at the phylum is a higher rank, not a disagreement")

# The person's choices: the diatom for Navicula, and no match for the Acartia
picks <- list()
picks[[nav$key]] <- as.character(nav$candidates[2])
ac <- r$changes[[which(names(kinds) == "Acartia X")]]
picks[[ac$key]] <- "none"
m2 <- apply_taxa_choices(worms, picks)
nrows <- which(m2$verbatimIdentification == "Eukaryota;Ochrophyta;Bacillariophyceae;Navicula")
expect(identical(m2$selected_match[nrows], c("False", "True")), "the chosen candidate becomes the selected row")
arow <- which(m2$verbatimIdentification == "Arthropoda;Hexanauplia;Acartia;Acartia_sp_X1")
expect(m2$scientificName[arow] == "" && m2$scientificNameID[arow] == "" && m2$selected_match[arow] == "True",
       "no match empties the selected row's name and ID (incertae sedis)")
expect(identical(m2[-c(nrows, arow), ], worms[-c(nrows, arow), ]), "other rows are unchanged")
tmp <- tempfile(fileext = ".tsv"); write_mapping(m2, tmp)
back <- utils::read.delim(tmp, colClasses = "character", na.strings = character(), check.names = FALSE, quote = "")
expect(identical(names(back), names(worms)) && nrow(back) == nrow(worms), "the copy keeps the columns and rows")
again <- changes_of(back)
expect(identical(vapply(again$changes, `[[`, "", "kind")[vapply(again$changes, `[[`, "", "lowest") == "Navicula"], "several"),
       "after choosing the diatom, Navicula agrees with the string (two candidates remain)")

# GBIF: names carry their authorship, ranks are lower case, and there is no cleanedTaxonomy in older tables
gbif <- worms[0, setdiff(cols, "scientificNameID")]
add <- function(...) { x <- row(...); x$scientificNameID <- NULL; x$nameAccordingTo <- "GBIF"; x$taxonID <- "gbif:1"; x }
gbif <- rbind(cbind(gbif, taxonID = character()),
  add("Annelida;Polychaeta;Alitta;Alitta virens", "", "True", "Alitta virens (M.Sars, 1835)", "species", "Animalia",
      "Annelida", "Polychaeta", "Alitta", type = "GBIF_EXACT"),
  add("Chordata;Actinopteri;Gadus;Gadus_morhuaa", "", "True", "Gadus morhua Linnaeus, 1758", "species", "Animalia",
      "Chordata", "Actinopteri", "Gadus", type = "GBIF_FUZZY"),
  add("Chordata;Actinopteri;Gadus;Gadus_novus", "", "True", "Gadus Linnaeus, 1758", "genus", "Animalia",
      "Chordata", "Actinopteri", "Gadus", type = "GBIF_HIGHERRANK"))
g <- changes_of(gbif)
gk <- setNames(vapply(g$changes, `[[`, "", "kind"), vapply(g$changes, `[[`, "", "lowest"))
expect(!"Alitta virens" %in% names(gk), "GBIF: a name with its authorship is matched as given")
expect(identical(gk[["Gadus morhuaa"]], "spelling") && grepl("Matched as Gadus morhua", g$changes[[which(names(gk) == "Gadus morhuaa")]]$why),
       "GBIF: a fuzzy match to another spelling")
expect(identical(gk[["Gadus novus"]], "higher"), "GBIF: a genus with its authorship, for a species not found, is a higher rank")
expect(g$api == "GBIF", "the register is named from the table")
expect(identical(unname(vapply(r$changes, `[[`, "", "kind")), c("disagrees", "not_found", "higher", "higher", "accepted")),
       "the changes come most important first")

cat(if (fails) sprintf("%d failed\n", fails) else "All passed\n")
quit(status = if (fails) 1 else 0)
