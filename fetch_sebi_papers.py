import re
import time
from pathlib import Path
from urllib.parse import quote
import httpx

PAPERS_DIR = Path(__file__).resolve().parent / "data" / "docs" / "papers"
BASE = "https://investor.sebi.gov.in"

DOCUMENTS = [
    ("/pdf/reference-material/languages/english/Securities Market Booklet.pdf", "sebi_securities_market_booklet"),
    ("/pdf/reference-material/languages/english/Financial Education Booklet (English).pdf", "sebi_financial_education_booklet"),
    ("/pdf/reference-material/languages/english/Financial Planning Guide (English).pdf", "sebi_financial_planning_guide"),
    ("/pdf/reference-material/Introduction to Commodity Derivatives Market.pdf", "sebi_commodity_derivatives_intro"),
    ("/pdf/reference-material/primarymarkets.pdf", "sebi_primary_markets_beginners_guide"),
    ("/pdf/reference-material/Primary.pdf", "sebi_primary_market_investor_message"),
    ("/pdf/reference-material/Secondaryma.pdf", "sebi_secondary_markets"),
    ("/pdf/reference-material/MFunds.pdf", "sebi_mutual_funds"),
    ("/pdf/reference-material/dos-and-donts-for-investors-investment-advisers.pdf", "sebi_investment_adviser_dos_donts"),
    ("/pdf/reference-material/Corporate.pdf", "sebi_corporate_restructuring"),
    ("/pdf/reference-material/sharedebentureholder.pdf", "sebi_share_debenture_holders_guide"),
    ("/pdf/reference-material/corporatebonds.pdf", "sebi_corporate_bonds"),
    ("/pdf/reference-material/sharedebenture.pdf", "sebi_share_debenture_investor_message"),
    ("/pdf/reference-material/beginners.pdf", "sebi_general_beginners_guide"),
    ("/pdf/reference-material/igrbrochure.pdf", "sebi_investor_grievance_redress"),
    ("/pdf/reference-material/ppt/PPT-21-ISM.pdf", "sebi_intro_to_securities_markets"),
    ("/pdf/reference-material/ppt/PPT-KYC-and-Account-Opening-in-Securities-Market.pdf", "sebi_kyc_account_opening"),
    ("/pdf/reference-material/ppt/PPT-3 How to invest in Intial Public Offer_ Feb 2025.pdf", "sebi_how_to_invest_ipo"),
    ("/pdf/reference-material/ppt/PPT-4 IHow to Invest in Rights Issue - Feb 2025.pdf", "sebi_how_to_invest_rights_issue"),
    ("/pdf/reference-material/ppt/PT-5 Corporate Action - Dividends, Bonus, Splits etc- Feb 2025.pdf", "sebi_corporate_actions"),
    ("/pdf/reference-material/ppt/PPT-6 How to buy and sell shares in Stock Exchange updated 30 Sept 2022.pdf", "sebi_how_to_buy_sell_shares"),
    ("/pdf/reference-material/ppt/PPT-7-Depository_Services_Jan24.pdf", "sebi_depository_services"),
    ("/pdf/reference-material/ppt/PPT-8-Introduction_to_Mutual_Funds_Investing_Jan24.pdf", "sebi_intro_mutual_funds_investing"),
    ("/pdf/reference-material/ppt/PPT-11_Investor_Awareness_-_Buyback_and_Open_Offer_of_Shares.pdf", "sebi_buyback_open_offer"),
    ("/pdf/reference-material/ppt/PPT-10 Updated PPT on REITs_approved 30 Sep 2022.pdf", "sebi_intro_reits"),
    ("/pdf/reference-material/ppt/PPT-11 Updated PPT on InvITs _approved 30 Sep 2022.pdf", "sebi_intro_invits"),
    ("/pdf/reference-material/ppt/PPT 13  on Introduction to ETFs.pdf", "sebi_intro_etfs"),
    ("/pdf/reference-material/ppt/PPT-14-Investments-by-NRIs-English.pdf", "sebi_nri_investments"),
    ("/pdf/reference-material/ppt/PPT-20-SASMF.pdf", "sebi_safeguarding_against_fraud"),
    ("/pdf/reference-material/ppt/Mutual-Fund-for-Beginners.pdf", "sebi_mutual_funds_beginners"),
    ("/pdf/reference-material/ppt/Mutual-Fund-for-intermediate.pdf", "sebi_mutual_funds_intermediate"),
    ("/pdf/reference-material/ppt/Mutual-Fund-for-Advance.pdf", "sebi_mutual_funds_advanced"),
]

def sanitize_filename(label: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", label)

def main():
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    already_have = {p.stem for p in PAPERS_DIR.glob("*.pdf")}

    downloaded = 0
    skipped_existing = 0
    failed = []

    for relative_path, label in DOCUMENTS:
        filename = sanitize_filename(label)
        if filename in already_have:
            skipped_existing += 1
            continue

        url = BASE + quote(relative_path)
        try:
            response = httpx.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()

            if not response.content.startswith(b"%PDF"):
                failed.append((label, "response did not start with %PDF"))
                continue

            dest = PAPERS_DIR / f"{filename}.pdf"
            dest.write_bytes(response.content)
            downloaded += 1
            print(f"Downloaded: {filename}.pdf ({len(response.content) // 1024} KB)")
        except Exception as e:
            failed.append((label, str(e)))
            print(f"Failed: {label} — {e}")

        time.sleep(1.0)

    print(f"\n{'=' * 50}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped (already had): {skipped_existing}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("\nFailed documents:")
        for label, reason in failed:
            print(f"  - {label}: {reason}")
    print(f"Total PDFs now in {PAPERS_DIR}: {len(list(PAPERS_DIR.glob('*.pdf')))}")
    print(f"{'=' * 50}")

if __name__ == "__main__":
    main()
