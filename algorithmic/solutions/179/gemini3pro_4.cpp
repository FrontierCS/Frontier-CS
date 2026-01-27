#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// BigInt Implementation
// Base 10^18 fits in uint64_t, but we need to be careful with addition overflow if we were adding.
// For this problem, we mainly need subtraction and comparison.
const uint64_t BASE = 1000000000000000000ULL;

struct BigInt {
    vector<uint64_t> d;

    BigInt() {}
    BigInt(string s) {
        if (s.empty()) { d.push_back(0); return; }
        int n = s.length();
        while (n > 0) {
            int start = max(0, n - 18);
            int len = n - start;
            d.push_back(stoull(s.substr(start, len)));
            n -= 18;
        }
        trim();
    }

    void trim() {
        while (d.size() > 1 && d.back() == 0) d.pop_back();
    }

    bool operator<(const BigInt& o) const {
        if (d.size() != o.d.size()) return d.size() < o.d.size();
        for (size_t i = d.size(); i-- > 0; ) {
            if (d[i] != o.d[i]) return d[i] < o.d[i];
        }
        return false;
    }

    // Assumes *this >= o
    void sub(const BigInt& o) {
        uint64_t borrow = 0;
        for (size_t i = 0; i < d.size(); ++i) {
            uint64_t b = (i < o.d.size() ? o.d[i] : 0);
            if (d[i] < b + borrow) {
                d[i] = d[i] + BASE - b - borrow;
                borrow = 1;
            } else {
                d[i] = d[i] - b - borrow;
                borrow = 0;
            }
        }
        trim();
    }

    BigInt operator-(const BigInt& o) const {
        BigInt res = *this;
        res.sub(o);
        return res;
    }
};

struct Item {
    int id;
    BigInt val;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    string w_str;
    if (!(cin >> n >> w_str)) return 0;

    BigInt W(w_str);
    vector<Item> items(n);
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        items[i].id = i;
        items[i].val = BigInt(s);
    }

    vector<int> best_assignment(n, 0);
    BigInt best_diff = W;

    auto update_best = [&](const vector<int>& assignment, const BigInt& diff) {
        if (diff < best_diff) {
            best_diff = diff;
            best_assignment = assignment;
        }
    };

    // Sort descending for the initial deterministic pass
    sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
        return b.val < a.val;
    });

    vector<int> current_assignment(n);
    
    // Pass 1: Deterministic Greedy (Largest First)
    {
        fill(current_assignment.begin(), current_assignment.end(), 0);
        BigInt rem = W;
        for (const auto& item : items) {
            if (!(rem < item.val)) { // item.val <= rem
                rem.sub(item.val);
                current_assignment[item.id] = 1;
            } else {
                // If we can't add it, it means adding it exceeds W.
                // Check if the overshot solution is better than current best.
                // diff = (S + val) - W = val - (W - S) = val - rem
                BigInt diff = item.val - rem;
                if (diff < best_diff) {
                    current_assignment[item.id] = 1;
                    update_best(current_assignment, diff);
                    current_assignment[item.id] = 0;
                }
            }
        }
        update_best(current_assignment, rem);
    }

    // Pass 2+: Randomized Greedy
    mt19937 rng(1337);
    auto start_time = chrono::steady_clock::now();

    // Run for ~0.8 seconds to stay safely within typical limits
    while (true) {
        auto now = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 800) break;

        shuffle(items.begin(), items.end(), rng);
        fill(current_assignment.begin(), current_assignment.end(), 0);
        BigInt rem = W;

        for (const auto& item : items) {
            if (!(rem < item.val)) {
                rem.sub(item.val);
                current_assignment[item.id] = 1;
            } else {
                BigInt diff = item.val - rem;
                if (diff < best_diff) {
                    current_assignment[item.id] = 1;
                    update_best(current_assignment, diff);
                    current_assignment[item.id] = 0;
                }
            }
            // Optimization: exact match found
            if (rem.d.size() == 1 && rem.d[0] == 0) {
                update_best(current_assignment, rem);
                goto end;
            }
        }
        update_best(current_assignment, rem);
    }

end:
    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}