#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

long long n;

long long query(long long x, long long y) {
    if (x == y) return 0;
    if (x < 1 || x > n || y < 1 || y > n) {
        return -1; // Should not happen
    }
    cout << "? " << x << " " << y << endl;
    long long dist;
    cin >> dist;
    if (dist == -1) exit(0);
    return dist;
}

void answer(long long u, long long v) {
    if (u > v) swap(u, v);
    cout << "! " << u << " " << v << endl;
    int r;
    cin >> r;
    if (r == -1) exit(0);
}

long long dist_cycle(long long u, long long v) {
    if (u < 1 || u > n || v < 1 || v > n) return -1;
    long long diff = abs(u - v);
    return min(diff, n - diff);
}

void solve() {
    cin >> n;

    long long p1 = 1;
    long long p2 = -1;

    // Ternary search for p2, a vertex maximally distant from p1
    long long l = 2, r = n;
    long long d_p2_val = -1;
    for (int i = 0; i < 80; ++i) {
        if (l > r) break;
        long long m1 = l + (r - l) / 3;
        long long m2 = r - (r - l) / 3;
        if (m1 >= m2) break;
        long long d1 = query(p1, m1);
        long long d2 = query(p1, m2);
        if (d1 > d_p2_val) { d_p2_val = d1; p2 = m1; }
        if (d2 > d_p2_val) { d_p2_val = d2; p2 = m2; }
        if (d1 < d2) {
            l = m1 + 1;
        } else {
            r = m2 - 1;
        }
    }
    
    long long final_p2 = p2;
    long long max_d = d_p2_val;
    if(l <= r){
        for(long long i = l; i <= r; ++i) {
            long long d = query(p1, i);
            if (d > max_d) {
                max_d = d;
                final_p2 = i;
            }
        }
    }
    p2 = final_p2;
    d_p2_val = max_d;
    
    long long d_p1_p2 = query(p1, p2);

    // Binary search for a midpoint m on a shortest path between p1 and p2
    long long m = -1;
    l = 1, r = n;
    long long target_dist = d_p1_p2 / 2;
    
    // Find a point m roughly in the middle of a shortest path
    // Any point on a shortest path works as a good reference.
    long long best_m = -1;
    long long min_diff = -1;

    for(int i=0; i<40; i++){
        long long mid = l + (r-l)/2;
        if(mid < 1 || mid > n) break;
        long long d = query(p1, mid);
        long long d_p2_m = query(p2, mid);
        if(d + d_p2_m == d_p1_p2){
            m = mid;
            break;
        }
        if(min_diff == -1 || abs(d-target_dist) < min_diff){
            min_diff = abs(d-target_dist);
            best_m = mid;
        }
        if(d < target_dist) l = mid+1;
        else r = mid-1;
    }

    if (m == -1) m = best_m;
    if (m == -1) m = n/2 + 1; // Fallback


    // Ternary search for one endpoint u from m's perspective
    // maximizing path shortening
    long long u = -1;
    long long max_saving = 0;
    l = 1, r = n;
    for (int i = 0; i < 80; ++i) {
        if (l > r) break;
        long long m1 = l + (r - l) / 3;
        long long m2 = r - (r - l) / 3;
        if (m1 >= m2) break;
        if (m1 == m) m1++;
        if (m2 == m) m2--;
        if (m1 >= m2) break;

        long long saving1 = dist_cycle(m, m1) - query(m, m1);
        long long saving2 = dist_cycle(m, m2) - query(m, m2);

        if (saving1 > max_saving) { max_saving = saving1; u = m1; }
        if (saving2 > max_saving) { max_saving = saving2; u = m2; }

        if (saving1 < saving2) {
            l = m1 + 1;
        } else {
            r = m2 - 1;
        }
    }
    if(l <= r){
      for(long long i = l; i <= r; ++i) {
          if (i == m) continue;
          long long s = dist_cycle(m, i) - query(m, i);
          if (s > max_saving) {
              max_saving = s;
              u = i;
          }
      }
    }
    if (u == -1) { // Fallback if TS fails
        u = l;
        if (u == m) u++;
        max_saving = dist_cycle(m,u) - query(m, u);
    }
    
    long long dist_u_v_cycle = max_saving + 1;
    
    long long v1 = u + dist_u_v_cycle;
    if (v1 > n) v1 -= n;
    if (v1 < 1) v1 +=n;

    long long v2 = u - dist_u_v_cycle;
    if (v2 > n) v2 -= n;
    if (v2 < 1) v2 += n;

    if (v1 != u && query(u, v1) == 1) {
        answer(u, v1);
    } else {
        answer(u, v2);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}