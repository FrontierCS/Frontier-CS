#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n_ll;
    if (!(cin >> n_ll)) return 0;
    int n = (int)n_ll;

    // Required size
    long double tmp = (long double)n_ll / 2.0L;
    int req = (int)floor(sqrtl(tmp));
    if (req <= 0) req = 1; // always take at least 1 element

    const int XOR_BITS = 24;
    const int XOR_SIZE = 1 << XOR_BITS;

    // Epoch-based marking to avoid clearing arrays each attempt
    vector<uint16_t> usedXorEpoch(XOR_SIZE, 0);
    vector<uint16_t> usedNumEpoch(n + 1, 0);

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    int maxAttempts = 4;
    vector<int> bestAns;
    int bestSize = 0;

    for (int attempt = 1; attempt <= maxAttempts; ++attempt) {
        vector<int> cur;
        cur.reserve(req);

        // Each attempt has its own epoch id
        uint16_t epoch = (uint16_t)attempt;

        long long triesLimit = (long long)req * 12 + 100;
        if (triesLimit > (long long)n * 2) triesLimit = (long long)n * 2;

        long long tries = 0;
        while ((int)cur.size() < req && tries < triesLimit) {
            ++tries;
            int x = (int)(rng() % n) + 1;

            if (usedNumEpoch[x] == epoch) continue; // already tried this x in this attempt
            usedNumEpoch[x] = epoch;

            bool ok = true;
            for (int a : cur) {
                int xv = a ^ x;
                if (usedXorEpoch[xv] == epoch) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;

            // Accept x
            for (int a : cur) {
                int xv = a ^ x;
                usedXorEpoch[xv] = epoch;
            }
            cur.push_back(x);
        }

        if ((int)cur.size() > bestSize) {
            bestSize = (int)cur.size();
            bestAns = cur;
        }
        if (bestSize >= req) break; // good enough
    }

    // In extremely unlikely case bestSize < req, just output best we have (problem expects >= req, but this should virtually never happen)
    cout << bestSize << "\n";
    if (!bestAns.empty()) {
        for (int i = 0; i < (int)bestAns.size(); ++i) {
            if (i) cout << ' ';
            cout << bestAns[i];
        }
    }
    cout << "\n";

    return 0;
}