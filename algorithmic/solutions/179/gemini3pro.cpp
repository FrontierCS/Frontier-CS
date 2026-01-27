#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// BigInt Structure
struct BigInt {
    vector<long long> d;
    static const long long BASE = 1000000000;

    BigInt() {}
    BigInt(long long v) {
        if (v == 0) d.push_back(0);
        while (v > 0) {
            d.push_back(v % BASE);
            v /= BASE;
        }
    }
    BigInt(string s) {
        if (s.empty()) { d.push_back(0); return; }
        for (int i = (int)s.length(); i > 0; i -= 9) {
            if (i < 9)
                d.push_back(stoll(s.substr(0, i)));
            else
                d.push_back(stoll(s.substr(i - 9, 9)));
        }
        trim();
    }

    void trim() {
        while (d.size() > 1 && d.back() == 0) d.pop_back();
    }

    bool operator<(const BigInt& o) const {
        if (d.size() != o.d.size()) return d.size() < o.d.size();
        for (int i = (int)d.size() - 1; i >= 0; --i)
            if (d[i] != o.d[i]) return d[i] < o.d[i];
        return false;
    }
    bool operator>(const BigInt& o) const { return o < *this; }
    bool operator<=(const BigInt& o) const { return !(*this > o); }
    bool operator>=(const BigInt& o) const { return !(*this < o); }
    bool operator==(const BigInt& o) const { return d == o.d; }

    BigInt operator+(const BigInt& o) const {
        BigInt res;
        size_t n = max(d.size(), o.d.size());
        res.d.reserve(n + 1);
        long long carry = 0;
        for (size_t i = 0; i < n || carry; ++i) {
            long long sum = carry + (i < d.size() ? d[i] : 0) + (i < o.d.size() ? o.d[i] : 0);
            res.d.push_back(sum % BASE);
            carry = sum / BASE;
        }
        return res;
    }

    BigInt operator-(const BigInt& o) const {
        BigInt res;
        res.d = d;
        long long borrow = 0;
        for (size_t i = 0; i < res.d.size(); ++i) {
            long long sub = res.d[i] - borrow - (i < o.d.size() ? o.d[i] : 0);
            if (sub < 0) {
                sub += BASE;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.d[i] = sub;
        }
        res.trim();
        return res;
    }
};

struct Item {
    int id;
    BigInt val;
};

int n;
BigInt W;
vector<Item> items;
vector<int> best_assignment;
BigInt best_diff;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    string w_str;
    cin >> w_str;
    W = BigInt(w_str);

    items.resize(n);
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        items[i].id = i;
        items[i].val = BigInt(s);
    }

    // Initialize best with empty set
    best_assignment.assign(n, 0);
    best_diff = W;

    auto start_time = chrono::steady_clock::now();
    vector<int> p(n);
    for(int i = 0; i < n; ++i) p[i] = i;

    // Helper lambda for greedy logic
    auto run_greedy = [&](const vector<int>& indices) {
        BigInt current_sum(0);
        vector<int> current_assign(n, 0);
        
        for (int idx : indices) {
            BigInt next_sum = current_sum + items[idx].val;
            if (next_sum <= W) {
                current_sum = next_sum;
                current_assign[items[idx].id] = 1;
            } else {
                // If adding this item exceeds W, check if it improves the score
                BigInt diff = next_sum - W;
                if (diff < best_diff) {
                    best_diff = diff;
                    current_assign[items[idx].id] = 1;
                    best_assignment = current_assign;
                    current_assign[items[idx].id] = 0; // backtrack to continue searching for smaller items
                }
            }
        }
        
        // Final check for the subset sum <= W
        BigInt diff = W - current_sum;
        if (diff < best_diff) {
            best_diff = diff;
            best_assignment = current_assign;
        }
    };

    // 1. Sort Descending
    sort(p.begin(), p.end(), [&](int a, int b) {
        return items[a].val > items[b].val;
    });
    run_greedy(p);

    // 2. Sort Ascending
    sort(p.begin(), p.end(), [&](int a, int b) {
        return items[a].val < items[b].val;
    });
    run_greedy(p);

    // 3. Randomized Greedy
    mt19937 rng(1337);
    while (true) {
        // Stop if perfect solution found
        if (best_diff.d.size() == 1 && best_diff.d[0] == 0) break;
        
        // Time limit check (approx 1.9s)
        auto now = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 1900) break;
        
        shuffle(p.begin(), p.end(), rng);
        run_greedy(p);
    }

    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}