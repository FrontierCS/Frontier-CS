#include <bits/stdc++.h>
using namespace std;

static const long long LIMX = 1000000000LL;
static const long long LIMQ = 1000000000000000000LL;
static const int THRESH_PRIME = 1000;

static vector<int> sieve_primes(int n) {
    vector<bool> is_prime(n + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; 1LL * i * i <= n; ++i) {
        if (!is_prime[i]) continue;
        for (int j = i * i; j <= n; j += i) is_prime[j] = false;
    }
    vector<int> primes;
    for (int i = 2; i <= n; ++i) if (is_prime[i]) primes.push_back(i);
    return primes;
}

static long long max_power_leq_1e9(int p) {
    long long pe = p;
    while (pe <= LIMX / p) pe *= p;
    return pe;
}

struct Block {
    long long q;
    vector<int> primes;
};

static long long ask_gcd(long long q) {
    cout << "0 " << q << "\n";
    cout.flush();
    long long g;
    if (!(cin >> g)) exit(0);
    return g;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    vector<int> primes = sieve_primes(THRESH_PRIME);

    vector<Block> blocks;
    {
        __int128 cur = 1;
        vector<int> curPr;
        for (int p : primes) {
            long long pe = max_power_leq_1e9(p);
            if (curPr.empty()) {
                cur = pe;
                curPr.push_back(p);
            } else {
                if (cur * (__int128)pe > (__int128)LIMQ) {
                    blocks.push_back(Block{(long long)cur, curPr});
                    cur = pe;
                    curPr.clear();
                    curPr.push_back(p);
                } else {
                    cur *= (__int128)pe;
                    curPr.push_back(p);
                }
            }
        }
        if (!curPr.empty()) blocks.push_back(Block{(long long)cur, curPr});
    }

    for (int tc = 0; tc < T; ++tc) {
        long long divA = 1;

        for (const auto &blk : blocks) {
            long long g = ask_gcd(blk.q);
            for (int p : blk.primes) {
                int e = 0;
                while (g % p == 0) {
                    g /= p;
                    ++e;
                }
                divA *= (e + 1);
            }
        }

        long long ans = divA * 2;
        cout << "1 " << ans << "\n";
        cout.flush();
    }

    return 0;
}