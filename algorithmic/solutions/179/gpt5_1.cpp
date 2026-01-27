#include <bits/stdc++.h>
using namespace std;

struct BigInt {
    static const uint32_t BASE = 1000000000; // 1e9
    vector<uint32_t> d; // little-endian

    BigInt() {}
    BigInt(uint64_t v) { 
        if (v == 0) d.push_back(0);
        else {
            while (v) {
                d.push_back(uint32_t(v % BASE));
                v /= BASE;
            }
        }
    }
    BigInt(const string& s) { fromString(s); }

    void trim() {
        while (d.size() > 1 && d.back() == 0) d.pop_back();
        if (d.empty()) d.push_back(0);
    }

    void fromString(const string& s_) {
        string s = s_;
        size_t pos = 0;
        while (pos < s.size() && s[pos] == '+') pos++;
        while (pos < s.size() && s[pos] == '0') pos++;
        if (pos == s.size()) { d = {0}; return; }
        d.clear();
        for (int i = (int)s.size() - 1; i >= (int)pos; i -= 9) {
            int start = max((int)pos, i - 8);
            int len = i - start + 1;
            uint32_t block = 0;
            for (int j = 0; j < len; ++j) {
                block = block * 10 + (s[start + j] - '0');
            }
            d.push_back(block);
        }
        trim();
    }

    string toString() const {
        if (d.empty()) return "0";
        string s = to_string(d.back());
        char buf[16];
        for (int i = (int)d.size() - 2; i >= 0; --i) {
            snprintf(buf, sizeof(buf), "%09u", d[i]);
            s += buf;
        }
        return s;
    }

    int cmp(const BigInt& o) const {
        if (d.size() != o.d.size()) return d.size() < o.d.size() ? -1 : 1;
        for (int i = (int)d.size() - 1; i >= 0; --i) {
            if (d[i] != o.d[i]) return d[i] < o.d[i] ? -1 : 1;
        }
        return 0;
    }
    bool operator<(const BigInt& o) const { return cmp(o) < 0; }
    bool operator>(const BigInt& o) const { return cmp(o) > 0; }
    bool operator<=(const BigInt& o) const { return cmp(o) <= 0; }
    bool operator>=(const BigInt& o) const { return cmp(o) >= 0; }
    bool operator==(const BigInt& o) const { return cmp(o) == 0; }
    bool operator!=(const BigInt& o) const { return cmp(o) != 0; }

    static BigInt add(const BigInt& a, const BigInt& b) {
        BigInt r;
        const size_t n = max(a.d.size(), b.d.size());
        r.d.resize(n + 1, 0);
        uint64_t carry = 0;
        size_t i = 0;
        for (; i < n; ++i) {
            uint64_t sum = carry;
            if (i < a.d.size()) sum += a.d[i];
            if (i < b.d.size()) sum += b.d[i];
            r.d[i] = (uint32_t)(sum % BASE);
            carry = sum / BASE;
        }
        if (carry) r.d[i++] = (uint32_t)carry;
        r.d.resize(i);
        r.trim();
        return r;
    }

    static BigInt sub(const BigInt& a, const BigInt& b) { // assume a >= b
        BigInt r;
        r.d.resize(a.d.size(), 0);
        int64_t carry = 0;
        size_t i = 0;
        for (; i < a.d.size(); ++i) {
            int64_t cur = (int64_t)a.d[i] - (i < b.d.size() ? b.d[i] : 0) + carry;
            if (cur < 0) {
                cur += BASE;
                carry = -1;
            } else {
                carry = 0;
            }
            r.d[i] = (uint32_t)cur;
        }
        r.trim();
        return r;
    }

    BigInt& operator+=(const BigInt& o) { *this = add(*this, o); return *this; }
    BigInt& operator-=(const BigInt& o) { *this = sub(*this, o); return *this; }

    static BigInt absDiff(const BigInt& a, const BigInt& b) {
        if (a >= b) return sub(a, b);
        else return sub(b, a);
    }

    bool isZero() const { return d.size() == 1 && d[0] == 0; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string Wstr;
    if (!(cin >> n >> Wstr)) {
        return 0;
    }
    BigInt W(Wstr);
    vector<BigInt> a(n);
    for (int i = 0; i < n; ++i) {
        string s; cin >> s;
        a[i] = BigInt(s);
    }

    // Initialize best solution as all zeros
    vector<char> best_sel(n, 0);
    BigInt best_sum(0);
    BigInt best_diff = BigInt::absDiff(W, best_sum);

    auto consider_solution = [&](const vector<char>& sel, const BigInt& sum) {
        BigInt diff = BigInt::absDiff(W, sum);
        if (diff < best_diff) {
            best_diff = diff;
            best_sel = sel;
            best_sum = sum;
        }
    };

    // Candidate: single best item
    {
        int best_idx = -1;
        BigInt best_local_diff = BigInt::absDiff(W, BigInt(0)); // same as W
        for (int i = 0; i < n; ++i) {
            BigInt diff = BigInt::absDiff(W, a[i]);
            if (diff < best_local_diff) {
                best_local_diff = diff;
                best_idx = i;
            }
        }
        if (best_idx != -1) {
            vector<char> sel(n, 0);
            sel[best_idx] = 1;
            consider_solution(sel, a[best_idx]);
        }
    }

    // Prepare index orderings
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    vector<int> idx_desc = idx, idx_asc = idx;
    sort(idx_desc.begin(), idx_desc.end(), [&](int i, int j) {
        int c = a[i].cmp(a[j]);
        if (c != 0) return c > 0;
        return i < j;
    });
    sort(idx_asc.begin(), idx_asc.end(), [&](int i, int j) {
        int c = a[i].cmp(a[j]);
        if (c != 0) return c < 0;
        return i < j;
    });

    auto run_greedy = [&](const vector<int>& order) {
        vector<char> sel(n, 0);
        BigInt S(0);
        BigInt curr_diff = BigInt::absDiff(W, S);
        for (int id : order) {
            BigInt trial = BigInt::add(S, a[id]);
            BigInt new_diff = BigInt::absDiff(W, trial);
            if (new_diff <= curr_diff) {
                sel[id] = 1;
                S = std::move(trial);
                curr_diff = std::move(new_diff);
                if (curr_diff.isZero()) break;
            }
        }
        // Local improvement: 1-flip hill climbing, limited iterations
        int max_iters = 2;
        for (int it = 0; it < max_iters; ++it) {
            bool any = false;
            for (int i = 0; i < n; ++i) {
                BigInt trial;
                if (sel[i]) {
                    // try removing
                    if (S >= a[i]) {
                        trial = BigInt::sub(S, a[i]);
                    } else {
                        // Should not happen since S is sum of selected includes a[i], but guard anyway
                        continue;
                    }
                } else {
                    // try adding
                    trial = BigInt::add(S, a[i]);
                }
                BigInt new_diff = BigInt::absDiff(W, trial);
                if (new_diff < curr_diff) {
                    sel[i] = !sel[i];
                    S = std::move(trial);
                    curr_diff = std::move(new_diff);
                    any = true;
                    if (curr_diff.isZero()) break;
                }
            }
            if (!any || curr_diff.isZero()) break;
        }
        consider_solution(sel, S);
    };

    run_greedy(idx_desc);
    run_greedy(idx_asc);

    // A couple of randomized greedy runs
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int r = 0; r < 2; ++r) {
        vector<int> order = idx;
        shuffle(order.begin(), order.end(), rng);
        run_greedy(order);
    }

    // Output best selection
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << int(best_sel[i]);
    }
    cout << '\n';

    return 0;
}