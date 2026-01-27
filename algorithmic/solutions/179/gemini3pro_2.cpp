#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// BigInt structure with base 10^9
const int BASE = 1000000000;

struct BigInt {
    vector<int> d;
    
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
                d.push_back(stoi(s.substr(0, i)));
            else
                d.push_back(stoi(s.substr(i - 9, 9)));
        }
        trim();
    }
    
    void trim() {
        while (d.size() > 1 && d.back() == 0) d.pop_back();
    }
    
    bool operator<(const BigInt& o) const {
        if (d.size() != o.d.size()) return d.size() < o.d.size();
        for (int i = (int)d.size() - 1; i >= 0; i--)
            if (d[i] != o.d[i]) return d[i] < o.d[i];
        return false;
    }
    
    bool operator>(const BigInt& o) const { return o < *this; }
    bool operator<=(const BigInt& o) const { return !(*this > o); }
    bool operator>=(const BigInt& o) const { return !(*this < o); }
    bool operator==(const BigInt& o) const { return d == o.d; }
    bool operator!=(const BigInt& o) const { return !(*this == o); }

    BigInt operator+(const BigInt& o) const {
        BigInt res;
        int n = max(d.size(), o.d.size());
        res.d.resize(n, 0);
        long long carry = 0;
        for (int i = 0; i < n || carry; ++i) {
            if (i == (int)res.d.size()) res.d.push_back(0);
            long long sum = carry + (i < (int)d.size() ? d[i] : 0) + (i < (int)o.d.size() ? o.d[i] : 0);
            res.d[i] = sum % BASE;
            carry = sum / BASE;
        }
        return res;
    }

    // Assume *this >= o
    BigInt operator-(const BigInt& o) const {
        BigInt res;
        res.d = d;
        long long borrow = 0;
        for (size_t i = 0; i < o.d.size() || borrow; ++i) {
            long long val = res.d[i] - borrow - (i < (int)o.d.size() ? o.d[i] : 0);
            if (val < 0) {
                val += BASE;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.d[i] = val;
        }
        res.trim();
        return res;
    }
};

BigInt abs_diff(const BigInt& a, const BigInt& b) {
    if (a >= b) return a - b;
    else return b - a;
}

struct Item {
    int id;
    BigInt val;
};

int n;
BigInt W;
vector<Item> items;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    string s; cin >> s; W = BigInt(s);
    
    items.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> s;
        items[i].val = BigInt(s);
        items[i].id = i;
    }

    // Sort descending for the first deterministic pass
    sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
        return a.val > b.val;
    });

    vector<int> best_b(n, 0);
    BigInt best_diff = W; 

    auto start_time = chrono::steady_clock::now();
    mt19937 rng(1337);

    // Strategy: 
    // 1. Run greedy on descending sorted items.
    // 2. Run greedy on randomly shuffled items repeatedly.
    // 3. Greedy decision: if taking an item reduces the absolute difference |W - S|, take it.
    
    bool first = true;
    while (true) {
        if (!first) {
            auto curr_time = chrono::steady_clock::now();
            if (chrono::duration_cast<chrono::milliseconds>(curr_time - start_time).count() > 1800) break;
            shuffle(items.begin(), items.end(), rng);
        }

        BigInt curr_sum(0);
        BigInt curr_diff = W;
        vector<int> curr_b(n, 0); 
        
        for (int i = 0; i < n; ++i) {
            BigInt next_sum = curr_sum + items[i].val;
            BigInt next_diff = abs_diff(W, next_sum);
            
            // Acceptance criterion: only if strictly better
            if (next_diff < curr_diff) {
                curr_sum = next_sum;
                curr_diff = next_diff;
                curr_b[i] = 1;
            }
        }

        if (curr_diff < best_diff) {
            best_diff = curr_diff;
            fill(best_b.begin(), best_b.end(), 0);
            for(int i=0; i<n; ++i) if(curr_b[i]) best_b[items[i].id] = 1;
            // If we found an exact match, stop
            if (best_diff.d.size() == 1 && best_diff.d[0] == 0) break;
        }

        first = false;
    }

    for (int i = 0; i < n; ++i) {
        cout << best_b[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}