# edna2obis: match taxa writes a mapping table with one row per candidate name for each taxonomy string
# (and assay), with selected_match True on the one it chose, and a changed names table: one row for each
# name whose selected match differs from the name given, with why (changed_names() in
# tools/edna2obis/edna2obis_galaxy.py, so Galaxy and the app use the same rules). These functions join
# that table to the mapping table's rows, for the choices on the page, and write a copy of the mapping
# table with the person's choices.

TAXA_CHANGE_NOTES <- c(
  disagrees = paste("Only the name itself agrees with your string; the rest of its classification differs, so it may be",
                    "a namesake in another group. Check these first."),
  several = "The name has more than one entry; the one whose classification agrees best with your string was chosen.",
  not_found = "No name in the string was found, so these are recorded as incertae sedis (not placed).",
  higher = "The most specific name was not found, so the next name up the string was used.",
  accepted = "The name in your string is a synonym or not accepted, and the accepted name is used.",
  spelling = "The match is spelt differently from the names in your string."
)

# For each changed name: the row selected, and the rows a person can choose from (upstream shows
# unaccepted names for transparency, but never selects them), with a label for each
taxa_changes <- function(map, ch) {
  need <- c("verbatimIdentification", "selected_match", "scientificName")
  if (is.null(map) || !nrow(map) || !all(need %in% names(map)) || is.null(ch)) return(NULL)
  col <- function(f) if (f %in% names(map)) map[[f]] else rep("", nrow(map))
  norm <- function(x) tolower(trimws(gsub("\\s+", " ", x)))
  truthy <- function(v) tolower(trimws(v)) %in% c("true", "1", "yes")
  key <- paste(col("verbatimIdentification"), col("assay_name"), sep = "\r")
  api <- { a <- unique(col("nameAccordingTo")); a <- a[nzchar(a)]; if (length(a)) a[1] else "the register" }
  out <- lapply(seq_len(nrow(ch)), function(i) {
    k <- paste(ch$verbatimIdentification[i], ch$assay_name[i], sep = "\r")
    rows <- which(key == k)
    sel <- rows[truthy(col("selected_match")[rows])][1]
    if (is.na(sel)) sel <- rows[1]
    cands <- rows[!truthy(col("unaccepted_match")[rows]) & nzchar(trimws(col("scientificName")[rows])) &
                    norm(col("scientificName")[rows]) != "incertae sedis"]
    if (length(sel) && !is.na(sel) && !sel %in% cands && ch$kind[i] != "not_found") cands <- c(sel, cands)
    cands <- cands[!duplicated(paste(norm(col("scientificName")[cands]), norm(col("kingdom")[cands])))]
    lab <- function(r) {
      g <- paste(Filter(nzchar, c(col("kingdom")[r], col("phylum")[r])), collapse = ", ")
      if (nzchar(g)) sprintf("%s (%s)", col("scientificName")[r], g) else col("scientificName")[r]
    }
    list(key = k, verbatim = ch$verbatimIdentification[i], assay = ch$assay_name[i], lowest = ch$your_name[i],
         name = ch$matched_to[i], rank = ch$taxonRank[i], kind = ch$kind[i], label = ch$change[i], why = ch$why[i],
         selected = sel, candidates = cands, labels = vapply(cands, lab, ""))
  })
  list(changes = out, n_names = length(unique(key)), api = api)
}

# A copy of the mapping table with the person's choices: picks is a named list, key -> the row chosen
# (as a number), or "none" for no match. With "none", the chosen row's name and ID are emptied, which
# edna2obis records as incertae sedis.
apply_taxa_choices <- function(map, picks) {
  if (!length(picks)) return(map)
  key <- paste(map$verbatimIdentification, if ("assay_name" %in% names(map)) map$assay_name else "", sep = "\r")
  truthy <- function(v) tolower(trimws(v)) %in% c("true", "1", "yes")
  for (k in names(picks)) {
    rows <- which(key == k)
    if (!length(rows)) next
    p <- picks[[k]]
    if (identical(p, "none")) {
      sel <- rows[truthy(map$selected_match[rows])][1]
      if (is.na(sel)) sel <- rows[1]
      for (f in intersect(c("scientificName", "scientificNameID", "taxonID"), names(map))) map[[f]][sel] <- ""
    } else {
      r <- suppressWarnings(as.integer(p))
      if (is.na(r) || !r %in% rows) next
      map$selected_match[rows] <- "False"
      map$selected_match[r] <- "True"
    }
  }
  map
}

write_mapping <- function(map, path) {
  utils::write.table(map, path, sep = "\t", quote = FALSE, row.names = FALSE, na = "", fileEncoding = "UTF-8")
  invisible(path)
}
