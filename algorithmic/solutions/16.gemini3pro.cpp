#include <iostream>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

typedef long long ll;

ll n;

ll dist_cycle(ll u, ll v) {
    ll d = abs(u - v);
    return min(d, n - d);
}

ll query(ll u, ll v) {
    cout << "? " << u << " " << v << endl;
    ll d;
    cin >> d;
    return d;
}

void solve() {
    cin >> n;
    
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    ll x = -1, y = -1, L = -1;
    ll K_cycle = -1; 
    
    // Step 1: Find a pair (x, y) such that the chord shortens the distance
    while (true) {
        ll u = (rng() % n) + 1;
        ll v = (u + n / 2 - 1) % n + 1;
        // Avoid u == v
        if (u == v) {
             v = (u + n / 2) % n + 1;
        }
        if (u == v) { // Should only happen if n=1, but problem says n>=4
            v = (u % n) + 1; 
        }
        
        ll d = query(u, v);
        ll dc = dist_cycle(u, v);
        
        if (d < dc) {
            x = u;
            y = v;
            ll saving = dc - d;
            L = saving + 1;
            K_cycle = dc; 
            break;
        }
    }
    
    // Step 2: Determine direction (CW or CCW)
    // Check CW neighbor of x
    ll x_cw = (x % n) + 1;
    ll d_cw = query(x_cw, y);
    
    // If chord is on CW path x->y, distance from x_cw should be d(x,y) - 1
    // unless x is the start of chord u, in which case logic is tricky.
    // But for large n, x!=u w.h.p. For small n, handle separately.
    
    ll D_curr = dist_cycle(x, y) - (L - 1);
    
    bool is_cw = false;
    bool ambiguous = false;

    if (d_cw == D_curr - 1) {
        is_cw = true;
    } else {
        // Check CCW neighbor
        ll x_ccw = (x - 2 + n) % n + 1;
        ll d_ccw = query(x_ccw, y);
        if (d_ccw == D_curr - 1) {
            is_cw = false;
        } else {
            ambiguous = true;
        }
    }
    
    if (ambiguous) {
        // x is likely u or v (an endpoint of chord)
        // Check two candidates for the other endpoint
        // Candidate 1: CW by distance L
        ll v1 = (x + L - 1) % n + 1;
        ll d_check = query(x, v1);
        if (d_check == 1) {
            cout << "! " << x << " " << v1 << endl;
        } else {
            // Candidate 2: CCW by distance L
            ll v2 = (x - L + n - 1) % n + 1;
            cout << "! " << x << " " << v2 << endl;
        }
        ll res; cin >> res;
        if (res == -1) exit(0);
        return;
    }
    
    // Standardize to CW direction from x to y
    if (!is_cw) {
        swap(x, y);
        // K_cycle is cycle distance, which is symmetric, so still valid.
    }
    
    // Step 3: Binary Search for u in the range [0, K_cycle - L]
    // The path x -> y is clockwise.
    // We want the last vertex 'm' on this path such that D(m, y) has full saving.
    
    ll low = 0, high = K_cycle - L;
    ll ans = 0;
    
    while (low <= high) {
        ll mid = low + (high - low) / 2;
        // Vertex at distance mid clockwise from x
        ll v_mid = (x - 1 + mid) % n + 1;
        
        if (mid == 0) { 
             ans = max(ans, mid);
             low = mid + 1;
             continue;
        }
        
        ll d_real = query(v_mid, y);
        ll d_cyc_rem = K_cycle - mid;
        
        // Check if full saving is preserved
        if (d_real == d_cyc_rem - (L - 1)) {
            ans = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    
    ll u_final = (x - 1 + ans) % n + 1;
    ll v_final = (u_final - 1 + L) % n + 1;
    
    cout << "! " << u_final << " " << v_final << endl;
    ll res; cin >> res;
    if (res == -1) exit(0);
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}