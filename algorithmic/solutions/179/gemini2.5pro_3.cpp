#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <stdexcept>
#include <chrono>
#include <random>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// Bignum implementation
const int BASE = 1e9;

struct BigInt {
    std::vector<int> digits;
    bool is_positive = true;

    BigInt(long long n = 0) {
        if (n == 0) {
            digits.push_back(0);
        } else {
            if (n < 0) {
                is_positive = false;
                n = -n;
            }
            while (n > 0) {
                digits.push_back(n % BASE);
                n /= BASE;
            }
        }
    }

    BigInt(std::string s) {
        if (s.empty() || s == "0") {
            digits.push_back(0);
            return;
        }
        if (s[0] == '-') {
            is_positive = false;
            s = s.substr(1);
        }
        for (int i = s.length(); i > 0; i -= 9) {
            long long chunk = 0;
            int start = std::max(0, i - 9);
            std::string sub = s.substr(start, i - start);
            if (!sub.empty()) {
                 chunk = std::stoll(sub);
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
            is_positive = true;
        }
    }

    int compare_abs(const BigInt& other) const {
        if (digits.size() != other.digits.size()) {
            return digits.size() < other.digits.size() ? -1 : 1;
        }
        for (int i = digits.size() - 1; i >= 0; --i) {
            if (digits[i] != other.digits[i]) {
                return digits[i] < other.digits[i] ? -1 : 1;
            }
        }
        return 0;
    }

    bool operator<(const BigInt& other) const {
        if (is_positive != other.is_positive) {
            return !is_positive;
        }
        if (is_positive) {
            return compare_abs(other) < 0;
        }
        return compare_abs(other) > 0;
    }
     bool operator>(const BigInt& other) const { return other < *this; }
     bool operator<=(const BigInt& other) const { return !(other < *this); }
     bool operator>=(const BigInt& other) const { return !(*this < other); }
     bool operator==(const BigInt& other) const { return is_positive == other.is_positive && compare_abs(other) == 0; }
     bool operator!=(const BigInt& other) const { return !(*this == other); }
};

BigInt add_abs(const BigInt& a, const BigInt& b) {
    BigInt res;
    res.digits.clear();
    int carry = 0;
    for (size_t i = 0; i < std::max(a.digits.size(), b.digits.size()) || carry; ++i) {
        long long current = carry;
        if (i < a.digits.size()) current += a.digits[i];
        if (i < b.digits.size()) current += b.digits[i];
        res.digits.push_back(current % BASE);
        carry = current / BASE;
    }
    res.trim();
    return res;
}

BigInt sub_abs(const BigInt& a, const BigInt& b) { // assumes |a| >= |b|
    BigInt res;
    res.digits.clear();
    int borrow = 0;
    for (size_t i = 0; i < a.digits.size(); ++i) {
        long long current_a = a.digits[i];
        long long current_b = (i < b.digits.size() ? b[i] : 0);
        long long diff = current_a - current_b - borrow;
        if (diff < 0) {
            diff += BASE;
            borrow = 1;
        } else {
            borrow = 0;
        }
        res.digits.push_back(diff);
    }
    res.trim();
    return res;
}

BigInt operator+(const BigInt& a, const BigInt& b) {
    if (a.is_positive == b.is_positive) {
        BigInt res = add_abs(a, b);
        res.is_positive = a.is_positive;
        return res;
    }
    if (a.compare_abs(b) >= 0) {
        BigInt res = sub_abs(a, b);
        res.is_positive = a.is_positive;
        return res;
    }
    BigInt res = sub_abs(b, a);
    res.is_positive = b.is_positive;
    return res;
}

BigInt operator-(const BigInt& a, const BigInt& b) {
    BigInt neg_b = b;
    if (!(neg_b.digits.size() == 1 && neg_b.digits[0] == 0)) {
        neg_b.is_positive = !neg_b.is_positive;
    }
    return a + neg_b;
}

BigInt abs_diff(const BigInt& a, const BigInt& b) {
    if (a < b) return b - a;
    return a - b;
}


int main() {
    fast_io();

    int n;
    std::string w_str;
    std::cin >> n >> w_str;
    BigInt W(w_str);

    std::vector<std::pair<BigInt, int>> a_pairs(n);
    std::vector<BigInt> a_vals(n);
    for (int i = 0; i < n; ++i) {
        std::string val_str;
        std::cin >> val_str;
        a_vals[i] = BigInt(val_str);
        a_pairs[i] = {a_vals[i], i};
    }

    std::vector<bool> best_b(n);
    BigInt best_diff;

    {
        auto a_sorted = a_pairs;
        std::sort(a_sorted.rbegin(), a_sorted.rend());

        BigInt current_s(0);
        std::vector<bool> current_b(n, false);
        for (const auto& p : a_sorted) {
            if (current_s + p.first <= W) {
                current_s = current_s + p.first;
                current_b[p.second] = true;
            }
        }
        best_b = current_b;
        best_diff = W - current_s;
    }

    {
        auto a_sorted = a_pairs;
        std::sort(a_sorted.rbegin(), a_sorted.rend());

        BigInt current_s(0);
        std::vector<bool> current_b(n, false);
        for (const auto& p : a_sorted) {
            BigInt diff1 = abs_diff(W, current_s);
            BigInt diff2 = abs_diff(W, current_s + p.first);
            if (diff2 < diff1) {
                current_s = current_s + p.first;
                current_b[p.second] = true;
            }
        }
        if (abs_diff(W, current_s) < best_diff) {
            best_b = current_b;
            best_diff = abs_diff(W, current_s);
        }
    }
    
    BigInt current_s(0);
    std::vector<bool> current_b = best_b;
    std::vector<int> in_indices, out_indices;
    std::vector<int> in_pos(n), out_pos(n);

    for(int i=0; i<n; ++i) {
        if(current_b[i]) {
            current_s = current_s + a_vals[i];
            in_pos[i] = in_indices.size();
            in_indices.push_back(i);
        } else {
            out_pos[i] = out_indices.size();
            out_indices.push_back(i);
        }
    }

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit = 1.9;

    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        double elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(current_time - start_time).count();
        if (elapsed > time_limit) break;
        if (best_diff == BigInt(0)) break;

        std::uniform_real_distribution<> prob_dist(0.0, 1.0);
        
        if (prob_dist(rng) < 0.7 || in_indices.empty() || out_indices.empty()) { // 1-flip
            std::uniform_int_distribution<int> idx_dist(0, n - 1);
            int idx_to_flip = idx_dist(rng);
            
            BigInt next_s = current_b[idx_to_flip] ? (current_s - a_vals[idx_to_flip]) : (current_s + a_vals[idx_to_flip]);
            
            if (abs_diff(W, next_s) < abs_diff(W, current_s)) {
                current_s = next_s;
                
                if (current_b[idx_to_flip]) { // moved from in to out
                    int pos_to_fill = in_pos[idx_to_flip];
                    int last_in_idx = in_indices.back();
                    in_indices[pos_to_fill] = last_in_idx;
                    in_pos[last_in_idx] = pos_to_fill;
                    in_indices.pop_back();
                    out_pos[idx_to_flip] = out_indices.size();
                    out_indices.push_back(idx_to_flip);
                } else { // moved from out to in
                    int pos_to_fill = out_pos[idx_to_flip];
                    int last_out_idx = out_indices.back();
                    out_indices[pos_to_fill] = last_out_idx;
                    out_pos[last_out_idx] = pos_to_fill;
                    out_indices.pop_back();
                    in_pos[idx_to_flip] = in_indices.size();
                    in_indices.push_back(idx_to_flip);
                }
                current_b[idx_to_flip] = !current_b[idx_to_flip];
            }
        } else { // swap
            std::uniform_int_distribution<int> in_dist(0, in_indices.size() - 1);
            std::uniform_int_distribution<int> out_dist(0, out_indices.size() - 1);
            int in_vec_idx = in_dist(rng);
            int out_vec_idx = out_dist(rng);
            int idx_in = in_indices[in_vec_idx];
            int idx_out = out_indices[out_vec_idx];

            BigInt next_s = current_s - a_vals[idx_in] + a_vals[idx_out];
            if (abs_diff(W, next_s) < abs_diff(W, current_s)) {
                current_s = next_s;
                
                in_indices[in_vec_idx] = idx_out;
                out_indices[out_vec_idx] = idx_in;
                
                std::swap(in_pos[idx_in], in_pos[idx_out]);
                std::swap(out_pos[idx_in], out_pos[idx_out]);
                
                current_b[idx_in] = false;
                current_b[idx_out] = true;
            }
        }
        if (abs_diff(W, current_s) < best_diff) {
            best_diff = abs_diff(W, current_s);
            best_b = current_b;
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << (best_b[i] ? 1 : 0) << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}