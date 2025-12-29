#include <bits/stdc++.h>
using namespace std;

static const long long LIM = 1000000000000000000LL;

static long long ask(long long q) {
    cout << "0 " << q << '\n';
    cout.flush();
    long long g;
    if (!(cin >> g)) exit(0);
    if (g == -1) exit(0);
    return g;
}

static void answer(long long ans) {
    cout << "1 " << ans << '\n';
    cout.flush();
}

static vector<int> sieve_primes(int n) {
    vector<bool> isPrime(n + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= n; i++) if (isPrime[i]) {
        for (int j = i * i; j <= n; j += i) isPrime[j] = false;
    }
    vector<int> primes;
    for (int i = 2; i <= n; i++) if (isPrime[i]) primes.push_back(i);
    return primes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    vector<int> primes = sieve_primes(1000);

    vector<vector<int>> blocks;
    vector<long long> prods;
    {
        long long curProd = 1;
        vector<int> cur;
        for (int p : primes) {
            if (!cur.empty() && (__int128)curProd * p > LIM) {
                blocks.push_back(cur);
                prods.push_back(curProd);
                cur.clear();
                curProd = 1;
            }
            cur.push_back(p);
            curProd *= p;
        }
        if (!cur.empty()) {
            blocks.push_back(cur);
            prods.push_back(curProd);
        }
    }

    for (int tc = 0; tc < T; tc++) {
        vector<int> found;
        found.reserve(16);

        for (size_t i = 0; i < blocks.size(); i++) {
            long long g = ask(prods[i]);
            if (g <= 1) continue;
            for (int p : blocks[i]) {
                if (g % p == 0) {
                    found.push_back(p);
                    while (g % p == 0) g /= p;
                }
                if (g == 1) break;
            }
        }

        long long d_small = 1;
        for (int p : found) {
            long long pp = 1;
            while ((__int128)pp * p <= LIM) pp *= p;
            long long g = ask(pp);
            int e = 0;
            while (g % p == 0) {
                g /= p;
                e++;
            }
            d_small *= (e + 1);
        }

        long long ans = 2LL * d_small;
        answer(ans);
    }

    return 0;
}