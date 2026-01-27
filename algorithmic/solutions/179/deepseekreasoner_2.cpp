#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstring>
#include <cstdint>
#include <cmath>
#include <climits>
#include <cassert>
#include <iomanip>
#include <sstream>

using namespace std;

// ---------- BigInt implementation (signed, base 10^9) ----------
class BigInt {
public:
    bool neg;
    vector<int32_t> digits;
    static const int32_t BASE = 1000000000;
    static const int32_t BASE_DIGITS = 9;

    BigInt() : neg(false) {}
    BigInt(const string& s) { from_string(s); }
    BigInt(int64_t x) {
        neg = false;
        if (x < 0) {
            neg = true;
            x = -x;
        }
        digits.clear();
        if (x == 0) digits.push_back(0);
        else while (x > 0) {
            digits.push_back(x % BASE);
            x /= BASE;
        }
    }

    void from_string(const string& s) {
        neg = false;
        digits.clear();
        int start = 0;
        if (s[0] == '-') {
            neg = true;
            start = 1;
        }
        for (int i = (int)s.size() - 1; i >= start; i -= BASE_DIGITS) {
            int32_t digit = 0;
            for (int j = max(start, i - BASE_DIGITS + 1); j <= i; ++j) {
                digit = digit * 10 + (s[j] - '0');
            }
            digits.push_back(digit);
        }
        normalize();
    }

    bool is_zero() const {
        return digits.empty() || (digits.size() == 1 && digits[0] == 0);
    }

    void normalize() {
        while (!digits.empty() && digits.back() == 0) digits.pop_back();
        if (is_zero()) neg = false;
    }

    // absolute value comparison
    bool abs_less(const BigInt& other) const {
        if (digits.size() != other.digits.size())
            return digits.size() < other.digits.size();
        for (int i = (int)digits.size() - 1; i >= 0; --i)
            if (digits[i] != other.digits[i])
                return digits[i] < other.digits[i];
        return false;
    }

    bool operator<(const BigInt& other) const {
        if (neg != other.neg) return neg;
        if (neg) return other.abs_less(*this);
        else return abs_less(other);
    }

    bool operator<=(const BigInt& other) const {
        return !(other < *this);
    }

    bool operator>(const BigInt& other) const {
        return other < *this;
    }

    bool operator>=(const BigInt& other) const {
        return !(*this < other);
    }

    bool operator==(const BigInt& other) const {
        return neg == other.neg && digits == other.digits;
    }

    bool operator!=(const BigInt& other) const {
        return !(*this == other);
    }

    BigInt operator-() const {
        BigInt res = *this;
        res.neg = !neg;
        if (is_zero()) res.neg = false;
        return res;
    }

    BigInt abs() const {
        BigInt res = *this;
        res.neg = false;
        return res;
    }

    BigInt operator+(const BigInt& other) const {
        if (neg == other.neg) {
            BigInt res = add(*this, other);
            res.neg = neg;
            res.normalize();
            return res;
        } else {
            if (abs_less(other)) {
                BigInt res = sub(other, *this);
                res.neg = other.neg;
                res.normalize();
                return res;
            } else {
                BigInt res = sub(*this, other);
                res.neg = neg;
                res.normalize();
                return res;
            }
        }
    }

    BigInt operator-(const BigInt& other) const {
        return *this + (-other);
    }

    // pre-condition: *this >= other, both non-negative
    static BigInt sub(const BigInt& a, const BigInt& b) {
        BigInt res;
        res.digits.resize(a.digits.size());
        int32_t borrow = 0;
        for (size_t i = 0; i < a.digits.size(); ++i) {
            int32_t diff = a.digits[i] - borrow;
            if (i < b.digits.size()) diff -= b.digits[i];
            if (diff < 0) {
                diff += BASE;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.digits[i] = diff;
        }
        res.normalize();
        return res;
    }

    // pre-condition: both non-negative
    static BigInt add(const BigInt& a, const BigInt& b) {
        BigInt res;
        size_t max_len = max(a.digits.size(), b.digits.size());
        res.digits.resize(max_len);
        int32_t carry = 0;
        for (size_t i = 0; i < max_len; ++i) {
            int32_t sum = carry;
            if (i < a.digits.size()) sum += a.digits[i];
            if (i < b.digits.size()) sum += b.digits[i];
            res.digits[i] = sum % BASE;
            carry = sum / BASE;
        }
        if (carry) res.digits.push_back(carry);
        return res;
    }

    string to_string() const {
        if (is_zero()) return "0";
        stringstream ss;
        if (neg) ss << '-';
        ss << digits.back();
        for (int i = (int)digits.size() - 2; i >= 0; --i) {
            ss << setw(BASE_DIGITS) << setfill('0') << digits[i];
        }
        return ss.str();
    }

    // Only for positive numbers, but we assume non-negative everywhere
    BigInt& operator+=(const BigInt& other) {
        *this = *this + other;
        return *this;
    }

    BigInt& operator-=(const BigInt& other) {
        *this = *this - other;
        return *this;
    }
};

// ---------- Main solution ----------
int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string w_str;
    cin >> n >> w_str;
    BigInt W(w_str);

    vector<BigInt> a(n);
    vector<int> idx(n);
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        a[i] = BigInt(s);
        idx[i] = i;
    }

    // Compute M (not needed for output, but for scoring)
    BigInt M = a[0];
    for (int i = 1; i < n; ++i) {
        if (M < a[i]) M = a[i];
    }

    // Greedy: sort indices by a[i] descending
    sort(idx.begin(), idx.end(), [&](int i, int j) {
        return a[j] < a[i];   // a[i] > a[j]
    });

    vector<bool> b(n, false);
    BigInt S(0);
    for (int i : idx) {
        BigInt new_S = S + a[i];
        if (new_S <= W) {
            b[i] = true;
            S = new_S;
        }
    }

    // Local improvement
    const int MAX_ITER = 10;
    vector<bool> included = b;
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        BigInt best_diff = (W - S).abs();
        int best_move = 0; // 0: none, 1: add, 2: remove, 3: swap
        int best_i = -1, best_j = -1;

        // Try adding one excluded element
        for (int j = 0; j < n; ++j) {
            if (included[j]) continue;
            BigInt new_S = S + a[j];
            BigInt diff = (W - new_S).abs();
            if (diff < best_diff) {
                best_diff = diff;
                best_move = 1;
                best_j = j;
            }
        }

        // Try removing one included element
        for (int i = 0; i < n; ++i) {
            if (!included[i]) continue;
            BigInt new_S = S - a[i];
            BigInt diff = (W - new_S).abs();
            if (diff < best_diff) {
                best_diff = diff;
                best_move = 2;
                best_i = i;
            }
        }

        // Try swapping one included with one excluded
        for (int i = 0; i < n; ++i) {
            if (!included[i]) continue;
            for (int j = 0; j < n; ++j) {
                if (included[j]) continue;
                BigInt new_S = S - a[i] + a[j];
                BigInt diff = (W - new_S).abs();
                if (diff < best_diff) {
                    best_diff = diff;
                    best_move = 3;
                    best_i = i;
                    best_j = j;
                }
            }
        }

        if (best_move == 0) break; // no improvement

        // Apply the best move
        if (best_move == 1) { // add
            included[best_j] = true;
            S = S + a[best_j];
            b[best_j] = true;
        } else if (best_move == 2) { // remove
            included[best_i] = false;
            S = S - a[best_i];
            b[best_i] = false;
        } else if (best_move == 3) { // swap
            included[best_i] = false;
            included[best_j] = true;
            S = S - a[best_i] + a[best_j];
            b[best_i] = false;
            b[best_j] = true;
        }

        // Early exit if exact match found
        if (best_diff == BigInt(0)) break;
    }

    // Output the subset
    for (int i = 0; i < n; ++i) {
        cout << (b[i] ? 1 : 0) << (i == n-1 ? '\n' : ' ');
    }

    return 0;
}