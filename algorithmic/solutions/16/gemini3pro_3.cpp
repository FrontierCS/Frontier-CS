#include <iostream>
#include <algorithm>
#include <vector>
#include <cstdlib>
#include <ctime>

using namespace std;

typedef long long ll;

ll n;

// Calculate distance between u and v on a simple cycle of length n
ll dist_cycle(ll u, ll v) {
    if (u > v) swap(u, v);
    ll d = v - u;
    return min(d, n - d);
}

// Query the interactive judge
ll ask(ll u, ll v) {
    cout << "? " << u << " " << v << endl;
    ll res;
    cin >> res;
    return res;
}

// Helper to guess and check
bool guess(ll u, ll v) {
    if (u == v) return false;
    // Sort for consistency, though order doesn't matter for undirected edge
    cout << "! " << u << " " << v << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Wrong guess, terminate
    return true; // Correct guess
}

void solve() {
    cin >> n;
    
    // Step 1: Find a pair (L, R) such that the chord is used in the shortest path.
    ll L = -1, R = -1;
    srand(time(0));
    
    // Try random pairs. The probability of finding such a pair is high.
    // We try up to 200 times.
    for (int i = 0; i < 200; ++i) {
        ll x = (rand() % n) + 1;
        // Ideally opposite points cover the most chords
        ll y = (x + n / 2 - 1) % n + 1;
        
        // Add some jitter to avoid fixed patterns
        if (i % 3 == 0) {
            ll offset = (rand() % (n / 4)) + n / 4;
            y = (x + offset - 1) % n + 1;
        }
        
        if (x == y) continue;
        
        ll d_real = ask(x, y);
        ll d_cyc = dist_cycle(x, y);
        
        if (d_real < d_cyc) {
            L = x;
            R = y;
            break;
        }
    }
    
    // If we haven't found a pair, just guess something to proceed (or fail gracefully).
    // This case is statistically extremely unlikely.
    if (L == -1) {
        guess(1, 2); 
        return;
    }
    
    // Step 2: Identify the chord from the active pair (L, R).
    // We need to determine which arc (CW or CCW) the chord lies on.
    // We try both possibilities.
    
    auto solve_arc = [&](bool cw) -> pair<ll, ll> {
        ll dist_cw = (R - L + n) % n;
        ll dist_ccw = (L - R + n) % n;
        
        // If we are searching the CW arc, its length is dist_cw
        // If CCW, length is dist_ccw
        ll len = cw ? dist_cw : dist_ccw;
        
        // Helper to get vertex at distance i from L along the chosen direction
        auto get_v = [&](ll i) {
            if (cw) {
                return (L + i - 1) % n + 1;
            } else {
                return (L - i - 1 + n) % n + 1;
            }
        };
        
        // The saving at R is known.
        // If the chord is indeed on this arc and R is after v, then
        // saving = dist_cycle(L, R) - ask(L, R).
        // Wait, dist_cycle uses the global min. On this specific arc, distance is 'len'.
        // But ask(L, R) is global shortest path.
        // If this arc contains the chord, then len should be >= ask(L, R).
        // The saving relative to THIS ARC is len - ask(L, R).
        
        ll current_saving = len - ask(L, R);
        if (current_saving <= 0) return {-1, -1}; // Chord not on this arc effectively
        
        ll k = current_saving + 1;
        
        // Binary search for the first vertex v such that saving relative to arc reaches current_saving
        ll low = 1, high = len;
        ll ans_idx = -1;
        
        while (low <= high) {
            ll mid = low + (high - low) / 2;
            ll v_curr = get_v(mid);
            ll d_real = ask(L, v_curr);
            ll saving = mid - d_real;
            
            if (saving >= current_saving) {
                ans_idx = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        
        if (ans_idx != -1) {
            ll v = get_v(ans_idx);
            ll u_idx = ans_idx - k;
            // u must be on the path, so index >= 0
            if (u_idx >= 0) {
                ll u = get_v(u_idx);
                return {u, v};
            }
        }
        return {-1, -1};
    };
    
    // Try CW direction first
    pair<ll, ll> cand = solve_arc(true);
    if (cand.first != -1) {
        // Verify if this is the chord.
        // A valid chord connects non-adjacent vertices and has edge weight 1.
        // Adjacent on cycle means dist_cycle == 1.
        if (dist_cycle(cand.first, cand.second) > 1) {
             ll d = ask(cand.first, cand.second);
             if (d == 1) {
                 guess(cand.first, cand.second);
                 return;
             }
        }
    }
    
    // If CW didn't work, try CCW
    cand = solve_arc(false);
    if (cand.first != -1) {
         guess(cand.first, cand.second);
         return;
    }
    
    // Should not reach here
    guess(1, 3);
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