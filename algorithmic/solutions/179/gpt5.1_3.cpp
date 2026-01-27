#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <string>

using namespace std;

struct BigInt {
    static const int base = 1000000000;
    vector<int> a; // little-endian, base 1e9

    BigInt(long long v = 0) { *this = v; }

    BigInt& operator=(long long v) {
        a.clear();
        if (v == 0) return *this;
        while (v > 0) {
            a.push_back((int)(v % base));
            v /= base;
        }
        return *this;
    }

    BigInt(const string& s) { read(s); }

    void trim() {
        while (!a.empty() && a.back() == 0) a.pop_back();
    }

    bool isZero() const {
        return a.empty();
    }

    void read(const string& s) {
        a.clear();
        int len = (int)s.size();
        for (int i = len; i > 0; i -= 9) {
            int x = 0;
            int l = max(0, i - 9);
            for (int j = l; j < i; ++j)
                x = x * 10 + (s[j] - '0');
            a.push_back(x);
        }
        trim();
    }

    int compare(const BigInt& v) const {
        if (a.size() != v.a.size())
            return a.size() < v.a.size() ? -1 : 1;
        for (int i = (int)a.size() - 1; i >= 0; --i) {
            if (a[i] != v.a[i])
                return a[i] < v.a[i] ? -1 : 1;
        }
        return 0;
    }

    bool operator<(const BigInt& v) const { return compare(v) < 0; }
    bool operator>(const BigInt& v) const { return compare(v) > 0; }
    bool operator<=(const BigInt& v) const { return compare(v) <= 0; }
    bool operator>=(const BigInt& v) const { return compare(v) >= 0; }
    bool operator==(const BigInt& v) const { return compare(v) == 0; }
    bool operator!=(const BigInt& v) const { return compare(v) != 0; }

    BigInt& operator+=(const BigInt& v) {
        int carry = 0;
        int n = (int)max(a.size(), v.a.size());
        if ((int)a.size() < n) a.resize(n, 0);
        for (int i = 0; i < n; ++i) {
            long long sum = (long long)a[i] + (i < (int)v.a.size() ? v.a[i] : 0) + carry;
            a[i] = (int)(sum % base);
            carry = (int)(sum / base);
        }
        if (carry) a.push_back(carry);
        return *this;
    }

    BigInt& operator-=(const BigInt& v) {
        // assume *this >= v
        int carry = 0;
        for (int i = 0; i < (int)v.a.size() || carry; ++i) {
            long long cur = (long long)a[i] - (i < (int)v.a.size() ? v.a[i] : 0) - carry;
            if (cur < 0) {
                cur += base;
                carry = 1;
            } else {
                carry = 0;
            }
            a[i] = (int)cur;
        }
        trim();
        return *this;
    }

    friend BigInt operator+(BigInt lhs, const BigInt& rhs) {
        lhs += rhs;
        return lhs;
    }

    friend BigInt operator-(BigInt lhs, const BigInt& rhs) {
        lhs -= rhs;
        return lhs;
    }
};

BigInt absdiff(const BigInt& x, const BigInt& y) {
    if (x >= y) return x - y;
    else return y - x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string sW;
    if (!(cin >> n >> sW)) {
        return 0;
    }
    BigInt W(sW);

    vector<BigInt> a;
    a.reserve(n);
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        a.emplace_back(s);
    }

    vector<int> b(n, 0);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    BigInt S(0);
    BigInt dist = W; // since S = 0

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    int max_passes = 4;
    for (int pass = 0; pass < max_passes; ++pass) {
        bool improved = false;
        shuffle(order.begin(), order.end(), rng);
        for (int idx : order) {
            BigInt candidate = S;
            if (b[idx] == 0) candidate += a[idx];
            else candidate -= a[idx];
            BigInt ndist = absdiff(W, candidate);
            if (ndist < dist) {
                S = candidate;
                dist = ndist;
                b[idx] ^= 1;
                improved = true;
            }
        }
        if (!improved) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << b[i];
    }
    cout << '\n';

    return 0;
}