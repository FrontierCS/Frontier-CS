#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>

using namespace std;

// Cache to store results of queries to minimize the number of interactions
map<pair<int, int>, int> cache_queries;

// Function to perform the query
int ask(int i, int j) {
    if (i > j) swap(i, j); // Ensure consistent ordering for cache
    if (i == j) return -1; // Should not happen in valid logic

    if (cache_queries.count({i, j})) {
        return cache_queries[{i, j}];
    }

    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) {
        exit(0); // Exit immediately if invalid query or limit exceeded
    }
    cache_queries[{i, j}] = res;
    return res;
}

int main() {
    // Standard I/O optimization
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Create a list of indices and shuffle them to process in random order
    // This helps in reducing the probability of worst-case scenarios
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 1);

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    shuffle(idx.begin(), idx.end(), rng);

    // Initial candidates a and b
    int a = idx[0];
    int b = idx[1];
    int val_ab = ask(a, b);

    // Tournament-like elimination to find the index of 0
    // Invariants: a and b are candidates for 0.
    // We aim to keep the pair with the smaller OR value.
    for (int i = 2; i < n; ++i) {
        int c = idx[i];
        int val_bc = ask(b, c);

        if (val_ab < val_bc) {
            // Case: (p[a] | p[b]) < (p[b] | p[c])
            // Implies c is not 0 (if c was 0, p[b]|p[c] == p[b] <= p[a]|p[b], contradiction)
            // Eliminate c, keep a and b.
            // val_ab remains valid for current pair (a, b).
        } else if (val_ab > val_bc) {
            // Case: (p[a] | p[b]) > (p[b] | p[c])
            // Implies a is not 0 (if a was 0, p[a]|p[b] == p[b] <= p[b]|p[c], contradiction)
            // Eliminate a, new pair is (b, c).
            a = b;
            b = c;
            val_ab = val_bc;
        } else {
            // Case: (p[a] | p[b]) == (p[b] | p[c])
            // Implies b is not 0 (if b was 0, p[a] == p[c], impossible in permutation)
            // Eliminate b, new pair is (a, c).
            // We need to query the value for (a, c).
            b = c;
            val_ab = ask(a, b);
        }
    }

    // Now we have two candidates a and b. One of them corresponds to the value 0.
    // We can distinguish them by checking against a random third element r.
    int zero_idx = -1;
    while (true) {
        int r = (rng() % n) + 1;
        while (r == a || r == b) {
            r = (rng() % n) + 1;
        }

        int val_ar = ask(a, r);
        int val_br = ask(b, r);

        if (val_ar != val_br) {
            // If a is 0, val_ar = p[r] and val_br = p[b] | p[r].
            // since p[b] != 0, typically val_ar < val_br. (val_ar <= val_br always holds).
            if (val_ar < val_br) {
                zero_idx = a;
            } else {
                zero_idx = b;
            }
            break;
        }
        // If val_ar == val_br, p[b] (if a=0) is a submask of p[r]. This is rare.
        // We repeat with a different r.
    }

    // Once we found the index with value 0, we can determine all other values
    // by asking ? zero_idx i, which returns 0 | p[i] = p[i].
    vector<int> ans(n + 1);
    ans[zero_idx] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        ans[i] = ask(zero_idx, i);
    }

    // Print the result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}