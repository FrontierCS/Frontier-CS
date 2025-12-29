#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cstdlib>
#include <ctime>
#include <random>

using namespace std;

// Map to cache query results to avoid redundant queries
map<int, pair<int, int>> cache_res;

// Function to query index i
// Automatically exits if diamond is found
pair<int, int> query(int i) {
    if (cache_res.count(i)) return cache_res[i];
    
    cout << "? " << i << endl;
    int a, b;
    cin >> a >> b;
    if (a == -1) {
        exit(0); // Should not happen based on problem statement
    }
    
    cache_res[i] = {a, b};
    
    // Check if diamond found (0 items more expensive on left and right)
    if (a == 0 && b == 0) {
        cout << "! " << i << endl;
        exit(0);
    }
    return {a, b};
}

int K_total = -1;

// Recursive solver
// L, R: current range
// k_in: number of "special" items in this range
// pre_L: number of "special" items strictly to the left of L (in 0...L-1)
void solve(int L, int R, int k_in, int pre_L) {
    if (k_in <= 0 || L > R) return;

    int mid = L + (R - L) / 2;
    pair<int, int> res = query(mid);
    int sum = res.first + res.second;

    if (sum == K_total) {
        // mid is a "normal" box (type v)
        // It provides exact counts for splitting
        // res.first is the total number of specials in [0, mid-1]
        // So specials in [L, mid-1] is (res.first - pre_L)
        int in_left = res.first - pre_L;
        solve(L, mid - 1, in_left, pre_L);
        solve(mid + 1, R, k_in - in_left, res.first);
    } else {
        // mid is a "special" box (type < v)
        // We cannot use its counts to split k_in effectively because its counts
        // refer to a subset of types (better than its own type).
        // We need to find a "normal" box in the range to act as a pivot.
        
        int pivot = -1;
        pair<int, int> p_res;
        
        // Try searching to the right for a normal box
        for (int i = mid + 1; i <= R; ++i) {
            pair<int, int> r = query(i);
            if (r.first + r.second == K_total) {
                pivot = i;
                p_res = r;
                break;
            }
        }
        
        if (pivot != -1) {
            int in_left = p_res.first - pre_L;
            solve(L, pivot - 1, in_left, pre_L);
            solve(pivot + 1, R, k_in - in_left, p_res.first);
            return;
        }
        
        // If not found, try searching to the left
        for (int i = mid - 1; i >= L; --i) {
            pair<int, int> r = query(i);
            if (r.first + r.second == K_total) {
                pivot = i;
                p_res = r;
                break;
            }
        }
        
        if (pivot != -1) {
            int in_left = p_res.first - pre_L;
            solve(L, pivot - 1, in_left, pre_L);
            solve(pivot + 1, R, k_in - in_left, p_res.first);
            return;
        }
        
        // If still not found, then ALL boxes in [L, R] are special.
        // We have already queried all of them in the loops above.
        // Since query() exits on finding the diamond (sum==0),
        // and we haven't exited, the diamond is not in [L, R].
        return;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int N;
    if (!(cin >> N)) return 0;
    
    // Setup random generator
    mt19937 rng(time(0));
    uniform_int_distribution<int> dist(0, N - 1);

    // Find the background sum K_total.
    // Most items are of the cheapest type v.
    // Querying random items will give us the count of all items better than v (K_total).
    // We take the maximum sum observed.
    int limit = 45; 
    for (int i = 0; i < limit; ++i) {
        int idx = dist(rng);
        pair<int, int> r = query(idx);
        if (r.first + r.second > K_total) {
            K_total = r.first + r.second;
        }
    }

    // Start the recursive search
    solve(0, N - 1, K_total, 0);

    // Fallback if not found (should be unreachable given constraints)
    cout << "! 0" << endl;
    return 0;
}