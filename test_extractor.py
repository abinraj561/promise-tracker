import nlp_extractor

def run_tests():
    samples = [
        "Shihab: Can you deliver the table by Friday?\nOwner: Yes, Friday evening.",
        "Rahul: Okay bro, I'll pay Rs 20000 tomorrow and you send the design by Monday.",
        "Deepak: Can you repair my iPhone screen by 4 PM today?\nArjun: Yes sir, ready by 4 PM."
    ]

    for s in samples:
        print("\n" + "="*50)
        print("SAMPLE INPUT:\n" + s)
        results = nlp_extractor.extract_promises_from_text(s)
        print(f"\nFound {len(results)} Promise(s):")
        for i, p in enumerate(results, 1):
            print(f"  [{i}] Customer: {p['customer_name']}")
            print(f"      Direction: {p['direction']}")
            print(f"      Title: {p['title']}")
            print(f"      Deliverable: {p['deliverable']}")
            print(f"      Due: {p['due_date_text']} ({p['due_date']})")
            print(f"      Responsible: {p['responsible_person']} - {p['responsible_role']}")
            curr = p['currency'].encode('ascii', 'replace').decode('ascii')
            print(f"      Payment: {curr}{p['payment_amount']}")

if __name__ == "__main__":
    run_tests()
