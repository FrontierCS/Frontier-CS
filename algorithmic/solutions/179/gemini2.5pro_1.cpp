#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <iomanip>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

const int BASE_POWER = 9;
const int BASE = 1e9;

struct BigInt {
    std::vector<int> digits; // least significant first
    bool is_zero_val;

    BigInt(long long v = 0) {
        if (v == 0) {
            digits.push_back(0);
            is_zero_val = true;
        } else {
            is_zero_val = false;
            while (v > 0) {
                digits.push_back(v % BASE);
                v /= BASE;
            }
        }
    }

    BigInt(std::string s) {
        if (s.empty() || s == "0") {
            digits.push_back(0);
            is_zero_val = true;
            return;
        }
        is_zero_val = false;
        digits.clear();
        for (int i = s.length(); i > 0; i -= BASE_POWER) {
            int chunk = 0;
            for (int j = std::max(0, i - BASE_POWER); j < i; j++) {
                chunk = chunk * 10 + (s[j] - '0');
            }
            digits.push_back(chunk);
        }
        trim();
    }

    void trim() {
        while (digits.size() > 1 && digits.back() == 0) {
            digits.pop_back();
        }
        if (digits.size() == 1 && digits[0] == 0) {
            is_zero_val = true;
        } else {
            is_zero_val = false;
        }
    }
    
    bool is_zero() const {
        return is_zero_val;
    }

    bool operator<(const BigInt& other) const {
        if (digits.size() != other.digits.size()) {
            return digits.size() < other.digits.size();
        }
        for (int i = digits.size() - 1; i >= 0; --i) {
            if (digits[i] != other.digits[i]) {
                return digits[i] < other.digits[i];
            }
        }
        return false;
    }
    
    bool operator>(const BigInt& other) const {
        return other < *this;
    }
    
    bool operator<=(const BigInt& other) const {
        return !(*this > other);
    }
    
    bool operator>=(const BigInt& other) const {
        return !(*this < other);
    }

    BigInt operator+(const BigInt& other) const {
        if (is_zero()) return other;
        if (other.is_zero()) return *this;

        BigInt res;
        res.digits.clear();
        int carry = 0;
        for (size_t i = 0; i < digits.size() || i < other.digits.size() || carry; ++i) {
            long long current = carry;
            if (i < digits.size()) current += digits[i];
            if (i < other.digits.size()) current += other.digits[i];
            res.digits.push_back(current % BASE);
            carry = current / BASE;
        }
        res.trim();
        return res;
    }

    // Assumes *this >= other
    BigInt operator-(const BigInt& other) const {
        if (other.is_zero()) return *this;
        if (*this <= other) return BigInt(0);

        BigInt res;
        res.digits.clear();
        int borrow = 0;
        for (size_t i = 0; i < digits.size(); ++i) {
            long long current = digits[i] - borrow;
            if (i < other.digits.size()) current -= other.digits[i];
            
            if (current < 0) {
                current += BASE;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.digits.push_back(current);
        }
        res.trim();
        return res;
    }
};

int n;
BigInt W;
std::vector<BigInt> a;
std::vector<std::pair<BigInt, int>> indexed_a;

std::vector<bool> best_b_overall;
BigInt best_S_diff_overall;

void update_best(const std::vector<bool>& b, const BigInt& S) {
    BigInt diff;
    if (W >= S) diff = W - S;
    else diff = S - W;
    
    if (best_b_overall.empty() || diff < best_S_diff_overall) {
        best_S_diff_overall = diff;
        best_b_overall = b;
    }
}


void solve() {
    std::string w_str;
    std::cin >> n >> w_str;
    W = BigInt(w_str);
    a.resize(n);
    indexed_a.resize(n);
    for (int i = 0; i < n; ++i) {
        std::string a_str;
        std::cin >> a_str;
        a[i] = BigInt(a_str);
        indexed_a[i] = {a[i], i};
    }
    
    // --- Initial solution: greedy descending ---
    std::sort(indexed_a.rbegin(), indexed_a.rend());
    
    std::vector<bool> current_b(n, false);
    BigInt current_S(0);
    
    for (const auto& p : indexed_a) {
        if ((current_S + p.first) <= W) {
            current_S = current_S + p.first;
            current_b[p.second] = true;
        }
    }
    
    update_best(current_b, current_S);
    
    // --- Local Search ---
    for (int iter = 0; iter < 5; ++iter) {
        std::vector<int> C, U;
        for(int i = 0; i < n; ++i) {
            if (current_b[i]) C.push_back(i);
            else U.push_back(i);
        }
        
        if (C.empty() || U.empty()) break;
        
        std::vector<std::pair<BigInt, int>> U_pairs;
        for (int u_idx : U) {
            U_pairs.push_back({a[u_idx], u_idx});
        }
        std::sort(U_pairs.begin(), U_pairs.end());

        int best_c = -1, best_u = -1;
        BigInt best_diff_for_iter = best_S_diff_overall;
        BigInt new_S_for_best_swap;
        
        if (W >= current_S) {
            BigInt D = W - current_S;
            for (int c_idx : C) {
                BigInt target = a[c_idx] + D;
                auto it = std::lower_bound(U_pairs.begin(), U_pairs.end(), std::make_pair(target, 0));
                
                if (it != U_pairs.end()) {
                    int u_idx = it->second;
                    BigInt new_S = (current_S - a[c_idx]) + a[u_idx];
                    BigInt new_diff = (W >= new_S) ? W - new_S : new_S - W;
                    if (new_diff < best_diff_for_iter) {
                        best_diff_for_iter = new_diff;
                        best_c = c_idx; best_u = u_idx;
                        new_S_for_best_swap = new_S;
                    }
                }
                if (it != U_pairs.begin()) {
                    it--;
                    int u_idx = it->second;
                    BigInt new_S = (current_S - a[c_idx]) + a[u_idx];
                    BigInt new_diff = (W >= new_S) ? W - new_S : new_S - W;
                     if (new_diff < best_diff_for_iter) {
                        best_diff_for_iter = new_diff;
                        best_c = c_idx; best_u = u_idx;
                        new_S_for_best_swap = new_S;
                    }
                }
            }
        } else { // W < current_S
            BigInt D = current_S - W;
            for (int c_idx : C) {
                if (a[c_idx] > D) {
                    BigInt target = a[c_idx] - D;
                    auto it = std::lower_bound(U_pairs.begin(), U_pairs.end(), std::make_pair(target, 0));
                    if (it != U_pairs.end()) {
                        int u_idx = it->second;
                        BigInt new_S = (current_S - a[c_idx]) + a[u_idx];
                        BigInt new_diff = (W >= new_S) ? W - new_S : new_S - W;
                        if (new_diff < best_diff_for_iter) {
                            best_diff_for_iter = new_diff;
                            best_c = c_idx; best_u = u_idx;
                            new_S_for_best_swap = new_S;
                        }
                    }
                    if (it != U_pairs.begin()) {
                        it--;
                        int u_idx = it->second;
                        BigInt new_S = (current_S - a[c_idx]) + a[u_idx];
                        BigInt new_diff = (W >= new_S) ? W - new_S : new_S - W;
                        if (new_diff < best_diff_for_iter) {
                            best_diff_for_iter = new_diff;
                            best_c = c_idx; best_u = u_idx;
                            new_S_for_best_swap = new_S;
                        }
                    }
                } else { // target <= 0
                    int u_idx = U_pairs[0].second;
                    BigInt new_S = (current_S - a[c_idx]) + a[u_idx];
                    BigInt new_diff = (W >= new_S) ? W - new_S : new_S - W;
                    if (new_diff < best_diff_for_iter) {
                        best_diff_for_iter = new_diff;
                        best_c = c_idx; best_u = u_idx;
                        new_S_for_best_swap = new_S;
                    }
                }
            }
        }
        
        if (best_c != -1) {
            current_b[best_c] = false;
            current_b[best_u] = true;
            current_S = new_S_for_best_swap;
            update_best(current_b, current_S);
        } else {
            break;
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << best_b_overall[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    fast_io();
    solve();
    return 0;
}