#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

// Global cache for queries
// key: index, value: {a0, a1}
map<int, pair<int, int>> cache_res;
int n;
int max_sum = -1; // K, the sum a0+a1 for ordinary boxes (type v)

// Perform query or retrieve from cache
pair<int, int> ask(int i) {
    if (i < 0 || i >= n) return {-1, -1};
    if (cache_res.count(i)) return cache_res[i];
    
    cout << "? " << i << endl;
    int a0, a1;
    cin >> a0 >> a1;
    if (a0 == -1) exit(0); // Should not happen unless error
    
    cache_res[i] = {a0, a1};
    if (a0 + a1 == 0) {
        cout << "! " << i << endl;
        exit(0);
    }
    return {a0, a1};
}

// Function to find k specials in (L, R). 
// L and R are boundaries. L is a known ordinary box (or -1). 
// R is a known ordinary box (or n).
// We assume all specials in (L, R) are accounted for in k.
void solve(int L, int R, int k) {
    if (k <= 0) return;
    if (L + 1 >= R) return;
    
    int mid = (L + R) / 2;
    pair<int, int> res = ask(mid);
    int sum = res.first + res.second;
    
    if (sum == max_sum) {
        // mid is ordinary
        int cnt_L = (L == -1) ? 0 : cache_res[L].first;
        // The number of specials in (L, mid) is the difference in counts
        int left_k = res.first - cnt_L;
        int right_k = k - left_k;
        solve(L, mid, left_k);
        solve(mid, R, right_k);
    } else {
        // mid is special.
        // We found one special at mid.
        // Since mid is special, we cannot use its count to partition the problem directly.
        // We need to find a nearby ordinary box to establish a boundary.
        // We scan to the right of mid.
        
        int r_bound = mid + 1;
        while (r_bound < R) {
            pair<int, int> r_res = ask(r_bound);
            if (r_res.first + r_res.second == max_sum) break;
            r_bound++;
        }
        
        // Now r_bound is either an ordinary box or it reached R.
        // The range [mid, r_bound-1] consists entirely of special boxes.
        int cluster_size = r_bound - mid;
        
        // Determine count at r_bound
        int cnt_new;
        if (r_bound < n) {
             // If r_bound is a valid index, and we stopped there, it's ordinary.
             // If r_bound reached R, and R < n, R is ordinary, so we use its count.
             // If r_bound reached R, and R == n, we use max_sum.
             if (r_bound == R) {
                 if (R == n) cnt_new = max_sum;
                 else cnt_new = cache_res[R].first;
             } else {
                 cnt_new = cache_res[r_bound].first;
             }
        } else {
             cnt_new = max_sum;
        }
        
        int cnt_L = (L == -1) ? 0 : cache_res[L].first;
        
        // Calculate specials in (L, mid)
        // Total specials in (L, r_bound) is (cnt_new - cnt_L).
        // This includes (L, mid) + [mid, r_bound-1].
        // So specials in (L, mid) = (cnt_new - cnt_L) - cluster_size.
        int left_k = (cnt_new - cnt_L) - cluster_size;
        
        solve(L, mid, left_k);
        
        // Calculate specials in (r_bound, R)
        // We had k total in (L, R).
        // We found left_k in (L, mid).
        // We found cluster_size in [mid, r_bound-1].
        // Remaining is for (r_bound, R).
        int right_k = k - left_k - cluster_size;
        solve(r_bound, R, right_k);
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    if (n == 1) {
        cout << "! 0" << endl;
        return 0;
    }

    // 1. Determine K (max_sum) by sampling
    // Given the constraints, K < sqrt(N). With N=200000, K < 450.
    // Sampling 500 boxes is extremely likely to find an ordinary box.
    int sample = min(n, 500);
    for (int i = 0; i < sample; ++i) {
        pair<int, int> p = ask(i);
        int s = p.first + p.second;
        if (s > max_sum) max_sum = s;
    }

    // 2. Scan through the boxes using skipping
    int step = sqrt(n);
    if (step < 1) step = 1;
    // Step size optimization: roughly K log(Step) + N/Step. 
    // Max K ~450. Step ~450 is good.
    if (step > 500) step = 500; 

    int cur = -1;
    int cur_cnt = 0; // Virtual box -1 has 0 specials to the left
    
    while (cur < n) {
        int next_pos = cur + step;
        if (next_pos >= n) {
            // Processing tail up to n
            solve(cur, n, max_sum - cur_cnt);
            break;
        }
        
        pair<int, int> res = ask(next_pos);
        int s = res.first + res.second;
        
        if (s == max_sum) {
            // Ordinary box found, we can skip and solve the gap
            int next_cnt = res.first;
            int k = next_cnt - cur_cnt;
            solve(cur, next_pos, k);
            cur = next_pos;
            cur_cnt = next_cnt;
        } else {
            // Special box found. We can't use it to skip directly.
            // We scan linearly to the right to find an ordinary box to re-establish counts.
            int r_bound = next_pos + 1;
            while (r_bound < n) {
                pair<int, int> r_res = ask(r_bound);
                if (r_res.first + r_res.second == max_sum) break;
                r_bound++;
            }
            
            // Determine count at the new boundary
            int r_cnt;
            if (r_bound < n) r_cnt = ask(r_bound).first;
            else r_cnt = max_sum;
            
            // Calculate how many specials are in the gap (cur, next_pos)
            // Total specials in (cur, r_bound) is r_cnt - cur_cnt.
            // We know [next_pos, r_bound-1] are all specials (cluster).
            int cluster = r_bound - next_pos;
            int k = r_cnt - cur_cnt - cluster;
            
            solve(cur, next_pos, k);
            
            cur = r_bound;
            cur_cnt = r_cnt;
        }
        
        if (cur_cnt == max_sum) break; // Found all specials
    }

    // Fallback output, though logic guarantees exit inside ask()
    cout << "! 0" << endl;
    return 0;
}