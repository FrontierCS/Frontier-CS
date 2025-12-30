#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

long long n;

long long query(long long x, long long y) {
    if (x == y) return 0;
    cout << "? " << x << " " << y << endl;
    long long dist;
    cin >> dist;
    if (dist == -1) exit(0);
    return dist;
}

long long dist_cycle(long long u, long long v) {
    if (u > v) swap(u, v);
    return min(v - u, n - (v - u));
}

void solve() {
    cin >> n;

    long long p1 = 1;
    long long p2 = 1 + n / 2;

    long long d = query(p1, p2);

    if (d < dist_cycle(p1, p2)) {
        // Case 1: p1 and p2 are separated.
        // u is on arc (p1, p2), v is on arc (p2, p1).

        // Find u: largest x in [p1, p2] with dist(x, p2) == dist_cycle(x, p2)
        long long u_l = p1, u_r = p2;
        long long u = p1;
        while (u_l <= u_r) {
            long long mid = u_l + (u_r - u_l) / 2;
            if (mid == p2) {
                u_r = mid - 1;
                continue;
            }
            if (query(mid, p2) == dist_cycle(mid, p2)) {
                u = mid;
                u_l = mid + 1;
            } else {
                u_r = mid - 1;
            }
        }

        // Find v: largest x in [p2, n] with dist(x, p1) == dist_cycle(x, p1)
        long long v_l = p2, v_r = n;
        long long v = p2;
        while (v_l <= v_r) {
            long long mid = v_l + (v_r - v_l) / 2;
            if (mid == p2) {
                v_l = mid + 1;
                continue;
            }
            if (query(mid, p1) == dist_cycle(mid, p1)) {
                v = mid;
                v_l = mid + 1;
            } else {
                v_r = mid - 1;
            }
        }
        cout << "! " << u << " " << v << endl;

    } else {
        // Case 2: p1 and p2 are on the same side.
        // Chord is in arc (p1, p2) or (p2, p1).

        // Test assumption: chord is in (p1, p2)
        // Find u: largest x in [p1, p2] with dist(x, p1) == dist_cycle(x, p1)
        long long u1_l = p1, u1_r = p2;
        long long u1 = p1;
        while (u1_l <= u1_r) {
            long long mid = u1_l + (u1_r - u1_l) / 2;
            if (mid == p1) {
                u1_l = mid + 1;
                continue;
            }
            if (query(p1, mid) == dist_cycle(p1, mid)) {
                u1 = mid;
                u1_l = mid + 1;
            } else {
                u1_r = mid - 1;
            }
        }
        
        // Find v: smallest x in [p1, p2] with dist(x, p2) == dist_cycle(x, p2)
        long long v1_l = p1, v1_r = p2;
        long long v1 = p2;
        while (v1_l <= v1_r) {
            long long mid = v1_l + (v1_r - v1_l) / 2;
            if(mid == p1) {
                v1_l = mid + 1;
                continue;
            }
            if (query(p2, mid) == dist_cycle(p2, mid)) {
                v1 = mid;
                v1_r = mid - 1;
            } else {
                v1_l = mid + 1;
            }
        }

        if (u1 < v1) {
            cout << "! " << u1 << " " << v1 << endl;
        } else {
            // Chord is in (p2, p1)
            // Find u: largest x in [p2, n] with dist(x, p2) == dist_cycle(x, p2)
            long long u2_l = p2, u2_r = n;
            long long u2 = p2;
            while (u2_l <= u2_r) {
                long long mid = u2_l + (u2_r - u2_l) / 2;
                if (mid == p2) {
                    u2_l = mid + 1;
                    continue;
                }
                if (query(p2, mid) == dist_cycle(p2, mid)) {
                    u2 = mid;
                    u2_l = mid + 1;
                } else {
                    u2_r = mid - 1;
                }
            }
            
            // Find v: smallest x in [p2, n] with dist(x, p1) == dist_cycle(x, p1)
            long long v2_l = p2, v2_r = n;
            long long v2 = n + 1;
            while(v2_l <= v2_r){
                long long mid = v2_l + (v2_r - v2_l) / 2;
                if(query(p1, mid) == dist_cycle(p1, mid)){
                    v2 = mid;
                    v2_r = mid - 1;
                } else {
                    v2_l = mid + 1;
                }
            }
            cout << "! " << u2 << " " << v2 << endl;
        }
    }
    
    int result;
    cin >> result;
    if (result == -1) {
        exit(0);
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