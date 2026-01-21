#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

struct Interactor {
    int ask(int v, long long x) {
        cout << "? " << v << " " << x << "\n";
        cout.flush();
        long long ans;
        if (!(cin >> ans)) die();
        if (ans == -1) die();
        return (int)ans;
    }

    void answer(long long s) {
        cout << "! " << s << "\n";
        cout.flush();
        int verdict;
        if (!(cin >> verdict)) die();
        if (verdict == -1) die();
    }
};

static vector<long long> uniquePrimeFactors(long long n) {
    vector<long long> primes;
    for (long long p = 2; p * p <= n; ++p) {
        if (n % p == 0) {
            primes.push_back(p);
            while (n % p == 0) n /= p;
        }
    }
    if (n > 1) primes.push_back(n);
    return primes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    Interactor it;

    const int m = 1000; // m*m = 1e6
    for (int tc = 0; tc < n; ++tc) {
        int c = it.ask(1, 1); // always on cycle

        unordered_map<int, int> baby;
        baby.reserve(m * 2);
        baby.max_load_factor(0.7f);

        baby[c] = 0;
        for (int i = 1; i < m; ++i) {
            int u = it.ask(c, i);
            if (!baby.count(u)) baby[u] = i;
        }

        long long M = -1;
        for (int j = 1; j <= m; ++j) {
            long long exp = 1LL * j * m;
            int u = it.ask(c, exp);
            auto itb = baby.find(u);
            if (itb != baby.end()) {
                M = exp - itb->second; // multiple of cycle length
                break;
            }
        }

        if (M < 0) M = 1000000; // should never happen

        auto primes = uniquePrimeFactors(M);

        auto isMultiple = [&](long long k) -> bool {
            if (k <= 0) return false;
            int u = it.ask(c, k);
            return u == c;
        };

        for (long long p : primes) {
            while (M % p == 0) {
                long long cand = M / p;
                if (cand >= 1 && isMultiple(cand)) M = cand;
                else break;
            }
        }

        it.answer(M);
    }

    return 0;
}