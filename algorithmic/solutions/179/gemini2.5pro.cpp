#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <stdexcept>

// Basic BigInt implementation
struct BigInt {
    std::string digits;

    BigInt(long long n = 0) : digits(std::to_string(n)) {}
    BigInt(std::string s) {
        if (s.empty() || s.find_first_not_of("0123456789") != std::string::npos) {
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

    bool operator<(const BigInt& other) const {
        if (digits.length() != other.digits.length()) {
            return digits.length() < other.digits.length();
        }
        return digits < other.digits;
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

    BigInt operator-(const BigInt& other) const {
        std::string a = digits;
        std::string b = other.digits;
        std::string res = "";
        int n1 = a.length(), n2 = b.length();
        std::reverse(a.begin(), a.end());
        std::reverse(b.begin(), b.end());
        int carry = 0;
        for (int i = 0; i < n2; i++) {
            int sub = ((a[i] - '0') - (b[i] - '0') - carry);
            if (sub < 0) {
                sub = sub + 10;
                carry = 1;
            } else {
                carry = 0;
            }
            res += std::to_string(sub);
        }
        for (int i = n2; i < n1; i++) {
            int sub = ((a[i] - '0') - carry);
            if (sub < 0) {
                sub = sub + 10;
                carry = 1;
            } else {
                carry = 0;
            }
            res += std::to_string(sub);
        }
        std::reverse(res.begin(), res.end());
        return BigInt(res);
    }
};

BigInt abs_diff(const BigInt& a, const BigInt& b) {
    if (a < b) return b - a;
    return a - b;
}

struct Item {
    BigInt val;
    int id;
};

std::pair<BigInt, std::vector<int>> solve_approx_subset_sum(int n, const std::vector<Item>& items, const BigInt& W) {
    if (W.digits == "0") {
        return {BigInt(0), std::vector<int>(n + 1, 0)};
    }
    
    int P = std::min(n * 2, 4200);
    std::vector<int> v(n);
    
    for (int i = 0; i < n; ++i) {
        std::string prod_str;
        unsigned long long current = 0;
        for(int j = items[i].val.digits.length() - 1; j >= 0; j--) {
            current += (unsigned long long)(items[i].val.digits[j] - '0') * P;
            prod_str.push_back((current % 10) + '0');
            current /= 10;
        }
        while(current > 0) {
            prod_str.push_back((current % 10) + '0');
            current /= 10;
        }
        std::reverse(prod_str.begin(), prod_str.end());
        BigInt prod(prod_str);

        int l = 0, r = P, ans = 0;
        while(l <= r){
            int mid = l + (r-l)/2;
            std::string mid_W_str;
            current = 0;
            for(int j = W.digits.length() - 1; j >= 0; j--) {
                current += (unsigned long long)(W.digits[j] - '0') * mid;
                mid_W_str.push_back((current % 10) + '0');
                current /= 10;
            }
            while(current > 0) {
                mid_W_str.push_back((current % 10) + '0');
                current /= 10;
            }
            std::reverse(mid_W_str.begin(), mid_W_str.end());
            BigInt mid_W(mid_W_str);

            if ( !(prod < mid_W) ){
                ans = mid;
                l = mid + 1;
            } else {
                r = mid - 1;
            }
        }
        v[i] = ans;
    }
    
    const BigInt INF_SENTINEL("1" + std::string(1200, '0'));
    std::vector<BigInt> dp(P + 1, INF_SENTINEL);
    std::vector<std::pair<int, int>> from(P + 1, {-1, -1});
    dp[0] = BigInt(0);

    for (int i = 0; i < n; ++i) {
        int val_scaled = v[i];
        if (val_scaled == 0) continue;
        for (int j = P; j >= val_scaled; --j) {
            if (!(INF_SENTINEL < dp[j - val_scaled])) {
                BigInt new_sum = dp[j - val_scaled] + items[i].val;
                if (new_sum < dp[j]) {
                    dp[j] = new_sum;
                    from[j] = {i, j - val_scaled};
                }
            }
        }
    }

    BigInt best_sum = BigInt(0);
    BigInt min_diff = W;
    int best_j = 0;

    for (int j = 0; j <= P; ++j) {
        if (!(INF_SENTINEL < dp[j])) {
            BigInt diff = abs_diff(W, dp[j]);
            if (diff < min_diff) {
                min_diff = diff;
                best_sum = dp[j];
                best_j = j;
            }
        }
    }

    std::vector<int> b(n + 1, 0);
    int curr_j = best_j;
    while (curr_j > 0 && from[curr_j].first != -1) {
        int item_idx = from[curr_j].first;
        b[items[item_idx].id] = 1;
        curr_j = from[curr_j].second;
    }
    
    return {best_sum, b};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::string w_str;
    std::cin >> n >> w_str;
    BigInt W(w_str);

    std::vector<Item> items(n);
    BigInt s_all(0);
    for (int i = 0; i < n; ++i) {
        std::string a_str;
        std::cin >> a_str;
        items[i] = {BigInt(a_str), i + 1};
        s_all = s_all + items[i].val;
    }
    
    auto res1 = solve_approx_subset_sum(n, items, W);
    BigInt s1 = res1.first;
    std::vector<int> b1 = res1.second;

    BigInt best_s = s1;
    std::vector<int> best_b = b1;

    if (!(s_all < W)) {
        BigInt W_prime = s_all - W;
        auto res2 = solve_approx_subset_sum(n, items, W_prime);
        BigInt s_prime_dp = res2.first;
        
        BigInt s2 = s_all - s_prime_dp;
        if (abs_diff(W, s2) < abs_diff(W, best_s)) {
            best_s = s2;
            best_b = res2.second;
            for (int i = 1; i <= n; ++i) {
                best_b[i] = 1 - best_b[i];
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_b[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}