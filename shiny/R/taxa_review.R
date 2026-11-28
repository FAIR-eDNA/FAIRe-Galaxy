# edna2obis: match taxa writes a mapping table with one row per candidate name for each taxonomy string
# (and assay), and selected_match True on the one it chose. These functions find the names the matching
# changed, say why in plain words, and write a copy of the table with the person's own choices. Names
# matched as they are given (after tidying, such as '_' to a space or dropping 'sp.') are only counted.

TAXA_CHANGE_KINDS <- c(
  disagrees = "Classification disagrees with your string",
  several = "More than one candidate",
  not_found = "Not found",
  higher = "Matched at a higher rank",
  accepted = "Accepted name used",
  spelling = "Matched to another spelling"
)
TAXA_CHANGE_NOTES <- c(
  disagrees = paste("Only the name itself agrees with your string; the rest of its classification differs, so it may be",
                    "a namesake in another group. Check these first."),
  several = "The name has more than one entry; the one whose classification agrees best with your string was chosen.",
  not_found = "No name in the string was found, so these are recorded as incertae sedis (not placed).",
  higher = "The most specific name was not found, so the next name up the string was used.",
  accepted = "The name in your string is a synonym or not accepted, and the accepted name is used.",
  spelling = "The match is spelt differently from the names in your string."
)

# The names in a taxonomy string, tidied as edna2obis does: split at ';', rank prefixes such as 'g__'
# removed, '_', '-' and '/' to spaces, numbers, 'sp.' and 'unassigned' dropped
taxon_parts <- function(s) {
  p <- trimws(strsplit(if (is.null(s) || is.na(s)) "" else s, ";", fixed = TRUE)[[1]])
  p <- sub("^[a-zA-Z]__", "", p)
  p <- gsub("[_/-]", " ", p)
  p <- gsub(" spp?\\.", "", p)
  p <- gsub("[0-9]+", "", p)
  p <- trimws(gsub("\\s+", " ", p))
  p[nchar(p) > 1 & tolower(p) != "unassigned"]
}

taxa_changes <- function(map) {
  need <- c("verbatimIdentification", "selected_match", "scientificName")
  if (is.null(map) || !nrow(map) || !all(need %in% names(map))) return(NULL)
  col <- function(f) if (f %in% names(map)) map[[f]] else rep("", nrow(map))
  norm <- function(x) tolower(trimws(gsub("\\s+", " ", x)))
  truthy <- function(v) tolower(trimws(v)) %in% c("true", "1", "yes")
  # a name given as 'Alitta virens' matches 'Alitta virens' and GBIF's 'Alitta virens (M.Sars, 1835)': what
  # follows the name is its authorship (a capital or a bracket), where a species' epithet is lower case
  is_name <- function(sci, name) {
    s <- trimws(gsub("\\s+", " ", sci)); n <- trimws(gsub("\\s+", " ", name))
    if (!nzchar(n)) return(FALSE)
    if (tolower(s) == tolower(n)) return(TRUE)
    startsWith(tolower(s), paste0(tolower(n), " ")) && grepl("^[A-Z(]", substring(s, nchar(n) + 2))
  }
  ranks <- c("kingdom", "phylum", "class", "order", "family", "genus")
  assay <- col("assay_name")
  key <- paste(col("verbatimIdentification"), assay, sep = "\r")
  api <- { a <- unique(col("nameAccordingTo")); a <- a[nzchar(a)]; if (length(a)) a[1] else "the register" }
  out <- list()
  for (k in unique(key)) {
    rows <- which(key == k)
    sel <- rows[truthy(col("selected_match")[rows])][1]
    if (is.na(sel)) sel <- rows[1]
    cleaned <- col("cleanedTaxonomy")[sel]
    parts <- if (nzchar(trimws(cleaned))) trimws(strsplit(cleaned, ";", fixed = TRUE)[[1]]) else taxon_parts(col("verbatimIdentification")[sel])
    parts <- parts[nzchar(parts)]
    lowest <- if (length(parts)) tail(parts, 1) else ""
    sci <- col("scientificName")[sel]
    rank <- tolower(col("taxonRank")[sel])
    # the rows a person can choose from: upstream shows unaccepted names for transparency, but never selects them
    cands <- rows[!truthy(col("unaccepted_match")[rows]) & nzchar(trimws(col("scientificName")[rows])) &
                    norm(col("scientificName")[rows]) != "incertae sedis"]
    if (!sel %in% cands && norm(sci) != "incertae sedis" && nzchar(trimws(sci))) cands <- c(sel, cands)
    cands <- cands[!duplicated(paste(norm(col("scientificName")[cands]), norm(col("kingdom")[cands])))]
    at <- which(vapply(parts, function(p) is_name(sci, p), logical(1)))
    # whether the string's names above the one matched (and above its genus, which a species' name
    # implies) appear in the match's classification: a namesake in another group shares the name, but
    # none of the higher names
    upto <- if (length(at)) parts[seq_len(max(at) - 1)] else head(parts, -1)
    tokens <- setdiff(norm(upto), c("eukaryota", norm(col("genus")[sel])))
    cvals <- norm(c(vapply(ranks, function(r) col(r)[sel], ""), sci))
    agree <- sum(vapply(tokens, function(t) any(cvals == t), logical(1)))
    queried <- sub("^Success_(Batch|AphiaID)_", "", col("match_type_debug")[sel])
    if (!nzchar(queried) || queried == col("match_type_debug")[sel]) queried <- lowest
    kinds <- character(); why <- character()
    found <- nzchar(trimws(sci)) && norm(sci) != "incertae sedis" && !grepl("^(Failed|No_GBIF)", col("match_type_debug")[sel])
    if (!found) {
      kinds <- "not_found"; why <- sprintf("Not found in %s: recorded as incertae sedis.", api)
    } else {
      group <- paste(Filter(nzchar, c(col("kingdom")[sel], col("phylum")[sel], col("class")[sel])), collapse = " > ")
      if (length(tokens) >= 2 && agree == 0) {
        kinds <- c(kinds, "disagrees")
        why <- c(why, sprintf("Only the name agrees with your string: %s places it in %s.", api, if (nzchar(group)) group else "another group"))
      }
      if (length(cands) > 1) {
        kinds <- c(kinds, "several"); why <- c(why, sprintf("%d candidates.", length(cands)))
      }
      if (length(at) && max(at) < length(parts)) {
        kinds <- c(kinds, "higher")
        why <- c(why, sprintf("'%s' was not found, so the match is at %s.", lowest, if (nzchar(rank)) rank else "a higher rank"))
      }
      if (truthy(col("replaced_unaccepted")[sel])) {
        kinds <- c(kinds, "accepted")
        why <- c(why, sprintf("'%s' is not an accepted name; %s gives %s.", queried, api, sci))
      } else if (!length(at)) {
        kinds <- c(kinds, "spelling"); why <- c(why, sprintf("Matched as %s.", sci))
      }
    }
    if (!length(kinds)) next
    lab <- function(r) {
      g <- paste(Filter(nzchar, c(col("kingdom")[r], col("phylum")[r])), collapse = ", ")
      if (nzchar(g)) sprintf("%s (%s)", col("scientificName")[r], g) else col("scientificName")[r]
    }
    out[[length(out) + 1]] <- list(key = k, verbatim = col("verbatimIdentification")[sel], assay = assay[sel], lowest = lowest,
                                   name = if (found) sci else "incertae sedis", rank = rank,
                                   kind = names(TAXA_CHANGE_KINDS)[names(TAXA_CHANGE_KINDS) %in% kinds][1],
                                   why = paste(why, collapse = " "), selected = sel, candidates = cands,
                                   labels = vapply(cands, lab, ""))
  }
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
