#include <bits/stdc++.h>
using namespace std;

static inline long long power_val(int a, int b) {
    return 2LL * a * b + 2LL * b + 2LL * max(a, b) + 1;
}

struct Rec {
    long long p;
    int u, v;
    bool operator<(Rec const& other) const {
        return p < other.p;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if(!(cin >> n)) return 0;

    int maxLen = 30 * n; // each |w_i| <= 30*n
    int Amax = max(1, maxLen - 1); // a = |X-run|, so |w| = a + 1

    // Prepare candidate list of a's
    vector<int> cand(Amax);
    iota(cand.begin(), cand.end(), 1);

    // Shuffle candidates for randomness to reduce chance of collision
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    shuffle(cand.begin(), cand.end(), rng);

    vector<int> avals;
    avals.reserve(n);

    // used set of powers for already chosen pairs to guarantee uniqueness
    unordered_set<long long> used;
    used.reserve((size_t)min(2000000, n * n * 2 + 1000));
    used.max_load_factor(0.7f);

    for (int x : cand) {
        if ((int)avals.size() == n) break;

        bool ok = true;
        // temporary storage for new powers to avoid duplicates among new pairs
        // use vector + sort/unique to reduce overhead
        vector<long long> temp;
        temp.reserve((size_t)avals.size() * 2 + 1);

        // compute all new pair powers with existing avals
        for (int a : avals) {
            long long p1 = power_val(x, a);
            long long p2 = power_val(a, x);
            if (used.find(p1) != used.end() || used.find(p2) != used.end()) {
                ok = false;
                break;
            }
            temp.push_back(p1);
            temp.push_back(p2);
        }
        if (!ok) continue;

        // self pair
        long long ps = power_val(x, x);
        if (used.find(ps) != used.end()) {
            ok = false;
        } else {
            temp.push_back(ps);
        }
        if (!ok) continue;

        // Ensure no duplicates within temp itself
        sort(temp.begin(), temp.end());
        if (unique(temp.begin(), temp.end()) != temp.end()) {
            ok = false;
        }
        if (!ok) continue;

        // Accept x: add to avals and insert powers into used
        avals.push_back(x);
        for (long long v : temp) used.insert(v);
    }

    // If not enough found (extremely unlikely), fallback: fill remaining with any distinct a's
    // and accept potential collisions (should not happen in practice).
    // But ensure at least n values.
    if ((int)avals.size() < n) {
        // Brute-force add remaining without checking (last resort)
        for (int x : cand) {
            if ((int)avals.size() == n) break;
            if (find(avals.begin(), avals.end(), x) == avals.end()) {
                avals.push_back(x);
            }
        }
    }

    // Output words
    for (int a : avals) {
        string s;
        s.reserve((size_t)a + 1);
        s.append(a, 'X');
        s.push_back('O');
        cout << s << '\n';
    }
    cout.flush();

    // Build mapping p -> (u,v) using sorted vector for memory efficiency
    vector<Rec> recs;
    recs.reserve((size_t)n * n);
    for (int i = 0; i < n; ++i) {
        int ai = avals[i];
        for (int j = 0; j < n; ++j) {
            int aj = avals[j];
            long long p = power_val(ai, aj);
            recs.push_back({p, i + 1, j + 1});
        }
    }
    sort(recs.begin(), recs.end());
    // Optionally assert uniqueness in debug: omitted for performance

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        // binary search
        int l = 0, r = (int)recs.size() - 1, ans = -1;
        while (l <= r) {
            int m = (l + r) >> 1;
            if (recs[m].p == p) { ans = m; break; }
            if (recs[m].p < p) l = m + 1;
            else r = m - 1;
        }
        if (ans == -1) {
            // Should not happen if construction succeeded; fallback to 1 1
            cout << 1 << ' ' << 1 << '\n';
        } else {
            cout << recs[ans].u << ' ' << recs[ans].v << '\n';
        }
        cout.flush();
    }

    return 0;
}