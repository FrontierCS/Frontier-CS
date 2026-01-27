#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <random>
#include <chrono>

using namespace std;

// BigInt Structure to handle numbers up to 10^1100
struct BigInt {
    vector<int> digits;
    static const int BASE = 1000000000;

    BigInt() {}
    
    // Construct from long long
    BigInt(long long v) {
        if (v == 0) digits.push_back(0);
        while (v > 0) {
            digits.push_back(v % BASE);
            v /= BASE;
        }
    }

    // Construct from string
    BigInt(string s) {
        if (s.empty()) { digits.push_back(0); return; }
        for (int i = (int)s.length(); i > 0; i -= 9) {
            if (i < 9)
                digits.push_back(stoi(s.substr(0, i)));
            else
                digits.push_back(stoi(s.substr(i - 9, 9)));
        }
        trim();
    }

    // Remove leading zeros
    void trim() {
        while (digits.size() > 1 && digits.back() == 0) {
            digits.pop_back();
        }
    }

    // Comparison operators
    bool operator<(const BigInt& other) const {
        if (digits.size() != other.digits.size())
            return digits.size() < other.digits.size();
        for (int i = (int)digits.size() - 1; i >= 0; --i) {
            if (digits[i] != other.digits[i])
                return digits[i] < other.digits[i];
        }
        return false;
    }

    bool operator>(const BigInt& other) const { return other < *this; }
    bool operator<=(const BigInt& other) const { return !(*this > other); }
    bool operator>=(const BigInt& other) const { return !(*this < other); }
    bool operator==(const BigInt& other) const { return digits == other.digits; }

    // Addition
    BigInt operator+(const BigInt& other) const {
        BigInt res;
        res.digits.reserve(max(digits.size(), other.digits.size()) + 1);
        int carry = 0;
        for (size_t i = 0; i < max(digits.size(), other.digits.size()) || carry; ++i) {
            long long sum = carry + (long long)(i < digits.size() ? digits[i] : 0) + (long long)(i < other.digits.size() ? other.digits[i] : 0);
            if (sum >= BASE) {
                res.digits.push_back(sum - BASE);
                carry = 1;
            } else {
                res.digits.push_back(sum);
                carry = 0;
            }
        }
        return res;
    }
    
    // Subtraction (Assumes *this >= other)
    BigInt operator-(const BigInt& other) const {
        BigInt res;
        res.digits.reserve(digits.size());
        int carry = 0;
        for (size_t i = 0; i < digits.size(); ++i) {
            long long sub = (long long)digits[i] - carry - (long long)(i < other.digits.size() ? other.digits[i] : 0);
            if (sub < 0) {
                sub += BASE;
                carry = 1;
            } else {
                carry = 0;
            }
            res.digits.push_back(sub);
        }
        res.trim();
        return res;
    }
    
    // Absolute difference
    static BigInt absDiff(const BigInt& a, const BigInt& b) {
        if (a < b) return b - a;
        return a - b;
    }
};

struct Item {
    int id; // Original index
    BigInt val;
};

int n;
BigInt W;
vector<Item> items;
vector<int> best_assignment;
BigInt best_diff;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    string w_str;
    cin >> w_str;
    W = BigInt(w_str);

    items.resize(n);
    for (int i = 0; i < n; ++i) {
        items[i].id = i;
        string s;
        cin >> s;
        items[i].val = BigInt(s);
    }

    // Initialize best solution with empty set
    best_assignment.assign(n, 0);
    best_diff = W;

    // Index array to control processing order
    vector<int> p(n);
    for(int i=0; i<n; ++i) p[i] = i;

    // Pass 1: Deterministic Greedy with Descending Sort
    // Sorting larger items first usually helps in subset sum
    sort(p.begin(), p.end(), [&](int a, int b) {
        return items[a].val > items[b].val;
    });

    // Random Number Generator setup
    mt19937 rng(static_cast<unsigned int>(chrono::steady_clock::now().time_since_epoch().count()));
    
    double start_time = (double)clock() / CLOCKS_PER_SEC;
    bool first_pass = true;

    // Iterative Randomized Greedy
    // Run as many passes as possible within time limit
    while (true) {
        if (!first_pass) {
            // Check time limit (approx 1.85s to be safe for 2s limit)
            if ((double)clock() / CLOCKS_PER_SEC - start_time > 1.85) break;
            
            // Random shuffle for subsequent passes
            shuffle(p.begin(), p.end(), rng);
        }

        BigInt current_sum(0);
        vector<int> current_assignment(n, 0);

        for (int idx : p) {
            BigInt next_sum = current_sum + items[idx].val;
            
            // Greedy decision
            if (next_sum <= W) {
                // Always take if it fits
                current_sum = next_sum;
                current_assignment[idx] = 1;
            } else {
                // If it overshoots, check if it brings us closer to W
                // Compare error |W - current_sum| with |next_sum - W|
                BigInt diff_curr = W - current_sum;
                BigInt diff_next = next_sum - W;
                
                if (diff_next < diff_curr) {
                    current_sum = next_sum;
                    current_assignment[idx] = 1;
                }
                
                // If we have overshot W (current_sum > W), adding any more positive integers
                // will only increase the error. Break this pass.
                if (current_sum > W) break;
            }
        }
        
        // Update global best if current is better
        BigInt diff = BigInt::absDiff(W, current_sum);
        if (diff < best_diff) {
            best_diff = diff;
            best_assignment = current_assignment;
            
            // If perfect match found (diff == 0), terminate early
            if (best_diff.digits.size() == 1 && best_diff.digits[0] == 0) break;
        }

        first_pass = false;
    }

    // Output result
    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}