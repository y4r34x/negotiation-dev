# 1 - Find Relevant Contracts

The source of our contracts (at least to begin) is the SEC EDGAR database API. Some helpful tips:

  * Problem: some contracts are heavily redacted and search treats [***] as null characters
      * Solution: include the phrase 'NOT "competitively harmful" NOT "competitive harm"' in the search

  * Problem: there's no standard document type for agreements.
      * Solution: filter by form 8-K (best) or 10-K and search for terms found in the agreement types we care about. For example: 'software support agreement NOT "competitively harmful" NOT "competitive harm"' returns 223,432 usable agreements

  * Problem: some contracts are ludicrously long.
      * Solution: when we use python libraries later in this guide, sort by file size (<20kb)

  * Problem: some contracts are HTML while others are TXT
      * Solution: use beautiful soup to preprocess all XML into a standard format

  * Problem: storing thousands (if not millions) of 20kb documents becomes 20mb or 20gb...
      * Solution: storing just the TSV values is ~200b per file, so 1k rows will only be about 20kb

Problems out of the way, here's our process:

  * Search for: Software Agreement NOT "competitively harmful" NOT "competitive harm"
  * Filter by: Form 8-K (there should be 205,000 results)
  * Sanity check: the first three results should be:

      https://www.sec.gov/Archives/edgar/data/1739942/000162828021014064/exhibit106-swinxable8xk.htm
      https://www.sec.gov/Archives/edgar/data/1905956/000121390023097468/ea190297ex10-1_treasure.htm
      https://www.sec.gov/Archives/edgar/data/1490978/000149097824000078/ex101_schrodingercolumbiam.htm




