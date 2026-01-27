#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>
#include <cassert>
#include <cctype>

using namespace std;

class BigInt {
private:
    bool negative;
    vector<int> digits; // little-endian, each digit 0-9

    void normalize() {
        while (digits.size() > 1 && digits.back() == 0)
            digits.pop_back();
        if (digits.size() == 1 && digits[0] == 0)
            negative = false;
    }

    static vector<int> add_vectors(const vector<int>& a, const vector<int>& b) {
        vector<int> res;
        int carry = 0;
        size_t i = 0;
        while (i < a.size() || i < b.size() || carry) {
            int da = i < a.size() ? a[i] : 0;
            int db = i < b.size() ? b[i] : 0;
            int s = da + db + carry;
            res.push_back(s % 10);
            carry = s / 10;
            i++;
        }
        return res;
    }

    static vector<int> sub_vectors(const vector<int>& a, const vector<int>& b) {
        // assumes a >= b
        vector<int> res;
        int borrow = 0;
        for (size_t i = 0; i < a.size(); i++) {
            int d = a[i] - borrow;
            int s = i < b.size() ? b[i] : 0;
            if (d < s) {
                d += 10;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.push_back(d - s);
        }
        // remove leading zeros
        while (res.size() > 1 && res.back() == 0)
            res.pop_back();
        return res;
    }

public:
    BigInt() : negative(false), digits{0} {}

    BigInt(const string& s) {
        from_string(s);
    }

    void from_string(const string& s) {
        digits.clear();
        int start = 0;
        negative = false;
        if (s[0] == '-') {
            negative = true;
            start = 1;
        }
        for (int i = s.size() - 1; i >= start; i--) {
            digits.push_back(s[i] - '0');
        }
        normalize();
    }

    bool is_zero() const {
        return digits.size() == 1 && digits[0] == 0;
    }

    string to_string() const {
        if (is_zero()) return "0";
        string res;
        if (negative) res += '-';
        for (int i = digits.size() - 1; i >= 0; i--)
            res += char(digits[i] + '0');
        return res;
    }

    // absolute value comparison
    bool is_abs_less(const BigInt& other) const {
        if (digits.size() != other.digits.size())
            return digits.size() < other.digits.size();
        for (int i = digits.size() - 1; i >= 0; i--) {
            if (digits[i] != other.digits[i])
                return digits[i] < other.digits[i];
        }
        return false; // equal
    }

    bool is_abs_equal(const BigInt& other) const {
        if (digits.size() != other.digits.size()) return false;
        for (size_t i = 0; i < digits.size(); i++)
            if (digits[i] != other.digits[i]) return false;
        return true;
    }

    // signed comparison
    bool operator<(const BigInt& other) const {
        if (negative != other.negative)
            return negative;
        if (negative)
            return other.is_abs_less(*this);
        else
            return is_abs_less(other);
    }

    bool operator<=(const BigInt& other) const {
        return !(other < *this);
    }

    BigInt abs() const {
        BigInt res = *this;
        res.negative = false;
        return res;
    }

    BigInt operator-() const {
        BigInt res = *this;
        if (!is_zero())
            res.negative = !res.negative;
        return res;
    }

    BigInt operator+(const BigInt& other) const {
        if (negative == other.negative) {
            BigInt res;
            res.negative = negative;
            res.digits = add_vectors(digits, other.digits);
            res.normalize();
            return res;
        } else {
            // signs differ
            if (is_abs_less(other)) {
                // |this| < |other|
                BigInt res;
                res.negative = other.negative;
                res.digits = sub_vectors(other.digits, digits);
                res.normalize();
                return res;
            } else {
                // |this| >= |other|
                BigInt res;
                res.negative = negative;
                res.digits = sub_vectors(digits, other.digits);
                res.normalize();
                return res;
            }
        }
    }

    BigInt operator-(const BigInt& other) const {
        return *this + (-other);
    }
};

pair<vector<int>, BigInt> improve(const vector<int>& b_init, const BigInt& S_init,
                                  const vector<BigInt>& a, const BigInt& W) {
    int n = a.size();
    vector<int> b = b_init;
    BigInt diff = W - S_init;
    BigInt absDiff = diff.abs();
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < n; i++) {
            if (b[i] == 0) {
                BigInt new_diff = diff - a[i];
                BigInt new_abs = new_diff.abs();
                if (new_abs.is_abs_less(absDiff)) {
                    improved = true;
                    b[i] = 1;
                    diff = new_diff;
                    absDiff = new_abs;
                }
            } else {
                BigInt new_diff = diff + a[i];
                BigInt new_abs = new_diff.abs();
                if (new_abs.is_abs_less(absDiff)) {
                    improved = true;
                    b[i] = 0;
                    diff = new_diff;
                    absDiff = new_abs;
                }
            }
        }
    }
    return {b, absDiff};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string W_str;
    cin >> n >> W_str;
    vector<string> a_str(n);
    for (int i = 0; i < n; i++)
        cin >> a_str[i];

    BigInt W(W_str);
    vector<BigInt> a;
    a.reserve(n);
    for (int i = 0; i < n; i++) {
        a.emplace_back(a_str[i]);
    }

    // compute total sum
    BigInt total_sum("0");
    for (const auto& num : a)
        total_sum = total_sum + num;

    if (total_sum <= W) {
        // take all
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << endl;
        return 0;
    }

    // Candidate 1: start from empty, greedy fill
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j) { return a[j] < a[i]; });

    vector<int> b1(n, 0);
    BigInt S1("0");
    for (int i : idx) {
        BigInt newS = S1 + a[i];
        if (newS <= W) {
            b1[i] = 1;
            S1 = newS;
        }
    }
    auto res1 = improve(b1, S1, a, W);
    BigInt absDiff1 = res1.second;

    // Candidate 2: start from all
    vector<int> b2(n, 1);
    BigInt S2 = total_sum;
    auto res2 = improve(b2, S2, a, W);
    BigInt absDiff2 = res2.second;

    vector<int> best_b;
    if (absDiff1.is_abs_less(absDiff2)) {
        best_b = res1.first;
    } else {
        best_b = res2.first;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << best_b[i];
    }
    cout << endl;

    return 0;
}