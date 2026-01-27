#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

class BigInt {
    vector<int> digits; // least significant first
public:
    BigInt() {}
    BigInt(const string& s) {
        digits.clear();
        for (int i = s.size() - 1; i >= 0; i--) {
            digits.push_back(s[i] - '0');
        }
        normalize();
    }
    BigInt(int x) {
        digits.clear();
        if (x == 0) digits.push_back(0);
        while (x > 0) {
            digits.push_back(x % 10);
            x /= 10;
        }
    }
    void normalize() {
        while (digits.size() > 1 && digits.back() == 0) {
            digits.pop_back();
        }
    }
    bool isZero() const {
        return digits.size() == 1 && digits[0] == 0;
    }
    BigInt operator+(const BigInt& other) const {
        BigInt res;
        int carry = 0;
        int maxlen = max(digits.size(), other.digits.size());
        res.digits.assign(maxlen, 0);
        for (int i = 0; i < maxlen; i++) {
            int d1 = i < digits.size() ? digits[i] : 0;
            int d2 = i < other.digits.size() ? other.digits[i] : 0;
            int sum = d1 + d2 + carry;
            res.digits[i] = sum % 10;
            carry = sum / 10;
        }
        if (carry) res.digits.push_back(carry);
        return res;
    }
    // assumes *this >= other
    BigInt operator-(const BigInt& other) const {
        BigInt res;
        int borrow = 0;
        res.digits.assign(digits.size(), 0);
        for (int i = 0; i < digits.size(); i++) {
            int d1 = digits[i] - borrow;
            int d2 = i < other.digits.size() ? other.digits[i] : 0;
            if (d1 < d2) {
                d1 += 10;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.digits[i] = d1 - d2;
        }
        res.normalize();
        return res;
    }
    bool operator<(const BigInt& other) const {
        if (digits.size() != other.digits.size()) {
            return digits.size() < other.digits.size();
        }
        for (int i = digits.size() - 1; i >= 0; i--) {
            if (digits[i] != other.digits[i]) {
                return digits[i] < other.digits[i];
            }
        }
        return false;
    }
    bool operator<=(const BigInt& other) const {
        if (digits.size() != other.digits.size()) {
            return digits.size() < other.digits.size();
        }
        for (int i = digits.size() - 1; i >= 0; i--) {
            if (digits[i] != other.digits[i]) {
                return digits[i] < other.digits[i];
            }
        }
        return true;
    }
    bool operator==(const BigInt& other) const {
        return digits == other.digits;
    }
    string toString() const {
        if (digits.empty()) return "0";
        string s;
        for (int i = digits.size() - 1; i >= 0; i--) {
            s += char(digits[i] + '0');
        }
        return s;
    }
    static BigInt abs_diff(const BigInt& a, const BigInt& b) {
        if (a < b) {
            return b - a;
        } else {
            return a - b;
        }
    }
};

struct Item {
    BigInt val;
    int idx;
    Item(const BigInt& v, int i) : val(v), idx(i) {}
};

bool descVal(const Item& a, const Item& b) {
    return b.val < a.val; // a > b
}

bool ascVal(const Item& a, const Item& b) {
    return a.val < b.val;
}

BigInt computeSum(const vector<Item>& arr, const vector<bool>& mask) {
    BigInt sum("0");
    for (const auto& item : arr) {
        if (mask[item.idx]) {
            sum = sum + item.val;
        }
    }
    return sum;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string w_str;
    cin >> n >> w_str;
    BigInt W(w_str);

    vector<Item> arr;
    arr.reserve(n);
    BigInt M("0");
    for (int i = 0; i < n; i++) {
        string s;
        cin >> s;
        BigInt val(s);
        arr.emplace_back(val, i);
        if (M < val) {
            M = val;
        }
    }

    // bestDiff and bestMask
    BigInt bestDiff = W; // empty set diff = W
    vector<bool> bestMask(n, false); // empty set

    // helper to update best
    auto updateBest = [&](const vector<bool>& mask, const BigInt& sum) {
        BigInt diff = BigInt::abs_diff(W, sum);
        if (diff < bestDiff) {
            bestDiff = diff;
            bestMask = mask;
        }
    };

    // candidate: empty set already considered

    // candidate: each single item
    for (int i = 0; i < n; i++) {
        vector<bool> mask(n, false);
        mask[arr[i].idx] = true;
        BigInt sum = arr[i].val;
        updateBest(mask, sum);
    }

    // candidate: total sum
    vector<bool> totalMask(n, true);
    BigInt totalSum = computeSum(arr, totalMask);
    updateBest(totalMask, totalSum);

    // greedy descending
    {
        sort(arr.begin(), arr.end(), descVal);
        vector<bool> mask(n, false);
        BigInt sum("0");
        for (const auto& item : arr) {
            BigInt newSum = sum + item.val;
            if (newSum <= W) {
                sum = newSum;
                mask[item.idx] = true;
            }
        }
        updateBest(mask, sum);
    }

    // greedy ascending
    {
        sort(arr.begin(), arr.end(), ascVal);
        vector<bool> mask(n, false);
        BigInt sum("0");
        for (const auto& item : arr) {
            BigInt newSum = sum + item.val;
            if (newSum <= W) {
                sum = newSum;
                mask[item.idx] = true;
            }
        }
        updateBest(mask, sum);
    }

    // randomized greedy
    const int RAND_ITER = 100;
    unsigned seed = chrono::system_clock::now().time_since_epoch().count();
    mt19937 rng(seed);
    for (int iter = 0; iter < RAND_ITER; iter++) {
        shuffle(arr.begin(), arr.end(), rng);
        vector<bool> mask(n, false);
        BigInt sum("0");
        for (const auto& item : arr) {
            BigInt newSum = sum + item.val;
            if (newSum <= W) {
                sum = newSum;
                mask[item.idx] = true;
            }
        }
        updateBest(mask, sum);
    }

    // hill climbing starting from bestMask
    vector<bool> currentMask = bestMask;
    BigInt currentSum = computeSum(arr, currentMask);
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < n; i++) {
            vector<bool> newMask = currentMask;
            BigInt newSum = currentSum;
            if (currentMask[arr[i].idx]) {
                // currently included, try excluding
                newSum = newSum - arr[i].val;
                newMask[arr[i].idx] = false;
            } else {
                // currently excluded, try including
                newSum = newSum + arr[i].val;
                newMask[arr[i].idx] = true;
            }
            if (BigInt::abs_diff(W, newSum) < BigInt::abs_diff(W, currentSum)) {
                currentMask = newMask;
                currentSum = newSum;
                improved = true;
                break; // restart the search
            }
        }
    }
    updateBest(currentMask, currentSum);

    // output
    for (int i = 0; i < n; i++) {
        cout << (bestMask[i] ? 1 : 0);
        if (i < n-1) cout << " ";
    }
    cout << endl;

    return 0;
}