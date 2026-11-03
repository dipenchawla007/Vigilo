# Calls the installed openEBGM package (GPL-2 | GPL-3).
# This script does not copy that package. It is an external results check.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  message("expected one input file")
  quit(status = 2)
}
if (!requireNamespace("openEBGM", quietly = TRUE)) {
  message("openEBGM is not installed")
  quit(status = 3)
}

payload <- readLines(args[[1]], warn = FALSE)
theta <- as.numeric(strsplit(payload[[1]], " ", fixed = TRUE)[[1]])
counts <- read.table(text = paste(payload[-1], collapse = "\n"), col.names = c("N", "E"))
qn <- openEBGM::Qn(theta, N = counts$N, E = counts$E)
ebgm <- openEBGM::ebgm(theta, N = counts$N, E = counts$E, qn = qn, digits = 6)
eb05 <- openEBGM::quantBisect(
  percent = 5, theta = theta, N = counts$N, E = counts$E, qn = qn, digits = 4
)
eb95 <- openEBGM::quantBisect(
  percent = 95, theta = theta, N = counts$N, E = counts$E, qn = qn, digits = 4
)
cat(paste(ebgm, qn, eb05, eb95, sep = " "), sep = "\n")
