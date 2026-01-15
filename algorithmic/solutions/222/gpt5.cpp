#include <bits/stdc++.h>
using namespace std;

static const long long N = 1000000;
static const int S = 1024; // ~sqrt(1e6)
static const int J = (N + S - 1) / S;
static const long long B = 1;

long long ask(long long v, long long x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    return res;
}

void answer(long long s) {
    cout << "! " << s << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    for (int tcase = 0; tcase < n; ++tcase) {
        // Get a cycle vertex
        long long c = ask(1, 1);

        unordered_map<long long, int> pos;
        pos.reserve(S * 2);
        pos.max_load_factor(0.7f);

        // Baby steps: store largest i for each label
        for (int i = 0; i < S; ++i) {
            long long x = B + i;
            long long y = ask(c, x);
            auto it = pos.find(y);
            if (it == pos.end()) pos.emplace(y, i);
            else if (it->second < i) it->second = i;
        }

        long long dmin = LLONG_MAX;

        // Giant steps: look for matches
        for (int j = 1; j <= J; ++j) {
            long long x = B + 1LL * j * S;
            long long y = ask(c, x);
            auto it = pos.find(y);
            if (it != pos.end()) {
                long long d = 1LL * j * S - it->second;
                if (d > 0 && d < dmin) dmin = d;
            }
        }

        if (dmin == LLONG_MAX) {
            // Shouldn't happen; fall back to 1e6
            dmin = N;
        }

        // Optional verification (not strictly necessary, but safe)
        long long vcheck = ask(c, dmin);
        if (vcheck != c) {
            // As a safeguard, try reducing dmin by gcd steps if mismatch (shouldn't occur)
            // Fallback to brute refine by dividing primes of dmin to minimal multiple
            long long m = dmin;
            for (long long p = 2; p * p <= m; ++p) {
                if (m % p == 0) {
                    while (m % p == 0) {
                        long long test = m / p;
                        long long vt = ask(c, test);
                        if (vt == c) m = test;
                        else break;
                    }
                }
            }
            if (m > 1) {
                long long test = 1;
                // m might be prime > 1 now, try divide once
                if (dmin % m == 0) {
                    test = dmin / m;
                    long long vt = ask(c, test);
                    if (vt == c) m = test;
                    else m = dmin;
                } else {
                    m = dmin;
                }
            }
            dmin = m;
        }

        answer(dmin);
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != 1) return 0;
    }

    return 0;
}