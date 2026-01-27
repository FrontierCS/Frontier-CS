#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to perform a query to the interactive judge
int query(int i, int j) {
    if (i == j) return -1; // Should not happen based on logic
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Incorrect query or limit exceeded
    return res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // We need to find the permutation p containing 0 to n-1.
    // The key is to find the index of 0 efficiently.
    // We use a randomized elimination strategy.

    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Shuffle indices to ensure average case complexity
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    // We maintain two candidates 'a' and 'b' and their OR sum 'v'.
    // We iterate through the rest of the elements to eliminate non-zeros.
    int a = p[0];
    int b = p[1];
    int v = query(a, b);

    for (int i = 2; i < n; ++i) {
        int c = p[i];
        int u = query(b, c);

        if (v < u) {
            // b|c > a|b implies c adds more/higher bits to b than a does.
            // Since 0 | x = x (minimal increase), a larger result suggests c is less likely to be 0.
            // We eliminate c. 'a' and 'b' remain candidates. 'v' stays valid for (a,b).
            // Cost: 1 query.
        } else if (u < v) {
            // b|c < a|b implies a adds more bits to b.
            // We eliminate a.
            // c becomes the new candidate replacing a.
            // 'u' is the value for query(b, c).
            a = c;
            v = u;
            // Cost: 1 query.
        } else {
            // u == v, i.e., a|b == c|b.
            // If b was 0, then a|0 = a and c|0 = c. Since elements are distinct, a != c.
            // Thus a|b cannot equal c|b if b=0.
            // Therefore, b cannot be 0. We safe eliminate b.
            // We update b to c and must recompute v = query(a, b).
            b = c;
            v = query(a, b);
            // Cost: 2 queries. This case is statistically rare.
        }
    }

    // Now 0 is either at index 'a' or 'b'.
    // We distinguish them by comparing with a random third index 'k'.
    int zero_idx = -1;
    while (true) {
        int k = (rng() % n) + 1;
        while (k == a || k == b) {
            k = (rng() % n) + 1;
        }

        int val_a = query(a, k);
        int val_b = query(b, k);

        if (val_a < val_b) {
            // a|k < b|k -> a is likely 0
            zero_idx = a;
            break;
        } else if (val_b < val_a) {
            // b|k < a|k -> b is likely 0
            zero_idx = b;
            break;
        }
        // If equal, k acts as a supermask for both or similar, loop again with new k.
    }

    // Construct the answer array
    vector<int> ans(n + 1);
    ans[zero_idx] = 0;
    
    // Determine all other elements by querying against the zero index
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        // p[i] | 0 = p[i]
        ans[i] = query(zero_idx, i);
    }

    // Output result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}