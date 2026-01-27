#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <set>

using namespace std;

// A simple BigInt class for non-negative integers.
struct BigInt {
    string digits;

    BigInt(long long val = 0) {
        if (val == 0) {
            digits = "0";
            return;
        }
        digits = to_string(val);
    }
    
    BigInt(string s) {
        if (s.empty()) {
            digits = "0";
            return;
        }
        auto first_digit = s.find_first_not_of('0');
        if (string::npos == first_digit) {
            digits = "0";
        } else {
            digits = s.substr(first_digit);
        }
    }

    bool operator<(const BigInt& other) const {
        if (digits.length() != other.digits.length()) {
            return digits.length() < other.digits.length();
        }
        return digits < other.digits;
    }

    bool operator==(const BigInt& other) const {
        return digits == other.digits;
    }

    BigInt operator+(const BigInt& other) const {
        string a = digits;
        string b = other.digits;
        string res = "";
        int i = a.length() - 1;
        int j = b.length() - 1;
        int carry = 0;
        while (i >= 0 || j >= 0 || carry) {
            int sum = carry + (i >= 0 ? a[i--] - '0' : 0) + (j >= 0 ? b[j--] - '0' : 0);
            res.push_back(sum % 10 + '0');
            carry = sum / 10;
        }
        reverse(res.begin(), res.end());
        return BigInt(res);
    }

    // Assumes *this >= other
    BigInt operator-(const BigInt& other) const {
        string a = digits;
        string b = other.digits;
        string res = "";
        int i = a.length() - 1;
        int j = b.length() - 1;
        int borrow = 0;
        while (i >= 0) {
            int sub = (a[i] - '0') - (j >= 0 ? b[j--] - '0' : 0) - borrow;
            if (sub < 0) {
                sub += 10;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.push_back(sub + '0');
            i--;
        }
        reverse(res.begin(), res.end());
        return BigInt(res);
    }
};

struct BigIntCmp {
    bool operator()(const BigInt& a, const BigInt& b) const {
        return a < b;
    }
};

struct State {
    BigInt sum;
    int prev_idx;
    bool choice;
};

struct Candidate {
    BigInt diff;
    State state;

    bool operator<(const Candidate& other) const {
        return diff < other.diff;
    }
};

BigInt abs_diff(const BigInt& a, const BigInt& b) {
    if (a < b) {
        return b - a;
    }
    return a - b;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    string w_str;
    cin >> n >> w_str;
    BigInt W(w_str);

    vector<pair<BigInt, int>> a(n);
    for (int i = 0; i < n; ++i) {
        string val_str;
        cin >> val_str;
        a[i] = {BigInt(val_str), i};
    }

    sort(a.rbegin(), a.rend());

    const int K = 100;

    vector<vector<State>> beams(n + 1);
    beams[0].push_back({BigInt(0), -1, false});

    for (int i = 0; i < n; ++i) {
        vector<Candidate> candidates;
        candidates.reserve(beams[i].size() * 2);
        for (size_t j = 0; j < beams[i].size(); ++j) {
            const auto& current_state = beams[i][j];

            // Option 1: Don't take a[i]
            State s1 = {current_state.sum, (int)j, false};
            candidates.push_back({abs_diff(s1.sum, W), s1});

            // Option 2: Take a[i]
            State s2 = {current_state.sum + a[i].first, (int)j, true};
            candidates.push_back({abs_diff(s2.sum, W), s2});
        }
        
        sort(candidates.begin(), candidates.end());
        
        set<BigInt, BigIntCmp> seen_sums;
        beams[i+1].reserve(K);
        for (const auto& cand : candidates) {
            if (seen_sums.find(cand.state.sum) == seen_sums.end()) {
                beams[i+1].push_back(cand.state);
                seen_sums.insert(cand.state.sum);
                if (beams[i+1].size() >= K) {
                    break;
                }
            }
        }
    }

    int best_idx = -1;
    BigInt min_diff;

    for (size_t i = 0; i < beams[n].size(); ++i) {
        BigInt diff = abs_diff(beams[n][i].sum, W);
        if (best_idx == -1 || diff < min_diff) {
            min_diff = diff;
            best_idx = i;
        }
    }

    vector<bool> b_sorted(n);
    int current_idx = best_idx;
    for (int i = n; i > 0; --i) {
        const auto& state = beams[i][current_idx];
        b_sorted[i-1] = state.choice;
        current_idx = state.prev_idx;
    }

    vector<int> b(n);
    for (int i = 0; i < n; ++i) {
        if (b_sorted[i]) {
            b[a[i].second] = 1;
        } else {
            b[a[i].second] = 0;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << b[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}