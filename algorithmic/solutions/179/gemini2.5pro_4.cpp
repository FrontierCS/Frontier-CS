#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <vector>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);
}

// Minimal BigInt implementation using strings.
struct BigInt {
    std::string digits;

    BigInt(long long n = 0) : digits(std::to_string(n)) {}
    BigInt(std::string s) {
        if (s.empty()) {
            digits = "0";
            return;
        }
        size_t first_digit = s.find_first_not_of('0');
        if (std::string::npos == first_digit) {
            digits = "0";
        } else {
            digits = s.substr(first_digit);
        }
    }

    bool is_zero() const { return digits == "0"; }

    bool operator<(const BigInt& other) const {
        if (digits.length() != other.digits.length()) {
            return digits.length() < other.digits.length();
        }
        return digits < other.digits;
    }
    
    bool operator<=(const BigInt& other) const {
        return !(other < *this);
    }

    bool operator==(const BigInt& other) const {
        return digits == other.digits;
    }

    BigInt operator+(const BigInt& other) const {
        std::string a = digits;
        std::string b = other.digits;
        std::string res = "";
        int i = a.length() - 1, j = b.length() - 1, carry = 0;
        while (i >= 0 || j >= 0 || carry) {
            int sum = carry + (i >= 0 ? a[i--] - '0' : 0) + (j >= 0 ? b[j--] - '0' : 0);
            res += std::to_string(sum % 10);
            carry = sum / 10;
        }
        std::reverse(res.begin(), res.end());
        return BigInt(res);
    }

    BigInt operator-(const BigInt& other) const { // Assumes *this >= other
        std::string a = digits;
        std::string b = other.digits;
        std::string res = "";
        int i = a.length() - 1, j = b.length() - 1, borrow = 0;
        while (i >= 0) {
            int sub = (a[i] - '0') - (j >= 0 ? b[j] - '0' : 0) - borrow;
            if (sub < 0) {
                sub += 10;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res += std::to_string(sub);
            i--;
            j--;
        }
        std::reverse(res.begin(), res.end());
        return BigInt(res);
    }
};

struct Item {
    BigInt value;
    int index;
};

// Heuristic parameter for DP table size
const int MAX_DP_SIZE = 400;

// Function to find the best subset sum <= target
std::pair<BigInt, std::vector<bool>> solve(const BigInt& target, const std::vector<Item>& items, int n) {
    std::vector<std::pair<BigInt, std::vector<bool>>> dp;
    dp.push_back({BigInt(0), std::vector<bool>(n, false)});

    for (const auto& item : items) {
        std::vector<std::pair<BigInt, std::vector<bool>>> new_sums;
        new_sums.reserve(dp.size());
        for (const auto& p : dp) {
            BigInt new_sum = p.first + item.value;
            if (new_sum <= target) {
                std::vector<bool> new_sol = p.second;
                new_sol[item.index] = true;
                new_sums.push_back({new_sum, new_sol});
            }
        }
        
        if (!new_sums.empty()) {
            std::vector<std::pair<BigInt, std::vector<bool>>> merged_dp;
            merged_dp.reserve(dp.size() + new_sums.size());
            std::merge(dp.begin(), dp.end(), new_sums.begin(), new_sums.end(), 
                       std::back_inserter(merged_dp), 
                       [](const auto& a, const auto& b){ return a.first < b.first; });
            
            merged_dp.erase(std::unique(merged_dp.begin(), merged_dp.end(), 
                [](const auto& a, const auto& b){ return a.first == b.first; }), merged_dp.end());
            dp = std::move(merged_dp);
        }

        if (dp.size() > MAX_DP_SIZE) {
            std::vector<std::pair<BigInt, std::vector<bool>>> trimmed_dp;
            trimmed_dp.reserve(MAX_DP_SIZE);
            for (int j = 0; j < MAX_DP_SIZE; ++j) {
                long long idx = (long long)j * (dp.size() - 1) / (MAX_DP_SIZE - 1);
                trimmed_dp.push_back(std::move(dp[idx]));
            }
            dp = std::move(trimmed_dp);
        }
    }
    return dp.back();
}

void print_solution(const std::vector<bool>& b) {
    for (size_t i = 0; i < b.size(); ++i) {
        std::cout << b[i] << (i == b.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    fast_io();

    int n;
    std::string w_str;
    std::cin >> n >> w_str;
    BigInt W(w_str);

    std::vector<Item> items;
    BigInt S_total(0);
    for (int i = 0; i < n; ++i) {
        std::string a_str;
        std::cin >> a_str;
        BigInt a(a_str);
        if (!a.is_zero()) {
            items.push_back({a, i});
            S_total = S_total + a;
        }
    }
    
    if (S_total <= W) {
        std::vector<bool> b(n, false);
        for (const auto& item : items) {
            b[item.index] = true;
        }
        print_solution(b);
        return 0;
    }

    auto res1 = solve(W, items, n);
    BigInt S1 = res1.first;
    std::vector<bool> b1 = res1.second;

    BigInt W_comp = S_total - W;
    auto res_comp = solve(W_comp, items, n);
    BigInt S_comp = res_comp.first;
    std::vector<bool> b_comp = res_comp.second;
    
    BigInt S2 = S_total - S_comp;
    std::vector<bool> b2(n, false);
    for (const auto& item : items) {
        b2[item.index] = true;
    }
    for (int i = 0; i < n; ++i) {
        if (b_comp[i]) {
            b2[i] = false;
        }
    }

    BigInt diff1 = W - S1;
    BigInt diff2 = S2 - W;

    if (diff1 <= diff2) {
        print_solution(b1);
    } else {
        print_solution(b2);
    }

    return 0;
}