#include <bits/stdc++.h>
using namespace std;

struct BigInt {
    static const uint32_t BASE = 1000000000;
    vector<uint32_t> d;

    BigInt(long long v = 0) { *this = v; }
    BigInt& operator=(long long v) {
        d.clear();
        if (v == 0) {
            d.push_back(0);
        } else {
            while (v > 0) {
                d.push_back((uint32_t)(v % BASE));
                v /= BASE;
            }
        }
        return *this;
    }
    BigInt(const string &s) { read(s); }

    void trim() {
        while (d.size() > 1 && d.back() == 0) d.pop_back();
        if (d.empty()) d.push_back(0);
    }

    void read(const string &s) {
        d.clear();
        int len = (int)s.size();
        for (int i = len; i > 0; i -= 9) {
            int start = max(0, i - 9);
            int l = i - start;
            uint32_t x = 0;
            for (int j = 0; j < l; ++j)
                x = x * 10 + (s[start + j] - '0');
            d.push_back(x);
        }
        trim();
    }

    static int cmp(const BigInt &a, const BigInt &b) {
        if (a.d.size() != b.d.size())
            return a.d.size() < b.d.size() ? -1 : 1;
        for (int i = (int)a.d.size() - 1; i >= 0; --i) {
            if (a.d[i] != b.d[i])
                return a.d[i] < b.d[i] ? -1 : 1;
        }
        return 0;
    }

    bool operator<(const BigInt &other) const { return cmp(*this, other) < 0; }
    bool operator>(const BigInt &other) const { return cmp(*this, other) > 0; }
    bool operator<=(const BigInt &other) const { return cmp(*this, other) <= 0; }
    bool operator>=(const BigInt &other) const { return cmp(*this, other) >= 0; }
    bool operator==(const BigInt &other) const { return cmp(*this, other) == 0; }
    bool operator!=(const BigInt &other) const { return cmp(*this, other) != 0; }

    bool isZero() const { return d.size() == 1 && d[0] == 0; }

    BigInt& operator+=(const BigInt &other) {
        size_t n = max(d.size(), other.d.size());
        if (d.size() < n) d.resize(n, 0);
        uint64_t carry = 0;
        for (size_t i = 0; i < n; ++i) {
            uint64_t sum = carry + d[i] + (i < other.d.size() ? other.d[i] : 0u);
            d[i] = (uint32_t)(sum % BASE);
            carry = sum / BASE;
        }
        if (carry) d.push_back((uint32_t)carry);
        return *this;
    }

    static BigInt subAbs(const BigInt &a, const BigInt &b) {
        BigInt res;
        res.d.assign(a.d.size(), 0);
        int64_t carry = 0;
        for (size_t i = 0; i < a.d.size(); ++i) {
            int64_t cur = (int64_t)a.d[i] - (i < b.d.size() ? b.d[i] : 0u) - carry;
            if (cur < 0) {
                cur += (int64_t)BASE;
                carry = 1;
            } else {
                carry = 0;
            }
            res.d[i] = (uint32_t)cur;
        }
        res.trim();
        return res;
    }

    static BigInt absDiff(const BigInt &a, const BigInt &b) {
        int c = cmp(a, b);
        if (c >= 0) return subAbs(a, b);
        else return subAbs(b, a);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string Wstr;
    if (!(cin >> n >> Wstr)) return 0;
    BigInt W(Wstr);

    vector<BigInt> a(n);
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        a[i].read(s);
    }

    vector<int> bestChoice(n, 0);
    BigInt zero(0);
    BigInt zeroDiff = BigInt::absDiff(W, zero);
    BigInt bestDiff = zeroDiff;

    // Best single element candidate
    BigInt bestSingleDiff = bestDiff;
    int bestSingleIdx = -1;
    for (int i = 0; i < n; ++i) {
        BigInt d = BigInt::absDiff(a[i], W);
        if (d < bestSingleDiff) {
            bestSingleDiff = d;
            bestSingleIdx = i;
        }
    }
    if (bestSingleIdx != -1 && bestSingleDiff < bestDiff) {
        bestDiff = bestSingleDiff;
        fill(bestChoice.begin(), bestChoice.end(), 0);
        bestChoice[bestSingleIdx] = 1;
    }

    if (!bestDiff.isZero()) {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);

        vector<int> asc = idx;
        sort(asc.begin(), asc.end(), [&](int i, int j) {
            int c = BigInt::cmp(a[i], a[j]);
            if (c != 0) return c < 0;
            return i < j;
        });

        vector<int> desc = asc;
        reverse(desc.begin(), desc.end());

        auto runGreedy = [&](const vector<int> &order) {
            vector<int> choose(n, 0);
            BigInt S(0);
            BigInt diffCur = zeroDiff;

            for (int id : order) {
                BigInt tmp = S;
                tmp += a[id];
                BigInt diff2 = BigInt::absDiff(W, tmp);
                if (diff2 <= diffCur) {
                    S = tmp;
                    diffCur = diff2;
                    choose[id] = 1;
                }
            }
            if (diffCur < bestDiff) {
                bestDiff = diffCur;
                bestChoice.swap(choose);
            }
        };

        runGreedy(asc);
        if (!bestDiff.isZero())
            runGreedy(desc);

        if (!bestDiff.isZero()) {
            mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
            vector<int> randOrder = idx;
            const int RANDOM_RUNS = 8;
            for (int it = 0; it < RANDOM_RUNS && !bestDiff.isZero(); ++it) {
                shuffle(randOrder.begin(), randOrder.end(), rng);
                runGreedy(randOrder);
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << bestChoice[i];
        if (i + 1 < n) cout << ' ';
    }
    cout << '\n';
    return 0;
}