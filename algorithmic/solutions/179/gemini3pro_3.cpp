#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Base for BigInt: 10^9
const int BASE = 1000000000;

struct BigInt {
    vector<int> limbs;

    BigInt() {}
    BigInt(long long v) {
        if (v == 0) limbs.push_back(0);
        while (v > 0) {
            limbs.push_back(v % BASE);
            v /= BASE;
        }
    }

    BigInt(string s) {
        if (s.empty()) { limbs.push_back(0); return; }
        size_t first = s.find_first_not_of('0');
        if (first == string::npos) { limbs.push_back(0); return; }
        s = s.substr(first);
        
        for (int i = (int)s.length(); i > 0; i -= 9) {
            if (i < 9)
                limbs.push_back(stoi(s.substr(0, i)));
            else
                limbs.push_back(stoi(s.substr(i - 9, 9)));
        }
    }

    bool operator<(const BigInt& other) const {
        if (limbs.size() != other.limbs.size())
            return limbs.size() < other.limbs.size();
        for (int i = (int)limbs.size() - 1; i >= 0; --i) {
            if (limbs[i] != other.limbs[i])
                return limbs[i] < other.limbs[i];
        }
        return false;
    }
    
    // Assumes non-negative result
    BigInt operator+(const BigInt& other) const {
        BigInt res;
        int carry = 0;
        size_t n = max(limbs.size(), other.limbs.size());
        res.limbs.reserve(n + 1);
        for (size_t i = 0; i < n || carry; ++i) {
            long long sum = (long long)carry + (i < limbs.size() ? limbs[i] : 0) + (i < other.limbs.size() ? other.limbs[i] : 0);
            if (sum >= BASE) {
                res.limbs.push_back(sum - BASE);
                carry = 1;
            } else {
                res.limbs.push_back(sum);
                carry = 0;
            }
        }
        return res;
    }

    // Assumes *this >= other
    BigInt operator-(const BigInt& other) const {
        BigInt res;
        int borrow = 0;
        size_t n = limbs.size();
        res.limbs.reserve(n);
        for (size_t i = 0; i < n; ++i) {
            long long diff = (long long)limbs[i] - borrow - (i < other.limbs.size() ? other.limbs[i] : 0);
            if (diff < 0) {
                diff += BASE;
                borrow = 1;
            } else {
                borrow = 0;
            }
            res.limbs.push_back(diff);
        }
        while (res.limbs.size() > 1 && res.limbs.back() == 0) {
            res.limbs.pop_back();
        }
        return res;
    }
    
    bool is_zero() const {
        return limbs.size() == 1 && limbs[0] == 0;
    }
    
    static BigInt abs_diff(const BigInt& a, const BigInt& b) {
        if (a < b) return b - a;
        return a - b;
    }
};

struct Item {
    int id;
    BigInt val;
};

int n;
BigInt W;
vector<Item> items;
vector<int> best_sol;
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

    best_sol.assign(n, 0);
    best_diff = W;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Prepare items for shuffling
    vector<Item> p_items = items;
    // Initial sort: Descending
    sort(p_items.begin(), p_items.end(), [](const Item& a, const Item& b){
        return b.val < a.val; 
    });

    auto start_time = chrono::steady_clock::now();
    bool first = true;
    
    while (true) {
        // Time limit check (approx 1.8s)
        if (!first) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 1800) break;
            // Shuffle for subsequent iterations
            shuffle(p_items.begin(), p_items.end(), rng);
        }

        BigInt current_sum(0);
        vector<int> current_sol(n, 0);

        // Greedy Construction
        for (const auto& item : p_items) {
            if (current_sum < W) {
                BigInt rem = W - current_sum;
                BigInt limit = rem + rem;
                if (item.val < limit) {
                    current_sum = current_sum + item.val;
                    current_sol[item.id] = 1;
                }
            }
        }
        
        BigInt diff = BigInt::abs_diff(W, current_sum);
        if (diff < best_diff) {
            best_diff = diff;
            best_sol = current_sol;
            if (best_diff.is_zero()) break;
        }
        
        // Local Search (Hill Climbing)
        bool improved = true;
        while (improved) {
            improved = false;
            // Check time inside heavy loop
            if ((chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() > 1800)) break;

            for (int i = 0; i < n; ++i) {
                if (current_sum < W) {
                    // Try ADD
                    if (current_sol[i] == 0) {
                        BigInt rem = W - current_sum;
                        BigInt limit = rem + rem;
                        if (items[i].val < limit) {
                             current_sum = current_sum + items[i].val;
                             current_sol[i] = 1;
                             improved = true;
                        }
                    }
                } else if (W < current_sum) {
                    // Try REMOVE
                    if (current_sol[i] == 1) {
                         BigInt exc = current_sum - W;
                         BigInt limit = exc + exc;
                         if (items[i].val < limit) {
                             current_sum = current_sum - items[i].val;
                             current_sol[i] = 0;
                             improved = true;
                         }
                    }
                } else {
                    // Found exact match
                    goto finish;
                }
            }
            
            BigInt d = BigInt::abs_diff(W, current_sum);
            if (d < best_diff) {
                best_diff = d;
                best_sol = current_sol;
                if (best_diff.is_zero()) goto finish;
            }
        }

        first = false;
    }

finish:
    for (int i = 0; i < n; ++i) {
        cout << best_sol[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}