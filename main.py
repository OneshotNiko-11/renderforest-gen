import requests
import random
import string
import threading
import time
import os
import re
from colorama import init, Fore

init()

def load_proxies():
    try:
        with open("proxies.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
            if proxies:
                print(Fore.YELLOW + f"[*] loaded {len(proxies)} proxies")
            return proxies
    except:
        return []

def get_proxy(proxies, index):
    if not proxies:
        return None
    return proxies[index % len(proxies)]

def setup_session_proxy(session, proxy_str, use_proxies):
    if use_proxies and proxy_str:
        try:
            session.proxies.update({
                'http': f'socks5://{proxy_str}',
                'https': f'socks5://{proxy_str}'
            })
        except:
            pass
    return session

def create_temp_inbox(session):
    try:
        url = 'https://api.internal.temp-mail.io/api/v3/email/new'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        payload = {"min_name_length": 10, "max_name_length": 10}
        response = session.post(url, headers=headers, json=payload, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()
        email = data.get('email')
        token = data.get('token')

        if not email or not token:
            return None

        return {'address': email, 'token': token}
    except:
        return None

def check_inbox_with_retry(session, token, email):
    try:
        url = f'https://api.internal.temp-mail.io/api/v3/email/{email}/messages'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }

        print(Fore.YELLOW + "[*] waiting for verification email...")

        for attempt in range(10):
            try:
                response = session.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    messages = response.json()

                    if messages:
                        for msg in messages:
                            subject = str(msg.get('subject', '')).lower()

                            if 'renderforest' in subject and 'registration' in subject:
                                print(Fore.GREEN + "[+] verification email found")

                                body_text = msg.get('body_text', '')
                                body_html = msg.get('body_html', '')

                                if body_text:
                                    match = re.search(r'https://www\.renderforest\.com/verify/[^\s\n]+', body_text)
                                    if match:
                                        return match.group(0)

                                if body_html:
                                    match = re.search(r'https://www\.renderforest\.com/verify/[^\s"\']+', body_html)
                                    if match:
                                        return match.group(0)

                print(Fore.YELLOW + f"[*] check {attempt + 1}/10 - no email yet, retrying in 5s...")
                time.sleep(5)

            except Exception as e:
                print(Fore.RED + f"[!] check error: {e}")
                time.sleep(5)

        print(Fore.RED + "[-] timeout waiting for verification email")
        return None

    except Exception as e:
        print(Fore.RED + f"[!] inbox check error: {e}")
        return None

def generate_username():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

def generate_name():
    first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
                   "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Hugh"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "G Rection", "Jazz", "Janice"]
    return random.choice(first_names), random.choice(last_names)

def generate_password(username):
    return f"{username}!"

def create_account(proxies, target_accounts, accounts_created, lock, running, proxy_index_counter, use_proxies):
    while running[0]:
        with lock:
            if accounts_created[0] >= target_accounts:
                break
            proxy_index = proxy_index_counter[0]
            proxy_index_counter[0] += 1

        proxy = get_proxy(proxies, proxy_index) if use_proxies else None
        session = requests.Session()
        session = setup_session_proxy(session, proxy, use_proxies)

        try:
            temp_mail = create_temp_inbox(session)
            if not temp_mail or 'address' not in temp_mail or 'token' not in temp_mail:
                continue

            email = temp_mail['address']
            token = temp_mail['token']

            print(Fore.GREEN + "[*] (mail made) " + Fore.LIGHTMAGENTA_EX + f"({email})")

            username = generate_username()
            first_name, last_name = generate_name()
            password = generate_password(username)

            print(Fore.YELLOW + "[*] getting csrf token...")
            csrf_response = session.get('https://www.renderforest.com/csrf', timeout=10)
            csrf_data = csrf_response.json()
            csrf_token = csrf_data.get('token')

            if not csrf_token:
                print(Fore.RED + "[-] failed to get csrf token")
                continue

            session.cookies.update({
                '_csrf': csrf_token,
                '__rf_uid': '%7B%22exp%22%3A%222027-01-13T18%3A51%3A44.085Z%22%2C%22uid%22%3A%222987a203b80f4e0482a06867b8369011%22%7D'
            })

            url = 'https://www.renderforest.com/signup'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'https://www.renderforest.com',
                'Referer': 'https://www.renderforest.com/',
                'X-CSRF-Token': csrf_token
            }

            payload = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
                "password_confirmation": password,
                "user_check": "1"
            }

            response = session.post(url, headers=headers, json=payload, timeout=15)

            if response.status_code == 200:
                print(Fore.GREEN + "[+] registered! checking inbox...")

                verification_link = check_inbox_with_retry(session, token, email)

                if verification_link:
                    print(Fore.CYAN + "[*] verifying email...")
                    verify_response = session.get(verification_link, timeout=10)
                    if verify_response.status_code == 200:
                        with lock:
                            if accounts_created[0] < target_accounts:
                                accounts_created[0] += 1
                                with open("accs.txt", "a") as f:
                                    f.write(f"{email}:{password}\n")  

                                print(Fore.CYAN + "[+] (created) " + Fore.LIGHTMAGENTA_EX + f"({email}:{password})")
                    else:
                        print(Fore.RED + f"[-] verification failed: {verify_response.status_code}")
                else:
                    print(Fore.RED + "[-] no verification email found")

            elif response.status_code == 429:

                retry_after = response.headers.get('Retry-After')

                if retry_after:
                    wait_time = int(retry_after)
                    print(Fore.RED + f"[-] Cloudflare blocked for {wait_time} seconds ({wait_time/60:.1f} minutes) - the current thread will pause until ratelimit is gone. Try using a variety of proxies, atleast 50 or more. If you are not using a proxy, you will have to wait an hour.")
                    print(Fore.MAGENTA + f"Current proxy: {proxy}")
                    time.sleep(wait_time)
                else:
                    print(Fore.RED + "[-] No Retry-After header, waiting 20 seconds...")
                    time.sleep(20)

            else:
                print(Fore.RED + f"[-] (failed) {response.status_code}")

        except Exception as e:
            print(Fore.RED + f"[!] error: {e}")
            continue

        delay = random.uniform(10, 15)
        print(Fore.YELLOW + f"[*] waiting {delay:.1f}s between attempts...")
        time.sleep(delay)

def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    print(Fore.LIGHTYELLOW_EX + "Renderforest.com Account Generator")
    print(Fore.LIGHTRED_EX + "WARNING: Use 1-3 threads without proxies - Renderforest has 1-hour rate limits.")

    proxies = []
    use_proxies = False

    use_proxy_input = input(Fore.LIGHTCYAN_EX + "Use proxies? (y/n): " + Fore.WHITE).lower()
    if use_proxy_input == 'y':
        proxies = load_proxies()
        if not proxies:
            print(Fore.RED + "[!] no proxies found")
            return
        use_proxies = True
        print(Fore.GREEN + "[+] using proxies")
    else:
        print(Fore.YELLOW + "[*] running without proxies")

    try:
        target_accounts = int(input(Fore.LIGHTCYAN_EX + "Accounts to make: " + Fore.WHITE))
        threads_count = int(input(Fore.LIGHTCYAN_EX + "Threads: " + Fore.WHITE))
    except:
        return

    accounts_created = [0]
    running = [True]
    lock = threading.Lock()
    proxy_index_counter = [0]
    threads = []

    for i in range(threads_count):
        thread = threading.Thread(target=create_account, args=(proxies, target_accounts, accounts_created, lock, running, proxy_index_counter, use_proxies), daemon=True)
        threads.append(thread)
        thread.start()

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.5)
            if accounts_created[0] >= target_accounts:
                running[0] = False
                break
    except KeyboardInterrupt:
        running[0] = False
        print(Fore.RED + "\n[!] stopping...")

    print(Fore.LIGHTGREEN_EX + f"\n✅ created {accounts_created[0]} accounts")
    print(Fore.LIGHTBLUE_EX + "[*] saved to accs.txt (email:password)")

if __name__ == "__main__":
    main()
