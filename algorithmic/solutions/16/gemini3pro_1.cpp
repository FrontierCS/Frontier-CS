#include <iostream>
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>
#include <cstdlib>

using namespace std;

typedef long long ll;

ll n;

ll query(ll u, ll v) {
    if (u == v) return 0;
    cout << "? " << u << " " << v << endl;
    ll res;
    cin >> res;
    return res;
}

// Distance from u to v in Clockwise direction
ll dist_cw(ll u, ll v) {
    if (u <= v) return v - u;
    return n - (u - v);
}

// Distance from u to v in Counter-Clockwise direction
ll dist_ccw(ll u, ll v) {
    if (u >= v) return u - v;
    return n - (v - u);
}

// Shortest distance on the original cycle
ll dist_cycle(ll u, ll v) {
    ll d = abs(u - v);
    return min(d, n - d);
}

// Get k-th vertex on CW path starting from u (0-th is u)
ll get_cw(ll u, ll k) {
    return (u + k - 1) % n + 1;
}

// Get k-th vertex on CCW path starting from u (0-th is u)
ll get_ccw(ll u, ll k) {
    return (u - k - 1 + n) % n + 1;
}

void solve() {
    cin >> n;
    ll x = -1, y = -1;
    ll L = -1;
    
    // Step 1: Find an active pair (x, y) whose shortest path uses the chord
    // We try random pairs (u, v) where v is roughly opposite to u.
    // The chord is used if query(u, v) < dist_cycle(u, v).
    // The probability of finding such a pair is roughly > 0.5 for any chord length.
    // 50 iterations give very high confidence.
    
    for (int i = 0; i < 60; ++i) {
        ll u = rand() % n + 1;
        ll v = (u + n / 2 - 1) % n + 1;
        
        ll d = query(u, v);
        ll dc = dist_cycle(u, v);
        
        if (d < dc) {
            x = u;
            y = v;
            L = dc - d + 1; // Calculating chord length on the cycle
            break;
        }
    }
    
    // If we didn't find any (should practically never happen), we can't solve it.
    // Assuming valid x, y, L found.
    
    // Step 2: Binary Search on the CW arc from x to y to find the chord endpoint v.
    // We look for the first vertex k such that the saving is full (L-1).
    ll len_cw = dist_cw(x, y);
    ll low = 0, high = len_cw;
    ll res_cw = -1;
    
    while (low <= high) {
        ll mid = low + (high - low) / 2;
        ll v_curr = get_cw(x, mid);
        ll d_actual = query(x, v_curr);
        ll d_expected = dist_cycle(x, v_curr);
        
        if (d_expected - d_actual == L - 1) {
            res_cw = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    
    ll v_cw_vertex = get_cw(x, res_cw);
    
    // If the found vertex is strictly before y, it must be the true endpoint v.
    if (v_cw_vertex != y) {
        // v is v_cw_vertex. u is L steps back on CW path (i.e., CCW direction).
        ll u_ans = get_ccw(v_cw_vertex, L);
        cout << "! " << u_ans << " " << v_cw_vertex << endl;
        int r; cin >> r;
        if (r == -1) exit(0);
        return;
    }
    
    // Step 3: If CW search returned y, it's inconclusive (could be on CCW side or v=y).
    // Search on CCW arc.
    ll len_ccw = dist_ccw(x, y);
    low = 0; high = len_ccw;
    ll res_ccw = -1;
    
    while (low <= high) {
        ll mid = low + (high - low) / 2;
        ll v_curr = get_ccw(x, mid);
        ll d_actual = query(x, v_curr);
        ll d_expected = dist_cycle(x, v_curr);
        
        if (d_expected - d_actual == L - 1) {
            res_ccw = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    
    ll v_ccw_vertex = get_ccw(x, res_ccw);
    
    // If CCW search found a vertex strictly before y, it's the true endpoint.
    if (v_ccw_vertex != y) {
        // v is v_ccw_vertex. u is L steps back on CCW path (i.e., CW direction).
        ll u_ans = get_cw(v_ccw_vertex, L);
        cout << "! " << u_ans << " " << v_ccw_vertex << endl;
        int r; cin >> r;
        if (r == -1) exit(0);
        return;
    }
    
    // Step 4: Both searches returned y. This means v = y.
    // We have two candidates for u: one on CW side, one on CCW side.
    // Check which one has distance 1 to y.
    
    ll u1 = get_ccw(y, L); // Candidate u on CW side (L steps CCW from y)
    ll u2 = get_cw(y, L);  // Candidate u on CCW side (L steps CW from y)
    
    ll d_check = query(u1, y);
    if (d_check == 1) {
        cout << "! " << u1 << " " << y << endl;
    } else {
        cout << "! " << u2 << " " << y << endl;
    }
    int r; cin >> r;
    if (r == -1) exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    // Use a fixed or random seed
    srand(12345); 
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}