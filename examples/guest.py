from karokit.guest import GuestClient


def main() -> None:
    client = GuestClient()
    print("Guest client initialized:", client.base_url)


if __name__ == "__main__":
    main()
