#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>
#include <cassert>

using namespace std;

// ---------- Big Integer Utilities ----------
// Since numbers can be up to 10^1100, we represent them as strings.
// We only need addition and comparison.

// Remove leading zeros from a string representation of a non‑negative integer.
string strip_leading_zeros(const string& s) {
    size_t i = 0;
    while (i < s.size() && s[i] == '0') ++i;
    if (i == s.size()) return "0";
    return s.substr(i);
}

// Compare two non‑negative integer strings.
// Returns: -1 if a < b, 0 if a == b, 1 if a > b.
int compare(const string& a, const string& b) {
    string sa = strip_leading_zeros(a);
    string sb = strip_leading_zeros(b);
    if (sa.size() != sb.size()) {
        return sa.size() < sb.size() ? -1 : 1;
    }
    if (sa < sb) return -1;
    if (sa > sb) return 1;
    return 0;
}

// Add two non‑negative integer strings.
string add(const string& a, const string& b) {
    string sa = strip_leading_zeros(a);
    string sb = strip_leading_zeros(b);
    int i = sa.size() - 1, j = sb.size() - 1;
    int carry = 0;
    string res;
    while (i >= 0 || j >= 0 || carry) {
        int d1 = i >= 0 ? sa[i--] - '0' : 0;
        int d2 = j >= 0 ? sb[j--] - '0' : 0;
        int sum = d1 + d2 + carry;
        res.push_back('0' + (sum % 10));
        carry = sum / 10;
    }
    reverse(res.begin(), res.end());
    return strip_leading_zeros(res);
}

// Subtract two non‑negative integer strings, assuming a >= b.
string subtract(const string& a, const string& b) {
    string sa = strip_leading_zeros(a);
    string sb = strip_leading_zeros(b);
    if (sa == sb) return "0";
    int i = sa.size() - 1, j = sb.size() - 1;
    int borrow = 0;
    string res;
    while (i >= 0) {
        int d1 = sa[i--] - '0' - borrow;
        int d2 = j >= 0 ? sb[j--] - '0' : 0;
        if (d1 < d2) {
            d1 += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        res.push_back('0' + (d1 - d2));
    }
    while (res.back() == '0') res.pop_back();
    reverse(res.begin(), res.end());
    return strip_leading_zeros(res);
}

// Returns |a - b| as a string.
string absolute_diff(const string& a, const string& b) {
    int cmp = compare(a, b);
    if (cmp == 0) return "0";
    if (cmp > 0) return subtract(a, b);
    return subtract(b, a);
}

// ---------- Subset Selection ----------
struct Item {
    string val;
    int idx;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string W;
    cin >> n >> W;

    vector<Item> items(n);
    for (int i = 0; i < n; ++i) {
        cin >> items[i].val;
        items[i].idx = i;
    }

    // Find maximum element M (as string)
    string M = "0";
    for (const auto& it : items) {
        if (compare(it.val, M) > 0) M = it.val;
    }

    // We will use a greedy randomized approach.
    // 1. Sort items by value (largest first) to try to get close to W quickly.
    // 2. Run multiple random permutations and keep the best subset.
    // 3. The score is 1 - |W-S|/(W+M). Since W and M are fixed,
    //    minimizing |W-S| maximizes the score.
    // We'll do a limited number of trials (enough to be fast, but enough to get a good solution).

    const int TRIALS = 100;  // adjust if needed (n <= 2100, 100 trials is fine)
    unsigned seed = chrono::system_clock::now().time_since_epoch().count();
    mt19937 rng(seed);

    string best_diff = add(W, M);  // an upper bound for |W-S|
    vector<bool> best_subset(n, false);

    // Precompute total sum of all items (to possibly break early)
    string total_sum = "0";
    for (const auto& it : items) total_sum = add(total_sum, it.val);

    // If total sum <= W, take everything.
    if (compare(total_sum, W) <= 0) {
        for (int i = 0; i < n; ++i) cout << "1 ";
        cout << "\n";
        return 0;
    }

    // Run trials
    for (int t = 0; t < TRIALS; ++t) {
        shuffle(items.begin(), items.end(), rng);
        string cur_sum = "0";
        vector<bool> cur_subset(n, false);

        // Greedy: take an item if it doesn't exceed W (or if it gets us closer?)
        // Actually, we want to minimize |W - S|, so we take if |W - (S+val)| < |W - S|.
        for (const auto& it : items) {
            string new_sum = add(cur_sum, it.val);
            string diff_old = absolute_diff(W, cur_sum);
            string diff_new = absolute_diff(W, new_sum);
            if (compare(diff_new, diff_old) <= 0) {
                cur_sum = new_sum;
                cur_subset[it.idx] = true;
            }
        }

        string diff = absolute_diff(W, cur_sum);
        if (compare(diff, best_diff) < 0) {
            best_diff = diff;
            best_subset = cur_subset;
        }
        // Early exit if we hit exactly W
        if (best_diff == "0") break;
    }

    // Output the best subset found
    for (int i = 0; i < n; ++i) {
        cout << (best_subset[i] ? "1" : "0") << " \n"[i == n-1];
    }

    return 0;
}