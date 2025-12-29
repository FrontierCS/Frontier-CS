#include <iostream>
#include <algorithm>
#include <cstdlib>
#include <vector>
#include <cmath>
#include <random>

using namespace std;

typedef long long ll;

ll n;

// Calculate distance on the simple cycle
ll dist_cycle(ll u, ll v) {
    ll diff = abs(u - v);
    return min(diff, n - diff);
}

// Interactive query
ll query(ll u, ll v) {
    cout << "? " << u << " " << v << endl;
    ll res;
    cin >> res;
    return res;
}

// Submit answer
void answer(ll u, ll v) {
    cout << "! " << u << " " << v << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
}

// Get the node at distance k from u along the specific shortest arc to v.
// d_cyc must be dist_cycle(u, v).
// The direction is inferred from the arc length.
ll get_node_on_arc(ll u, ll v, ll k, ll d_cyc) {
    ll cw_dist = (v - u + n) % n;
    if (cw_dist == d_cyc) {
        // Clockwise arc
        return (u + k - 1) % n + 1;
    } else {
        // Counter-clockwise arc
        return (u - k - 1 + n + n) % n + 1;
    }
}

void solve() {
    cin >> n;
    
    // Random number generator
    static std::mt19937_64 rng(1337);
    
    ll x = -1, y = -1;
    ll d_meas = -1, d_cyc = -1;
    
    // Step 1: Find a pair (x, y) such that the chord is part of the shortest path.
    // We do this by checking random pairs with distance roughly n/2.
    int attempts = 0;
    while (true) {
        attempts++;
        ll u_rnd = (rng() % n) + 1;
        
        ll offset;
        if (n <= 20) {
            offset = n / 2;
        } else {
            // Random offset in range [n/2 - 100, n/2] to ensure we check various arc lengths near diameter
            ll lower = n / 2 - 100;
            if (lower < 2) lower = 2;
            ll range = (n / 2) - lower + 1;
            offset = lower + (rng() % range);
        }
        
        if (offset < 2 && n > 3) offset = 2;
        if (offset >= n) offset = n - 1;

        ll v_rnd = (u_rnd + offset - 1) % n + 1;
        if (u_rnd == v_rnd) v_rnd = (u_rnd % n) + 1;
        
        ll d = query(u_rnd, v_rnd);
        ll dc = dist_cycle(u_rnd, v_rnd);
        
        if (d < dc) {
            x = u_rnd;
            y = v_rnd;
            d_meas = d;
            d_cyc = dc;
            break;
        }
        
        // Failsafe for query limit, though unlikely to be reached
        if (attempts > 300) {
            // Should not happen given problem constraints and probability
            // If it does, we just continue, hoping to find it.
        }
    }
    
    // Step 2: Calculate K, the cycle distance between chord endpoints u and v.
    // d(x, y) = d_cycle(x, u) + 1 + d_cycle(v, y)
    // d_cycle(x, y) = d_cycle(x, u) + K + d_cycle(v, y)
    // Difference is K - 1.
    ll K = d_cyc - d_meas + 1;
    
    // Step 3: Binary search for the split point S_x on the arc x -> y.
    // S_x is the furthest point from x such that the shortest path is entirely on the cycle.
    // For points beyond S_x, the chord path becomes shorter.
    // Range for binary search is [0, d_cyc - 1] (distance from x).
    
    ll L = 0, R = d_cyc - 1;
    ll Sx_pos = 0;
    
    while (L <= R) {
        ll mid = L + (R - L) / 2;
        if (mid == 0) {
            Sx_pos = max(Sx_pos, mid);
            L = mid + 1;
            continue;
        }
        
        ll node_mid = get_node_on_arc(x, y, mid, d_cyc);
        ll d_real = query(x, node_mid);
        
        if (d_real == mid) {
            // Cycle path is still shortest
            Sx_pos = mid;
            L = mid + 1;
        } else {
            // Chord path is shorter
            R = mid - 1;
        }
    }
    
    // Step 4: Determine u and v positions relative to x on the arc.
    // Let P_u and P_v be distances of u and v from x.
    // We have P_v - P_u = K.
    // Also from derivation, P_u + P_v <= 2 * Sx_pos <= P_u + P_v + 1.
    // Let Sum = P_u + P_v.
    // 2 * Sx_pos is either Sum or Sum + 1.
    // Since Sum and K must have the same parity (Sum - K = 2 * P_u),
    // and 2 * Sx_pos is even, we can determine Sum uniquely.
    
    ll Sum;
    if (K % 2 != 0) {
        // K is odd => Sum is odd => Sum = 2 * Sx_pos - 1
        Sum = 2 * Sx_pos - 1;
    } else {
        // K is even => Sum is even => Sum = 2 * Sx_pos
        Sum = 2 * Sx_pos;
    }
    
    ll u_pos = (Sum - K) / 2;
    ll v_pos = (Sum + K) / 2;
    
    ll u = get_node_on_arc(x, y, u_pos, d_cyc);
    ll v = get_node_on_arc(x, y, v_pos, d_cyc);
    
    answer(u, v);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}