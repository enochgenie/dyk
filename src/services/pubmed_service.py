"""
PubMed API Integration for Evidence Retrieval
Fetches relevant scientific literature to ground insights.
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import time
from urllib.parse import quote


class PubMedAPI:
    """Interface to PubMed E-utilities API."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize PubMed API client.

        Args:
            email: Your email (recommended by NCBI)
            api_key: NCBI API key for higher rate limits (optional)
        """
        self.email = email or "researcher@example.com"
        self.api_key = api_key
        self.rate_limit_delay = (
            0.34 if not api_key else 0.11
        )  # seconds between requests

    def search(
        self, query: str, max_results: int = 5, min_year: Optional[int] = None
    ) -> List[str]:
        """
        Search PubMed and return PMIDs.

        Args:
            query: Search query string
            max_results: Maximum number of results
            min_year: Minimum publication year (e.g., 2019)

        Returns:
            List of PubMed IDs
        """
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "email": self.email,
            "sort": "relevance",
        }

        if min_year:
            params["term"] += f" AND {min_year}:3000[dp]"

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(
                f"{self.BASE_URL}esearch.fcgi", params=params, timeout=10
            )
            response.raise_for_status()

            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])

            return pmids

        except Exception as e:
            print(f"Error searching PubMed: {e}")
            return []

    def fetch_abstracts(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch article details including abstracts for given PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of article dictionaries
        """
        if not pmids:
            return []

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email,
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(
                f"{self.BASE_URL}efetch.fcgi", params=params, timeout=30
            )
            response.raise_for_status()

            return self._parse_xml_response(response.text)

        except Exception as e:
            print(f"Error fetching abstracts: {e}")
            return []

    def _parse_xml_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse XML response from PubMed into structured data."""
        articles = []

        try:
            root = ET.fromstring(xml_text)

            for article_elem in root.findall(".//PubmedArticle"):
                article = {}

                # PMID
                pmid_elem = article_elem.find(".//PMID")
                article["pmid"] = pmid_elem.text if pmid_elem is not None else None

                # Title
                title_elem = article_elem.find(".//ArticleTitle")
                article["title"] = title_elem.text if title_elem is not None else ""

                # Abstract
                abstract_texts = article_elem.findall(".//AbstractText")
                abstract_parts = []
                for abstract_elem in abstract_texts:
                    label = abstract_elem.get("Label", "")
                    text = abstract_elem.text or ""
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
                article["abstract"] = " ".join(abstract_parts)

                # Authors
                authors = []
                for author_elem in article_elem.findall(".//Author"):
                    last_name = author_elem.find("LastName")
                    fore_name = author_elem.find("ForeName")
                    if last_name is not None:
                        author = last_name.text
                        if fore_name is not None:
                            author = f"{fore_name.text} {author}"
                        authors.append(author)
                article["authors"] = authors

                # Journal
                journal_elem = article_elem.find(".//Journal/Title")
                article["journal"] = (
                    journal_elem.text if journal_elem is not None else ""
                )

                # Publication date
                pub_date = article_elem.find(".//PubDate")
                year_elem = pub_date.find("Year") if pub_date is not None else None
                article["year"] = year_elem.text if year_elem is not None else None

                # Publication types
                pub_types = []
                for pt in article_elem.findall(".//PublicationType"):
                    if pt.text:
                        pub_types.append(pt.text)
                article["publication_types"] = pub_types

                # URL
                article["url"] = f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"

                articles.append(article)

        except Exception as e:
            print(f"Error parsing XML: {e}")

        return articles

    def search_and_fetch(
        self, query: str, max_results: int = 5, min_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Convenience method: search and fetch abstracts in one call.

        Args:
            query: Search query
            max_results: Maximum results to fetch
            min_year: Minimum publication year

        Returns:
            List of articles with abstracts
        """
        pmids = self.search(query, max_results, min_year)
        if not pmids:
            return []

        return self.fetch_abstracts(pmids)


class EvidenceRetriever:
    """Higher-level evidence retrieval orchestrator."""

    def __init__(
        self,
        pubmed_client: PubMedAPI,
        max_results: int = 5,
        min_year: Optional[int] = None,
    ):
        self.pubmed = pubmed_client
        self.max_results = max_results
        self.min_year = min_year

    def retrieve_for_cohort(
        self,
        cohort: Dict[str, Any],
        health_domain: Optional[str] = None,
        insight_template: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve evidence relevant to a specific cohort.

        Args:
            cohort: Cohort dictionary with parameters
            health_domain: Optional health domain to focus on
            insight_template: Optional insight template to guide query generation
            max_sources: Maximum number of sources to retrieve

        Returns:
            Dictionary with queries, articles, and formatted context
        """
        # Generate search queries based on cohort
        queries = self._generate_queries(cohort, health_domain, insight_template)

        all_articles = []
        for query in queries[:3]:  # Limit to top 3 queries
            articles = self.pubmed.search_and_fetch(
                query, max_results=self.max_results, min_year=self.min_year
            )
            all_articles.extend(articles)

        # Deduplicate by PMID
        seen_pmids = set()
        unique_articles = []
        for article in all_articles:
            pmid = article.get("pmid")
            if pmid and pmid not in seen_pmids:
                seen_pmids.add(pmid)
                unique_articles.append(article)

        # Format context
        evidence_context = self._format_evidence_context(
            unique_articles[: self.max_results]
        )

        return {
            "queries": queries,
            "articles": unique_articles[: self.max_results],
            "evidence_context": evidence_context,
            "total_sources": len(unique_articles),
        }

    def _format_evidence_context(self, articles: List[Dict[str, Any]]) -> str:
        """
        Format fetched articles into a context string for LLM.

        Args:
            articles: List of article dictionaries

        Returns:
            Formatted evidence context string
        """
        if not articles:
            return "No evidence found."

        context_parts = []

        for i, article in enumerate(articles, 1):
            context_parts.append(f"\n{'=' * 80}")
            context_parts.append(f"EVIDENCE SOURCE {i}")
            context_parts.append(f"{'=' * 80}")
            context_parts.append(f"Title: {article.get('title', 'N/A')}")
            context_parts.append(
                f"Authors: {', '.join(article.get('authors', [])[:3])} et al."
                if article.get("authors")
                else "Authors: N/A"
            )
            context_parts.append(f"Journal: {article.get('journal', 'N/A')}")
            context_parts.append(f"Year: {article.get('year', 'N/A')}")
            context_parts.append(f"PMID: {article.get('pmid', 'N/A')}")
            context_parts.append(f"URL: {article.get('url', 'N/A')}")
            context_parts.append(
                f"Publication Types: {', '.join(article.get('publication_types', []))}"
            )
            context_parts.append(f"\nABSTRACT:")
            context_parts.append(article.get("abstract", "No abstract available"))
            context_parts.append("")

        return "\n".join(context_parts)

    def _generate_queries(
        self,
        cohort: Dict[str, Any],
        health_domain: Optional[str] = None,
        insight_template: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate PubMed search queries based on cohort characteristic, health domain, and insight template."""
        queries = []

        # Extract key parameters
        params = cohort["cohort_params"]
        age_group = params.get("age_group", "")
        gender = params.get("gender", "")
        ethnicity = params.get("ethnicity", "")
        conditions = params.get("health_conditions", "")
        smoking = params.get("smoking_status", "")
        bmi = params.get("bmi", "")
        activity = params.get("physical_activity", "")

        # Build base demographic query
        demo_parts = []
        if age_group:
            # Convert age group to query term
            demo_parts.append(age_group + " years old")

        if gender:
            demo_parts.append(gender)

        if ethnicity:
            demo_parts.append(ethnicity)

        demographic = " ".join(demo_parts)

        if health_domain:
            queries.append(f"{demographic} {health_domain}")

        return queries


# Example usage
if __name__ == "__main__":
    # Test PubMed API
    pubmed = PubMedAPI(
        email="enoch@geniehealth.care", api_key="03d462238cdb0267655817127bb92370ef08"
    )
    test_query = "30-39 obese female diabetes"

    abstracts = pubmed.search_and_fetch(test_query, max_results=2)
    print("Fetched Abstracts:", abstracts)

    # example cohort
    cohort = {
        "cohort_id": "cohort_0015",
        "cohort_params": {"age_group": "70+", "health_conditions": "diabetes"},
        "priority_level": 3,
        "description": "70+ years old, diabetes",
    }

    retriever = EvidenceRetriever(pubmed, max_results=3, min_year=2010)
    evidence = retriever.retrieve_for_cohort(cohort, health_domain="cardiovascular")

    print(f"Generated {len(evidence['queries'])} queries")
    print(f"Retrieved {evidence['total_sources']} unique sources")
    print("\nSample Evidence Context:")
    print(evidence["evidence_context"])
