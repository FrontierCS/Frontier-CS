#include <bits/stdc++.h>
using namespace std;

struct Entry {
    unsigned long long key;
    int u;
    int v;
};

static inline unsigned long long computeC(int a, int b, int c, int d) {
    using i128 = __int128_t;
    i128 A = a, B = b, Cc = c, D = d;
    i128 within = max(a, c) + max(b, d);
    i128 x2o_union = A*B + Cc*D - (i128)min(a, c)*(i128)min(b, d);
    i128 o2x = B*Cc;
    i128 twoB = A*B*Cc + B*Cc*D;
    i128 threeB = A*B*Cc*D;
    i128 total = within + x2o_union + o2x + twoB + threeB;
    return (unsigned long long) total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Choose maximum per-word length to control I/O size while keeping range large
    int S = min(30 * n, 6000);
    int L = max(1, S / 4);
    int U = max(L, S / 2);

    vector<int> A(n), B(n);
    vector<Entry> entries;
    entries.reserve((size_t)n * (size_t)n);

    std::mt19937_64 rng((unsigned long long)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto attempt = [&]() -> bool {
        unordered_set<unsigned long long> used;
        used.reserve(n * 2);
        for (int i = 0; i < n; ++i) {
            int a, b;
            while (true) {
                a = L + (int)(rng() % (U - L + 1));
                b = L + (int)(rng() % (U - L + 1));
                if ((long long)a + b > S) continue; // ensure sum <= S
                unsigned long long key = ((unsigned long long)a << 32) ^ (unsigned long long)b;
                if (used.insert(key).second) break;
            }
            A[i] = a;
            B[i] = b;
        }
        entries.clear();
        entries.reserve((size_t)n * (size_t)n);
        for (int i = 0; i < n; ++i) {
            int a = A[i], b = B[i];
            for (int j = 0; j < n; ++j) {
                int c = A[j], d = B[j];
                unsigned long long k = computeC(a, b, c, d);
                entries.push_back({k, i + 1, j + 1});
            }
        }
        sort(entries.begin(), entries.end(), [](const Entry &x, const Entry &y){
            return x.key < y.key;
        });
        for (size_t i = 1; i < entries.size(); ++i) {
            if (entries[i].key == entries[i - 1].key) {
                if (entries[i].u != entries[i - 1].u || entries[i].v != entries[i - 1].v) {
                    return false; // collision across different pairs
                }
            }
        }
        return true;
    };

    // Try multiple attempts to avoid collisions; probability of needing more than one is tiny
    const int MAX_ATTEMPTS = 5;
    bool ok = false;
    for (int t = 0; t < MAX_ATTEMPTS; ++t) {
        if (attempt()) { ok = true; break; }
    }
    if (!ok) {
        // Fallback deterministic construction (still likely collision-free with these ranges)
        // Ensure uniqueness by simple deterministic but varied pairs
        unordered_set<unsigned long long> used;
        used.reserve(n * 2);
        for (int i = 0; i < n; ++i) {
            int base = L + (i % (U - L + 1));
            int a = base;
            int b = min(U, S - a);
            if (b < L) b = L;
            // adjust to ensure unique
            while (true) {
                unsigned long long key = ((unsigned long long)a << 32) ^ (unsigned long long)b;
                if (used.insert(key).second) break;
                if (a < U) ++a;
                else if (b > L) --b;
                else { // as a last resort, random tweak within bounds
                    a = L + (int)(rng() % (U - L + 1));
                    b = L + (int)(rng() % (U - L + 1));
                    if (a + b > S) { b = S - a; if (b < L) b = L; }
                }
            }
            A[i] = a;
            B[i] = b;
        }
        entries.clear();
        entries.reserve((size_t)n * (size_t)n);
        for (int i = 0; i < n; ++i) {
            int a = A[i], b = B[i];
            for (int j = 0; j < n; ++j) {
                int c = A[j], d = B[j];
                unsigned long long k = computeC(a, b, c, d);
                entries.push_back({k, i + 1, j + 1});
            }
        }
        sort(entries.begin(), entries.end(), [](const Entry &x, const Entry &y){
            return x.key < y.key;
        });
        // No guarantee collision-free; we proceed anyway
    }

    // Output the strings
    string s;
    for (int i = 0; i < n; ++i) {
        s.clear();
        s.reserve((size_t)A[i] + (size_t)B[i]);
        s.append(A[i], 'X');
        s.append(B[i], 'O');
        cout << s << '\n';
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;

    // For binary search, entries are already sorted by key
    for (int qi = 0; qi < q; ++qi) {
        unsigned long long p;
        cin >> p;
        auto it = lower_bound(entries.begin(), entries.end(), p, [](const Entry &e, const unsigned long long val){
            return e.key < val;
        });
        if (it != entries.end() && it->key == p) {
            cout << it->u << ' ' << it->v << '\n';
        } else {
            // Should not happen if judge generated p from our words; fallback to something
            // Output a default valid pair
            cout << 1 << ' ' << 1 << '\n';
        }
        cout.flush();
    }

    return 0;
}