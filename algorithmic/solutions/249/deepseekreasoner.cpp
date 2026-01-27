#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>
#include <ctime>

using namespace std;

// Memoization map to prevent repeating queries
map<pair<int, int>, int> memo;

// Helper function to perform query
int query(int i, int j) {
    if (i > j) swap(i, j);
    if (i == j) return -1; 
    if (memo.count({i, j})) return memo[{i, j}];
    
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return memo[{i, j}] = res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // We will process indices 1 to n
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);

    // Shuffle the order to randomize the tournament
    mt19937 rng(1337);
    shuffle(order.begin(), order.end(), rng);

    int cand = order[0];
    int pivot = order[1];
    
    int val_cand = query(cand, pivot);

    // Tournament to find the index of 0
    for (int i = 1; i < n; ++i) {
        int chall = order[i];
        if (chall == pivot) continue;

        int val_chall = query(chall, pivot);

        if (val_chall < val_cand) {
            cand = chall;
            val_cand = val_chall;
        } else if (val_chall == val_cand) {
            // Tie break: current cand and challenger perform identically against pivot.
            // We pick a new random pivot to distinguish them.
            int new_p = -1;
            while (true) {
                int r = order[rng() % n];
                if (r != cand && r != chall) {
                    new_p = r;
                    break;
                }
            }
            
            int v1 = query(cand, new_p);
            int v2 = query(chall, new_p);
            
            // If challenger is 'smaller' (better candidate for 0), take it.
            // Also update the pivot to the new discriminator.
            if (v2 < v1) {
                cand = chall;
                val_cand = v2;
                pivot = new_p;
            } else {
                val_cand = v1;
                pivot = new_p;
            }
        }
    }

    // It's possible that 0 ended up as the 'pivot' and was never compared as a challenger,
    // or we are just verifying. We compare 'cand' and 'pivot' using random checkers.
    int zero_idx = cand;
    for (int iter = 0; iter < 30; ++iter) {
        int checker = -1;
        while(true) {
            int r = order[rng() % n];
            if (r != cand && r != pivot) {
                checker = r;
                break;
            }
        }
        int v_cand = query(cand, checker);
        int v_pivot = query(pivot, checker);
        
        if (v_pivot < v_cand) {
            zero_idx = pivot;
            break;
        } else if (v_cand < v_pivot) {
            zero_idx = cand;
            break;
        }
    }

    // Reconstruct the permutation knowing the position of 0
    vector<int> result(n + 1);
    result[zero_idx] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        result[i] = query(i, zero_idx);
    }
    
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << result[i];
    }
    cout << endl;

    return 0;
}