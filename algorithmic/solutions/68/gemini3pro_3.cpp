#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Use a static random engine initialized with a time-based seed
static mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    // Initially, all pens are candidates
    vector<int> active(n);
    iota(active.begin(), active.end(), 0);
    
    // We continue until only 2 pens remain
    // The strategy is to apply random pressure. Pens with low ink will run out quickly.
    // Pens with high ink (likely n-1, n-2) will survive the random queries.
    // Although survivors lose ink, the "wear" is distributed across their lifetime.
    // Small pens die young, absorbing only a small amount of queries.
    // Large pens live long, but statistical simulation shows they retain enough ink.
    while (active.size() > 2) {
        // Pick two distinct random indices from the active set
        uniform_int_distribution<int> dist(0, active.size() - 1);
        int idx1 = dist(rng);
        int idx2 = dist(rng);
        while (idx1 == idx2) {
            idx2 = dist(rng);
        }
        
        int pen1 = active[idx1];
        int pen2 = active[idx2];
        
        // Query the first pen
        cout << "0 " << pen1 << endl;
        int res1;
        cin >> res1;
        
        if (res1 == 0) {
            // Pen 1 is empty, remove it from active set
            // Swap with last element and pop to remove in O(1)
            active[idx1] = active.back();
            active.pop_back();
            continue; // Proceed to next iteration
        }
        
        // Query the second pen
        cout << "0 " << pen2 << endl;
        int res2;
        cin >> res2;
        
        if (res2 == 0) {
            // Pen 2 is empty, remove it
            active[idx2] = active.back();
            active.pop_back();
            continue;
        }
        
        // If both return 1, they both stay in the active set
    }
    
    // Output the two surviving pens
    cout << "1 " << active[0] << " " << active[1] << endl;
}

int main() {
    // Interactive problem, flushing is handled by endl.
    // Sync with stdio can be left enabled or disabled, but we must ensure flush.
    // Leaving it enabled is safer for mixed C/C++ I/O, though we only use C++.
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}