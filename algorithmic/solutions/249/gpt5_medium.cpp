#include <bits/stdc++.h>
using namespace std;

int n;

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    auto rand_int = [&](int l, int r) {
        return uniform_int_distribution<int>(l, r)(rng);
    };

    vector<int> all(n);
    iota(all.begin(), all.end(), 1);

    // Choose a pivot using small sampling to avoid worst-case
    int R = 1;
    if (n > 1) {
        int K = min(3, n);
        vector<int> pivots;
        // select K distinct random pivots
        {
            vector<int> tmp = all;
            shuffle(tmp.begin(), tmp.end(), rng);
            pivots.assign(tmp.begin(), tmp.begin() + K);
        }
        int bestCnt = INT_MAX;
        int s = min(25, n - 1);
        for (int p : pivots) {
            vector<int> pool;
            pool.reserve(n - 1);
            for (int x = 1; x <= n; ++x) if (x != p) pool.push_back(x);
            shuffle(pool.begin(), pool.end(), rng);
            pool.resize(s);

            int mn = INT_MAX, cnt = 0;
            for (int j : pool) {
                int v = ask(p, j);
                if (v < mn) { mn = v; cnt = 1; }
                else if (v == mn) cnt++;
            }
            if (cnt < bestCnt) {
                bestCnt = cnt;
                R = p;
            }
        }
    }

    // Full pass with pivot R
    vector<int> v(n + 1, -1);
    int minV = INT_MAX;
    for (int i = 1; i <= n; ++i) {
        if (i == R) continue;
        v[i] = ask(R, i);
        if (v[i] < minV) minV = v[i];
    }

    vector<int> C;
    for (int i = 1; i <= n; ++i) {
        if (i == R) continue;
        if (v[i] == minV) C.push_back(i);
    }
    if (C.empty()) {
        // Fallback: extremely unlikely, but in case, pick any index as candidate set
        for (int i = 1; i <= n; ++i) if (i != R) { C.push_back(i); break; }
    }

    // Eliminate to find index z where p[z] = 0
    while (C.size() > 1) {
        int t;
        while (true) {
            t = rand_int(1, n);
            bool inC = false;
            for (int x : C) if (x == t) { inC = true; break; }
            if (!inC) break;
        }
        int mn = INT_MAX;
        vector<int> vals(C.size());
        for (size_t idx = 0; idx < C.size(); ++idx) {
            int i = C[idx];
            vals[idx] = ask(t, i);
            if (vals[idx] < mn) mn = vals[idx];
        }
        vector<int> C2;
        for (size_t idx = 0; idx < C.size(); ++idx) {
            if (vals[idx] == mn) C2.push_back(C[idx]);
        }
        // If no shrink (very unlikely), try another t
        if (C2.size() == C.size()) continue;
        C.swap(C2);
    }

    int z = C[0];

    vector<int> p(n + 1, 0);
    p[z] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == z) continue;
        p[i] = ask(z, i);
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << p[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}