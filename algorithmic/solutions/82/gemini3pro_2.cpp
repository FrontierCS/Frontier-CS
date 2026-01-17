#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to perform a query
int query(int i, int j) {
    cout << "? " << i + 1 << " " << j + 1 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

int n;
mt19937 rng(1337); 

// Estimate the value of p[idx] using K random queries.
// The bitwise AND of (p[idx] | p[other]) for random 'other' converges to p[idx].
// K=16 gives a very high probability of correctness given the constraints.
int get_val(int idx) {
    int k = 16; 
    vector<int> others;
    others.reserve(n - 1);
    for (int i = 0; i < n; ++i) {
        if (i != idx) others.push_back(i);
    }
    
    // Pick k random unique indices from others
    if ((int)others.size() > k) {
        // We only need k random elements, so we can do a partial shuffle
        // or just pick k elements randomly.
        for (int i = 0; i < k; ++i) {
            uniform_int_distribution<int> dist(i, (int)others.size() - 1);
            int pick = dist(rng);
            swap(others[i], others[pick]);
        }
        others.resize(k);
    }
    
    int val = -1;
    for (int other : others) {
        int res = query(idx, other);
        if (val == -1) val = res;
        else val &= res;
    }
    return val;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Randomize processing order to avoid worst-case scenarios where 0 is at the end
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);

    // Initial candidate for 0
    int curr = order[0];
    int curr_val = get_val(curr);
    
    vector<int> p(n, -1);
    struct Info {
        int basis_val;
        int result;
    };
    // Stores the query result and the basis value used for that query
    vector<Info> history(n, {-1, -1});

    for (int i = 1; i < n; ++i) {
        int idx = order[i];
        int res = query(curr, idx);
        
        // If result equals curr_val, then p[idx] is a submask of p[curr].
        // Since values are distinct, p[idx] must be strictly smaller (or 0).
        // We swap to the better candidate.
        if (res == curr_val) {
            p[curr] = curr_val; // The old curr definitely has value curr_val
            curr = idx;
            curr_val = get_val(curr); // Determine value of new candidate
        } else {
            // Not a submask, store result to resolve later
            history[idx] = {curr_val, res};
        }
    }
    
    // The final candidate must be 0 (or the element 0)
    p[curr] = curr_val;
    int zero_idx = curr;
    
    // Resolve all other values
    for (int i = 0; i < n; ++i) {
        if (p[i] != -1) continue; // Already determined (was a previous curr)
        
        // If the basis used was 0, the result is the value (0 | x = x)
        if (history[i].basis_val == 0) {
            p[i] = history[i].result;
        } else {
            // Otherwise, we need to query against the found 0 to get the exact value
            p[i] = query(zero_idx, i);
        }
    }
    
    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}