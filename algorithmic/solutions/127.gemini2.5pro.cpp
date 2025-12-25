#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Global variables for interaction
int n;

// Query function
pair<int, int> query(int i) {
    cout << "? " << i << endl;
    int a0, a1;
    cin >> a0 >> a1;
    if (a0 == -1 && a1 == -1) exit(0); // Judge error signal
    return {a0, a1};
}

// Answer function
void answer(int i) {
    cout << "! " << i << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;

    int p_best = -1;
    long long s_ub = n + 1;

    // Phase 1: Iteratively find a box with a better prize type.
    // The number of distinct prize types is very small. After a few iterations,
    // this will find a box with a type 2 prize, for which S=1.
    for (int i = 0; i < 8 && s_ub != 0; ++i) {
        int l = 0, r = n - 1;
        int first_better = -1;

        // Binary search for the first index i with S_i < s_ub
        while (l <= r) {
            int mid = l + (r - l) / 2;
            pair<int, int> res = query(mid);
            if (res.first + res.second < s_ub) {
                first_better = mid;
                r = mid - 1;
            } else {
                l = mid + 1;
            }
        }

        if (first_better == -1) {
            // No prize found is better than the one at p_best. This means p_best
            // holds a type 2 prize (S=1), and we couldn't find the diamond (S=0).
            break;
        }

        p_best = first_better;
        // A single query at first_better is enough to get its S value.
        // Caching the value from the BS would be an optimization.
        pair<int, int> res = query(p_best);
        s_ub = res.first + res.second;
    }
    
    if (s_ub == 0) {
        answer(p_best);
        return 0;
    }

    // Phase 2: p_best now holds a type 2 prize (S=1). The diamond is the only
    // prize better than type 2. A query at p_best tells us if the diamond
    // is to the left or right.
    pair<int, int> res = query(p_best);
    int l, r;
    if (res.first == 1) {
        l = 0;
        r = p_best - 1;
    } else {
        l = p_best + 1;
        r = n - 1;
    }

    // Phase 3: Find the diamond in the range [l, r]. The diamond has S=0.
    // Any other prize in this range must be of type > 2, so its S >= 3.
    // We can use p_best as a reference to guide a binary search.
    while (l <= r) {
        if (l == r) {
            answer(l);
            return 0;
        }
        int mid = l + (r - l) / 2;
        res = query(mid);
        long long s_mid = res.first + res.second;

        if (s_mid == 0) {
            answer(mid);
            return 0;
        }

        // T_mid > T_p_best. So p_best is "better" than mid.
        // The set of s_mid items better than T_mid contains p_best and the diamond.
        // We can deduce the diamond's location relative to mid by analyzing a0.
        int diamond_candidates_left;
        if (p_best < mid) {
            // p_best is in [0, mid-1], so it contributes to a0.
            // All other a0-1 items better than T_mid are also in [0, mid-1].
            diamond_candidates_left = res.first - 1;
        } else { // p_best > mid
            // p_best is in [mid+1, n-1], not contributing to a0.
            diamond_candidates_left = res.first;
        }
        
        // This logic works because we know there's only one other "good" item (diamond)
        // and we start our search range [l, r] from an edge (0 or p_best+1), so
        // counts in [0, mid-1] correctly reflect counts in [l, mid-1].
        if (diamond_candidates_left > 0) {
            r = mid - 1;
        } else {
            l = mid + 1;
        }
    }
    
    return 0;
}