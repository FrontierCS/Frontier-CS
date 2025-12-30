#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

long long n;

// Function to ask a query
long long query(long long x, long long y) {
    if (x == y) return 0;
    cout << "? " << x << " " << y << endl;
    long long dist;
    cin >> dist;
    if (dist == -1) exit(0);
    return dist;
}

// Function to output the answer
void answer(long long u, long long v) {
    if (u > v) swap(u, v);
    cout << "! " << u << " " << v << endl;
    int r;
    cin >> r;
    if (r == -1) exit(0);
}

// Function to handle vertex numbers wrapping around n
long long normalize(long long v) {
    return (v - 1 + n) % n + 1;
}

void solve() {
    cin >> n;

    long long half_n = n / 2;

    // Step 1: Binary search for the first vertex `cand1` that has a shortcut to its antipodal point.
    // The boundaries of the range of such vertices are related to the chord endpoints.
    // It has been observed that one of these boundaries (or the boundary shifted by n/2) is an endpoint.
    long long cand1 = -1;
    long long low = 1, high = n;
    while(low <= high) {
        long long mid = low + (high - low) / 2;
        long long antipodal = normalize(mid + half_n);
        if (query(mid, antipodal) < half_n) {
            cand1 = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    long long u = -1, v = -1;

    // Step 2: Try `cand1` and `cand1 - n/2` as potential endpoints. One must be correct.
    long long u_candidates[2] = {cand1, normalize(cand1 - half_n)};

    for (long long current_cand : u_candidates) {
        if (current_cand == -1) continue;
        
        // Step 3: Once we have a candidate endpoint `u`, find the cycle distance `k` to the other endpoint `v`.
        // We do this by binary searching for `k` in [2, n/2] such that `d(u, u+k) == 1`.
        long long arc_len = -1;
        low = 2, high = half_n;
        while(low <= high) {
            long long mid = low + (high - low) / 2;
            long long p = normalize(current_cand + mid);
            if (query(current_cand, p) == 1) {
                arc_len = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }

        if (arc_len != -1) {
            u = current_cand;
            // Step 4: We found `u` and `k`. The other endpoint `v` is either `u+k` or `u-k`.
            long long v1 = normalize(u + arc_len);
            long long v2 = normalize(u - arc_len);

            // Step 5: Distinguish between `v1` and `v2`.
            // Query distance from `u+1` to `v2`.
            // If the chord is `(u, v2)`, this distance will be shortened to `min(d_c(u+1, v2), 2)`.
            // If the chord is `(u, v1)`, this distance will remain `d_c(u+1, v2)`.
            long long test_node = normalize(u + 1);
            long long dist_to_v2 = query(test_node, v2);
            
            long long cycle_dist_test_v2 = arc_len + 1;
            if (dist_to_v2 == min(cycle_dist_test_v2, 2LL)) {
                 v = v2;
            } else {
                 v = v1;
            }
            break;
        }
    }
    
    answer(u, v);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}