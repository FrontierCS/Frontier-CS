#include <bits/stdc++.h>
using namespace std;

struct Big {
    static const uint32_t BASE = 1000000000;
    vector<uint32_t> d; // little-endian base 1e9

    Big() {}
    Big(uint64_t x) {
        if (x == 0) return;
        while (x) { d.push_back(uint32_t(x % BASE)); x /= BASE; }
    }
    bool isZero() const { return d.empty(); }
    void norm() { while (!d.empty() && d.back() == 0) d.pop_back(); }

    static Big fromString(const string &s) {
        Big a;
        int n = (int)s.size();
        for (int i = n; i > 0; i -= 9) {
            int l = max(0, i - 9);
            int len = i - l;
            uint32_t part = 0;
            for (int j = 0; j < len; ++j) {
                part = part * 10 + (s[l + j] - '0');
            }
            a.d.push_back(part);
        }
        a.norm();
        return a;
    }

    static int cmp(const Big &a, const Big &b) {
        if (a.d.size() != b.d.size()) return a.d.size() < b.d.size() ? -1 : 1;
        for (int i = (int)a.d.size() - 1; i >= 0; --i) {
            if (a.d[i] != b.d[i]) return a.d[i] < b.d[i] ? -1 : 1;
        }
        return 0;
    }
    static bool lessThan(const Big &a, const Big &b) { return cmp(a, b) < 0; }
    static bool leq(const Big &a, const Big &b) { return cmp(a, b) <= 0; }

    static Big add(const Big &a, const Big &b) {
        Big c;
        size_t n = max(a.d.size(), b.d.size());
        c.d.resize(n);
        uint64_t carry = 0;
        for (size_t i = 0; i < n; ++i) {
            uint64_t sum = carry;
            if (i < a.d.size()) sum += a.d[i];
            if (i < b.d.size()) sum += b.d[i];
            c.d[i] = uint32_t(sum % BASE);
            carry = sum / BASE;
        }
        if (carry) c.d.push_back(uint32_t(carry));
        return c;
    }
    static void iadd(Big &a, const Big &b) {
        size_t n = max(a.d.size(), b.d.size());
        if (a.d.size() < n) a.d.resize(n, 0);
        uint64_t carry = 0;
        for (size_t i = 0; i < n; ++i) {
            uint64_t sum = carry + a.d[i];
            if (i < b.d.size()) sum += b.d[i];
            a.d[i] = uint32_t(sum % BASE);
            carry = sum / BASE;
        }
        if (carry) a.d.push_back(uint32_t(carry));
    }
    static Big sub(const Big &a, const Big &b) { // assumes a >= b
        Big c;
        c.d.resize(a.d.size());
        int64_t carry = 0;
        for (size_t i = 0; i < a.d.size(); ++i) {
            int64_t cur = (int64_t)a.d[i] - (i < b.d.size() ? b.d[i] : 0) + carry;
            if (cur < 0) { cur += BASE; carry = -1; } else carry = 0;
            c.d[i] = uint32_t(cur);
        }
        c.norm();
        return c;
    }
    static void isub(Big &a, const Big &b) { // assumes a >= b
        int64_t carry = 0;
        for (size_t i = 0; i < a.d.size(); ++i) {
            int64_t cur = (int64_t)a.d[i] - (i < b.d.size() ? b.d[i] : 0) + carry;
            if (cur < 0) { cur += BASE; carry = -1; } else carry = 0;
            a.d[i] = uint32_t(cur);
        }
        a.norm();
    }
    static Big absdiff(const Big &a, const Big &b) {
        int c = cmp(a, b);
        if (c >= 0) return sub(a, b);
        return sub(b, a);
    }
    static Big times2(const Big &a) {
        Big c;
        c.d.resize(a.d.size());
        uint64_t carry = 0;
        for (size_t i = 0; i < a.d.size(); ++i) {
            uint64_t x = (uint64_t)a.d[i] * 2 + carry;
            c.d[i] = uint32_t(x % BASE);
            carry = x / BASE;
        }
        if (carry) c.d.push_back(uint32_t(carry));
        return c;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    string Ws;
    if (!(cin >> n >> Ws)) {
        return 0;
    }
    Big W = Big::fromString(Ws);
    vector<Big> a(n);
    for (int i = 0; i < n; ++i) {
        string s; cin >> s;
        a[i] = Big::fromString(s);
    }

    vector<int> order_orig(n), order_asc(n), order_desc(n);
    iota(order_orig.begin(), order_orig.end(), 0);
    order_asc = order_orig;
    order_desc = order_orig;

    auto cmpBigIdxAsc = [&](int i, int j) {
        int c = Big::cmp(a[i], a[j]);
        if (c != 0) return c < 0;
        return i < j;
    };
    auto cmpBigIdxDesc = [&](int i, int j) {
        int c = Big::cmp(a[i], a[j]);
        if (c != 0) return c > 0;
        return i < j;
    };
    stable_sort(order_asc.begin(), order_asc.end(), cmpBigIdxAsc);
    stable_sort(order_desc.begin(), order_desc.end(), cmpBigIdxDesc);

    auto build_solution = [&](const vector<int> &order, vector<char> &bits, Big &sum_out) {
        bits.assign(n, 0);
        Big sum; // 0
        bool below = true;
        Big rem = W; // valid when below == true

        for (int idx : order) {
            if (!below) break;
            const Big &ai = a[idx];
            int c = Big::cmp(ai, rem);
            if (c <= 0) {
                Big::iadd(sum, ai);
                bits[idx] = 1;
                Big::isub(rem, ai); // rem >= ai
                // below remains true
            } else {
                Big twiceRem = Big::add(rem, rem);
                if (Big::cmp(ai, twiceRem) < 0) {
                    Big::iadd(sum, ai);
                    bits[idx] = 1;
                    below = false; // sum > W
                    break;
                }
            }
        }

        // Local improvement: one add or remove, then optional opposite
        int cmpSW = Big::cmp(sum, W);
        if (cmpSW <= 0) {
            // sum <= W: try add one unselected closest to rem
            rem = Big::sub(W, sum); // rem = W - sum
            if (!rem.isZero()) {
                Big best_d = rem; // current distance
                int best_i = -1;
                for (int i = 0; i < n; ++i) if (!bits[i]) {
                    Big d = Big::absdiff(a[i], rem);
                    if (Big::cmp(d, best_d) < 0) {
                        best_d = std::move(d);
                        best_i = i;
                    }
                }
                if (best_i != -1) {
                    Big::iadd(sum, a[best_i]);
                    bits[best_i] = 1;
                }
            }
            // After add, maybe sum > W: try remove one selected closest to excess
            if (Big::cmp(sum, W) > 0) {
                Big exc = Big::sub(sum, W);
                Big best_d = exc;
                int best_j = -1;
                for (int i = 0; i < n; ++i) if (bits[i]) {
                    Big d = Big::absdiff(a[i], exc);
                    if (Big::cmp(d, best_d) < 0) {
                        best_d = std::move(d);
                        best_j = i;
                    }
                }
                if (best_j != -1) {
                    sum = Big::sub(sum, a[best_j]);
                    bits[best_j] = 0;
                }
            }
        } else {
            // sum > W: try remove one selected closest to excess
            Big exc = Big::sub(sum, W);
            if (!exc.isZero()) {
                Big best_d = exc;
                int best_j = -1;
                for (int i = 0; i < n; ++i) if (bits[i]) {
                    Big d = Big::absdiff(a[i], exc);
                    if (Big::cmp(d, best_d) < 0) {
                        best_d = std::move(d);
                        best_j = i;
                    }
                }
                if (best_j != -1) {
                    sum = Big::sub(sum, a[best_j]);
                    bits[best_j] = 0;
                }
            }
            // After removal, if sum <= W, try add one unselected closest to rem
            if (Big::cmp(sum, W) <= 0) {
                rem = Big::sub(W, sum);
                if (!rem.isZero()) {
                    Big best_d = rem;
                    int best_i = -1;
                    for (int i = 0; i < n; ++i) if (!bits[i]) {
                        Big d = Big::absdiff(a[i], rem);
                        if (Big::cmp(d, best_d) < 0) {
                            best_d = std::move(d);
                            best_i = i;
                        }
                    }
                    if (best_i != -1) {
                        Big::iadd(sum, a[best_i]);
                        bits[best_i] = 1;
                    }
                }
            }
        }

        sum_out = std::move(sum);
    };

    vector<char> best_bits(n, 0);
    Big best_sum; // 0
    Big best_diff = W; // since best_sum=0

    auto try_order = [&](const vector<int> &order) {
        vector<char> bits;
        Big sum;
        build_solution(order, bits, sum);
        Big diff = Big::absdiff(sum, W);
        if (Big::cmp(diff, best_diff) < 0) {
            best_diff = std::move(diff);
            best_bits = std::move(bits);
            best_sum = std::move(sum);
        }
    };

    try_order(order_orig);
    try_order(order_desc);
    try_order(order_asc);

    // Random shuffles within time budget
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    vector<int> order = order_orig;
    auto start = chrono::high_resolution_clock::now();
    const double time_limit_sec = 0.9; // soft limit
    int iterations = 0;
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > time_limit_sec) break;
        shuffle(order.begin(), order.end(), rng);
        try_order(order);
        if (++iterations >= 200) break; // safety cap
    }

    // Output best_bits
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_bits[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}