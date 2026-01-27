#include <bits/stdc++.h>
using namespace std;

struct BigInt {
    static const uint32_t base = 1000000000;
    vector<uint32_t> d; // little-endian

    BigInt() {}
    BigInt(uint64_t v) { 
        if (v == 0) return;
        while (v) { d.push_back(v % base); v /= base; }
    }

    static BigInt fromString(const string& s) {
        BigInt x;
        int n = (int)s.size();
        for (int i = n; i > 0; i -= 9) {
            int l = max(0, i - 9);
            int len = i - l;
            uint32_t part = 0;
            for (int j = l; j < i; ++j) {
                part = part * 10 + (s[j] - '0');
            }
            x.d.push_back(part);
        }
        x.trim();
        return x;
    }

    inline void trim() {
        while (!d.empty() && d.back() == 0) d.pop_back();
    }

    static int cmp(const BigInt& a, const BigInt& b) {
        if (a.d.size() != b.d.size()) return (a.d.size() < b.d.size()) ? -1 : 1;
        for (int i = (int)a.d.size() - 1; i >= 0; --i) {
            if (a.d[i] != b.d[i]) return (a.d[i] < b.d[i]) ? -1 : 1;
        }
        return 0;
    }

    bool operator<(const BigInt& other) const { return cmp(*this, other) < 0; }
    bool operator>(const BigInt& other) const { return cmp(*this, other) > 0; }
    bool operator<=(const BigInt& other) const { return cmp(*this, other) <= 0; }
    bool operator>=(const BigInt& other) const { return cmp(*this, other) >= 0; }
    bool operator==(const BigInt& other) const { return cmp(*this, other) == 0; }
    bool operator!=(const BigInt& other) const { return cmp(*this, other) != 0; }

    static BigInt add(const BigInt& a, const BigInt& b) {
        BigInt r;
        uint64_t carry = 0;
        size_t n = max(a.d.size(), b.d.size());
        r.d.resize(n);
        for (size_t i = 0; i < n; ++i) {
            uint64_t av = (i < a.d.size() ? a.d[i] : 0);
            uint64_t bv = (i < b.d.size() ? b.d[i] : 0);
            uint64_t sum = av + bv + carry;
            r.d[i] = (uint32_t)(sum % base);
            carry = sum / base;
        }
        if (carry) r.d.push_back((uint32_t)carry);
        return r;
    }

    BigInt& operator+=(const BigInt& b) {
        uint64_t carry = 0;
        size_t n = max(d.size(), b.d.size());
        if (d.size() < n) d.resize(n, 0);
        for (size_t i = 0; i < n; ++i) {
            uint64_t av = d[i];
            uint64_t bv = (i < b.d.size() ? b.d[i] : 0);
            uint64_t sum = av + bv + carry;
            d[i] = (uint32_t)(sum % base);
            carry = sum / base;
        }
        if (carry) d.push_back((uint32_t)carry);
        return *this;
    }

    static BigInt sub(const BigInt& a, const BigInt& b) { // assumes a >= b
        BigInt r;
        if (cmp(a, b) < 0) return r; // return 0 if invalid, but should not happen
        r.d.resize(a.d.size());
        int64_t carry = 0;
        for (size_t i = 0; i < a.d.size(); ++i) {
            int64_t av = a.d[i];
            int64_t bv = (i < b.d.size() ? b.d[i] : 0);
            int64_t cur = av - bv - carry;
            if (cur < 0) { cur += base; carry = 1; } else carry = 0;
            r.d[i] = (uint32_t)cur;
        }
        r.trim();
        return r;
    }

    BigInt& operator-=(const BigInt& b) { // assumes *this >= b
        int64_t carry = 0;
        for (size_t i = 0; i < d.size(); ++i) {
            int64_t av = d[i];
            int64_t bv = (i < b.d.size() ? b.d[i] : 0);
            int64_t cur = av - bv - carry;
            if (cur < 0) { cur += base; carry = 1; } else carry = 0;
            d[i] = (uint32_t)cur;
        }
        trim();
        return *this;
    }

    static BigInt absDiff(const BigInt& a, const BigInt& b) {
        int c = cmp(a, b);
        if (c >= 0) return sub(a, b);
        else return sub(b, a);
    }

    bool isZero() const { return d.empty(); }
};

static inline BigInt operator+(const BigInt& a, const BigInt& b) { return BigInt::add(a, b); }
static inline BigInt operator-(const BigInt& a, const BigInt& b) { return BigInt::sub(a, b); }

struct StrategyResult {
    vector<uint8_t> sel;
    BigInt sum;
    BigInt diff; // |W - sum|
};

static int lower_bound_idx_by_value(const vector<int>& idxs, const vector<BigInt>& A, const BigInt& key) {
    int l = 0, r = (int)idxs.size();
    while (l < r) {
        int m = (l + r) >> 1;
        if (A[idxs[m]] < key) l = m + 1;
        else r = m;
    }
    return l;
}

static StrategyResult run_greedy_and_improve(const vector<BigInt>& A, const BigInt& W, const vector<int>& order, mt19937& rng) {
    int n = (int)A.size();
    vector<uint8_t> sel(n, 0);
    BigInt S; // zero
    // Greedy: include if S + A[i] <= W
    for (int idx : order) {
        BigInt ns = S + A[idx];
        if (BigInt::cmp(ns, W) <= 0) {
            S = std::move(ns);
            sel[idx] = 1;
        }
    }

    auto currentDiff = BigInt::absDiff(S, W);
    // Attempt local improvements: a few small steps
    for (int outer = 0; outer < 2; ++outer) {
        // Single addition: try adding one not-selected element that minimizes |W - (S + a[i])|
        int bestAdd = -1;
        BigInt bestAddDiff = currentDiff; // need strictly less
        for (int i = 0; i < n; ++i) if (!sel[i]) {
            BigInt ns = S + A[i];
            BigInt d = BigInt::absDiff(ns, W);
            if (d < bestAddDiff) {
                bestAddDiff = d;
                bestAdd = i;
                if (bestAddDiff.isZero()) break;
            }
        }
        if (bestAdd != -1) {
            S += A[bestAdd];
            sel[bestAdd] = 1;
            currentDiff = std::move(bestAddDiff);
        } else {
            break;
        }
    }

    // Build included / not-included lists
    vector<int> inc, notinc;
    inc.reserve(n); notinc.reserve(n);
    for (int i = 0; i < n; ++i) (sel[i] ? inc : notinc).push_back(i);

    // Sort notinc ascending by value for binary searches and two-pointer
    sort(notinc.begin(), notinc.end(), [&](int i, int j){ return A[i] < A[j]; });

    // Try a single swap (remove one included and add one not-included)
    if (!inc.empty() && !notinc.empty()) {
        bool isOver = BigInt::cmp(S, W) > 0;
        BigInt D = BigInt::absDiff(S, W);
        int bestX = -1, bestY = -1;
        BigInt bestSwapDiff = currentDiff;

        for (int xi : inc) {
            bool Tneg = false;
            BigInt T;
            if (!isOver) {
                // T = D + A[xi]
                T = D + A[xi];
            } else {
                // T = A[xi] - D (could be negative)
                if (A[xi] >= D) {
                    T = A[xi] - D;
                } else {
                    Tneg = true;
                    T = D - A[xi]; // |negative|
                }
            }

            // Find y ~ T
            if (Tneg) {
                // best y is minimal value
                int yi = notinc[0];
                BigInt ns = (S - A[xi]) + A[yi];
                BigInt d = BigInt::absDiff(ns, W);
                if (d < bestSwapDiff) {
                    bestSwapDiff = d;
                    bestX = xi; bestY = yi;
                }
            } else {
                int pos = lower_bound_idx_by_value(notinc, A, T);
                // candidate at pos
                if (pos < (int)notinc.size()) {
                    int yi = notinc[pos];
                    BigInt ns = (S - A[xi]) + A[yi];
                    BigInt d = BigInt::absDiff(ns, W);
                    if (d < bestSwapDiff) {
                        bestSwapDiff = d;
                        bestX = xi; bestY = yi;
                    }
                }
                if (pos - 1 >= 0) {
                    int yi = notinc[pos - 1];
                    BigInt ns = (S - A[xi]) + A[yi];
                    BigInt d = BigInt::absDiff(ns, W);
                    if (d < bestSwapDiff) {
                        bestSwapDiff = d;
                        bestX = xi; bestY = yi;
                    }
                }
            }
        }
        if (bestX != -1) {
            sel[bestX] = 0;
            sel[bestY] = 1;
            S = (S - A[bestX]) + A[bestY];
            currentDiff = std::move(bestSwapDiff);

            // Rebuild lists for the next phase
            inc.clear(); notinc.clear();
            for (int i = 0; i < n; ++i) (sel[i] ? inc : notinc).push_back(i);
            sort(notinc.begin(), notinc.end(), [&](int i, int j){ return A[i] < A[j]; });
        }
    }

    // If under-sum, try adding two not-included elements using two-pointer
    if (BigInt::cmp(S, W) < 0 && (int)notinc.size() >= 2) {
        BigInt target = W - S;
        int i = 0, j = (int)notinc.size() - 1;
        int bestI = -1, bestJ = -1;
        BigInt bestPairDiff = currentDiff;
        while (i < j) {
            const BigInt& v1 = A[notinc[i]];
            const BigInt& v2 = A[notinc[j]];
            BigInt sum = v1 + v2;
            BigInt d = BigInt::absDiff(target, sum);
            if (d < bestPairDiff) {
                bestPairDiff = d;
                bestI = notinc[i];
                bestJ = notinc[j];
                if (bestPairDiff.isZero()) break;
            }
            int c = BigInt::cmp(sum, target);
            if (c < 0) ++i;
            else if (c > 0) --j;
            else break;
        }
        if (bestI != -1) {
            sel[bestI] = 1;
            sel[bestJ] = 1;
            S += A[bestI];
            S += A[bestJ];
            currentDiff = std::move(bestPairDiff);
        }
    } else if (BigInt::cmp(S, W) > 0 && !inc.empty()) {
        // If over-sum, try removing one included element
        int bestRem = -1;
        BigInt bestRemDiff = currentDiff;
        for (int xi : inc) {
            BigInt ns = S - A[xi];
            BigInt d = BigInt::absDiff(ns, W);
            if (d < bestRemDiff) {
                bestRemDiff = d;
                bestRem = xi;
            }
        }
        if (bestRem != -1) {
            sel[bestRem] = 0;
            S -= A[bestRem];
            currentDiff = std::move(bestRemDiff);
        }
    }

    StrategyResult res;
    res.sel = std::move(sel);
    res.sum = std::move(S);
    res.diff = std::move(currentDiff);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    string Wstr;
    if (!(cin >> n >> Wstr)) {
        return 0;
    }
    BigInt W = BigInt::fromString(Wstr);
    vector<BigInt> A(n);
    for (int i = 0; i < n; ++i) {
        string s; cin >> s;
        A[i] = BigInt::fromString(s);
    }

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    // Prepare different orders
    vector<vector<int>> orders;

    // Descending
    vector<int> desc = idx;
    sort(desc.begin(), desc.end(), [&](int i, int j){ return BigInt::cmp(A[i], A[j]) > 0; });
    orders.push_back(desc);

    // Ascending
    vector<int> asc = idx;
    sort(asc.begin(), asc.end(), [&](int i, int j){ return A[i] < A[j]; });
    orders.push_back(asc);

    // Random shuffles
    mt19937 rng(123456789);
    for (int t = 0; t < 3; ++t) {
        vector<int> rnd = idx;
        shuffle(rnd.begin(), rnd.end(), rng);
        orders.push_back(std::move(rnd));
    }

    // Run strategies and keep the best
    StrategyResult best;
    best.sel.assign(n, 0);
    best.sum = BigInt(0);
    best.diff = BigInt::absDiff(best.sum, W); // initially |W - 0| = W

    for (auto& ord : orders) {
        StrategyResult cur = run_greedy_and_improve(A, W, ord, rng);
        if (cur.diff < best.diff) {
            best = std::move(cur);
            if (best.diff.isZero()) break;
        }
    }

    // Output selection vector
    for (int i = 0; i < n; ++i) {
        cout << (int)best.sel[i] << (i + 1 == n ? '\n' : ' ');
    }
    return 0;
}