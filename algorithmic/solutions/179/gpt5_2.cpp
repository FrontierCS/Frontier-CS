#include <bits/stdc++.h>
using namespace std;

struct Big {
    static const uint32_t BASE = 1000000000;
    vector<uint32_t> d; // little-endian

    Big() {}
    Big(uint64_t v) { 
        if (v == 0) return;
        while (v) { d.push_back(uint32_t(v % BASE)); v /= BASE; }
    }

    static Big fromString(const string &s) {
        Big x;
        int n = (int)s.size();
        for (int i = n; i > 0; i -= 9) {
            int l = max(0, i - 9);
            int len = i - l;
            uint32_t block = 0;
            for (int j = 0; j < len; ++j) block = block * 10 + (s[l + j] - '0');
            x.d.push_back(block);
        }
        x.norm();
        return x;
    }

    void norm() {
        while (!d.empty() && d.back() == 0) d.pop_back();
    }

    bool isZero() const { return d.empty(); }

    static int cmp(const Big &a, const Big &b) {
        if (a.d.size() != b.d.size()) return (a.d.size() < b.d.size()) ? -1 : 1;
        for (int i = (int)a.d.size() - 1; i >= 0; --i) {
            if (a.d[i] != b.d[i]) return (a.d[i] < b.d[i]) ? -1 : 1;
        }
        return 0;
    }

    static void add(const Big &a, const Big &b, Big &out) {
        size_t n = max(a.d.size(), b.d.size());
        out.d.resize(n);
        uint64_t carry = 0;
        for (size_t i = 0; i < n; ++i) {
            uint64_t av = (i < a.d.size() ? a.d[i] : 0);
            uint64_t bv = (i < b.d.size() ? b.d[i] : 0);
            uint64_t sum = av + bv + carry;
            out.d[i] = (uint32_t)(sum % BASE);
            carry = sum / BASE;
        }
        if (carry) out.d.push_back((uint32_t)carry);
    }

    static void addTo(Big &a, const Big &b) {
        size_t n = max(a.d.size(), b.d.size());
        if (a.d.size() < n) a.d.resize(n, 0);
        uint64_t carry = 0;
        for (size_t i = 0; i < n; ++i) {
            uint64_t av = a.d[i];
            uint64_t bv = (i < b.d.size() ? b.d[i] : 0);
            uint64_t sum = av + bv + carry;
            a.d[i] = (uint32_t)(sum % BASE);
            carry = sum / BASE;
        }
        if (carry) a.d.push_back((uint32_t)carry);
    }

    // assumes a >= b
    static void sub(const Big &a, const Big &b, Big &out) {
        out.d.resize(a.d.size());
        int64_t carry = 0;
        for (size_t i = 0; i < a.d.size(); ++i) {
            int64_t av = a.d[i];
            int64_t bv = (i < b.d.size() ? b.d[i] : 0);
            int64_t cur = av - bv - carry;
            if (cur < 0) { cur += BASE; carry = 1; } else carry = 0;
            out.d[i] = (uint32_t)cur;
        }
        out.norm();
    }

    static void subFrom(Big &a, const Big &b) { // a >= b
        int64_t carry = 0;
        for (size_t i = 0; i < a.d.size(); ++i) {
            int64_t av = a.d[i];
            int64_t bv = (i < b.d.size() ? b.d[i] : 0);
            int64_t cur = av - bv - carry;
            if (cur < 0) { cur += BASE; carry = 1; } else carry = 0;
            a.d[i] = (uint32_t)cur;
        }
        a.norm();
    }

    static void absdiff(const Big &a, const Big &b, Big &out) {
        int c = cmp(a, b);
        if (c >= 0) sub(a, b, out);
        else sub(b, a, out);
    }
};

struct Solver {
    int n;
    Big W;
    vector<Big> a;

    vector<char> best;
    Big bestDiff;

    Big temp; // reusable temp big

    Solver(int n_, Big W_, vector<Big> a_) : n(n_), W(std::move(W_)), a(std::move(a_)) {
        best.assign(n, 0);
        bestDiff = W; // empty set sum = 0 -> diff = W
    }

    inline bool lessThan(const Big &x, const Big &y) {
        return Big::cmp(x, y) < 0;
    }

    void try_order(const vector<int> &order, int improv_passes = 2) {
        vector<char> take(n, 0);
        Big D = W; // current |W - S|, starts at W
        bool sLEw = true; // S <= W initially

        // Greedy pass
        for (int id : order) {
            const Big &v = a[id];
            if (sLEw) {
                Big::absdiff(D, v, temp);
                if (lessThan(temp, D)) {
                    // Accept: S += v
                    if (Big::cmp(D, v) >= 0) {
                        Big::subFrom(D, v); // D = D - v
                        // sLEw stays true
                    } else {
                        Big::sub(v, D, D); // D = v - D
                        sLEw = false;
                    }
                    take[id] = 1;
                }
            } else {
                Big::add(D, v, temp);
                if (lessThan(temp, D)) {
                    // Can't happen since D+v >= D
                    // but keep for completeness
                    Big::addTo(D, v); // D = D + v
                    // sLEw stays false
                    take[id] = 1;
                }
            }
        }

        // Improvement passes
        for (int pass = 0; pass < improv_passes; ++pass) {
            bool improved = false;

            // Scan all items
            for (int i = 0; i < n; ++i) {
                const Big &v = a[i];
                if (take[i]) {
                    // Try removal
                    if (sLEw) {
                        Big::add(D, v, temp);
                        if (lessThan(temp, D)) {
                            // Accept: removing while S<=W always increases D, so won't happen
                            Big::addTo(D, v);
                            // sLEw stays true
                            take[i] = 0;
                            improved = true;
                        }
                    } else {
                        Big::absdiff(D, v, temp);
                        if (lessThan(temp, D)) {
                            // Accept removal: S -= v
                            int c = Big::cmp(D, v);
                            if (c > 0) {
                                Big::subFrom(D, v); // D = D - v
                                // sLEw stays false
                            } else if (c == 0) {
                                D = Big(0);
                                sLEw = true; // now S == W
                            } else {
                                Big::sub(v, D, D); // D = v - D
                                sLEw = true; // crossed below/equal W
                            }
                            take[i] = 0;
                            improved = true;
                        }
                    }
                } else {
                    // Try addition
                    if (sLEw) {
                        Big::absdiff(D, v, temp);
                        if (lessThan(temp, D)) {
                            // Accept add
                            if (Big::cmp(D, v) >= 0) {
                                Big::subFrom(D, v);
                            } else {
                                Big::sub(v, D, D);
                                sLEw = false;
                            }
                            take[i] = 1;
                            improved = true;
                        }
                    } else {
                        Big::add(D, v, temp);
                        if (lessThan(temp, D)) {
                            // Won't happen since D+v >= D
                            Big::addTo(D, v);
                            take[i] = 1;
                            improved = true;
                        }
                    }
                }
            }

            if (!improved) break;
        }

        // Compare with best
        if (lessThan(D, bestDiff)) {
            bestDiff = D;
            best = take;
        }
    }

    vector<char> solve() {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);

        // Ascending order
        vector<int> asc = idx;
        stable_sort(asc.begin(), asc.end(), [&](int i, int j){
            return Big::cmp(a[i], a[j]) < 0;
        });
        try_order(asc, 2);

        // Descending order
        vector<int> desc = asc;
        reverse(desc.begin(), desc.end());
        try_order(desc, 2);

        // Random runs
        std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);
        int runs = 12;
        for (int r = 0; r < runs; ++r) {
            vector<int> rnd = idx;
            shuffle(rnd.begin(), rnd.end(), rng);
            try_order(rnd, 1);
        }

        return best;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string Wstr;
    if (!(cin >> n >> Wstr)) {
        return 0;
    }
    Big W = Big::fromString(Wstr);
    vector<Big> a(n);
    for (int i = 0; i < n; ++i) {
        string s; 
        cin >> s;
        a[i] = Big::fromString(s);
    }

    Solver solver(n, W, a);
    vector<char> ans = solver.solve();

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (ans[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}