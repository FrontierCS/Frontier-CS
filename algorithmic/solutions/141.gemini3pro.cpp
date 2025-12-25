#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    vector<int> active(n);
    iota(active.begin(), active.end(), 1);

    int max_ops = 100000;
    int current_ops = 0;

    // Initialize random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    while (true) {
        int sz = active.size();
        if (sz == 0) break; 

        // Check if we can afford another pass
        // A pass requires 1 reset + sz queries.
        if (current_ops + 1 + sz > max_ops) break;

        // If the number of remaining candidates fits in memory,
        // we can perform a definitive check in one pass.
        // Memory stores k elements. If sz <= k, no element will be evicted
        // before all elements are compared against all previous ones in this pass.
        if (sz <= k) {
            cout << "R" << endl;
            current_ops++;
            vector<int> next_active;
            for (int x : active) {
                cout << "? " << x << endl;
                current_ops++;
                char resp;
                cin >> resp;
                if (resp == 'N') {
                    next_active.push_back(x);
                }
            }
            active = next_active;
            break; // Deterministic result found
        }

        // Perform a probabilistic filter pass with random shuffle
        shuffle(active.begin(), active.end(), rng);
        
        cout << "R" << endl;
        current_ops++;
        
        vector<int> next_active;
        bool changed = false;
        for (int x : active) {
            cout << "? " << x << endl;
            current_ops++;
            char resp;
            cin >> resp;
            if (resp == 'N') {
                next_active.push_back(x);
            } else {
                changed = true;
            }
        }

        active = next_active;

        // We continue shuffling and filtering until we run out of budget or satisfy sz <= k.
        // Even if 'changed' is false, there might be duplicates hidden by the current permutation order,
        // especially when k is small. So we persist.
    }

    cout << "! " << active.size() << endl;

    return 0;
}