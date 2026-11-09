from .seed import seed_database

if __name__ == "__main__":
    seed_database(reset=True)
    print("Knowledge mock data seeded.")
