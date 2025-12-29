#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

typedef long long ll;

// Rectangle defined by [la, ra] x [lb, rb]
struct Rect {
    ll la, ra, lb, rb;
};

ll n;
// Global known lower bounds for a and b.
// Since response 1 (x < a) and 2 (y < b) provide absolute lower bounds on the true a and b,
// we can maintain these globally to prune all active rectangles.
ll global_la = 1;
ll global_lb = 1;

// Function to perform query and handle termination
int query(ll x, ll y) {
    cout << x << " " << y << endl;
    int ans;
    cin >> ans;
    // 0: Both x = a and y = b. Solution found.
    if (ans == 0) exit(0);
    return ans;
}

int main() {
    // Input n
    if (!(cin >> n)) return 0;

    // Queue for rectangles to search. This corresponds to a BFS exploration of the search space.
    // The disjoint nature of splitting ensures we don't duplicate search effort.
    queue<Rect> q;
    // Initial search space is the whole grid [1, n] x [1, n]
    q.push({1, n, 1, n});

    while (!q.empty()) {
        Rect cur = q.front();
        q.pop();

        // Prune search space using global lower bounds discovered so far.
        // This is crucial to efficiently kill "ghost" rectangles (regions that don't contain the solution).
        cur.la = max(cur.la, global_la);
        cur.lb = max(cur.lb, global_lb);

        // If the rectangle is invalid (empty range), discard it
        if (cur.la > cur.ra || cur.lb > cur.rb) continue;

        // Pick the midpoint of the current rectangle
        ll mx = cur.la + (cur.ra - cur.la) / 2;
        ll my = cur.lb + (cur.rb - cur.lb) / 2;

        int ans = query(mx, my);

        if (ans == 1) {
            // Response 1: x < a  =>  a >= x + 1
            // Update global lower bound for a
            global_la = max(global_la, mx + 1);
            
            // Refine current rectangle: remove left part [la, mx]
            // New la becomes mx + 1
            if (mx + 1 <= cur.ra) {
                cur.la = mx + 1;
                q.push(cur);
            }
        } else if (ans == 2) {
            // Response 2: y < b  =>  b >= y + 1
            // Update global lower bound for b
            global_lb = max(global_lb, my + 1);
            
            // Refine current rectangle: remove bottom part [lb, my]
            // New lb becomes my + 1
            if (my + 1 <= cur.rb) {
                cur.lb = my + 1;
                q.push(cur);
            }
        } else if (ans == 3) {
            // Response 3: x > a OR y > b
            // This implies (a, b) is NOT in the top-right quadrant [mx, ra] x [my, rb] relative to the current query.
            // The valid region within the current rectangle is the L-shape excluding [mx, ra] x [my, rb].
            // We split this L-shape into two DISJOINT rectangles to avoid overlapping search spaces.
            
            // Rectangle 1: Left part [la, mx-1] x [lb, rb]
            if (cur.la <= mx - 1) {
                q.push({cur.la, mx - 1, cur.lb, cur.rb});
            }
            // Rectangle 2: Bottom-Right part [mx, ra] x [lb, my-1]
            if (cur.ra >= mx && cur.lb <= my - 1) {
                q.push({mx, cur.ra, cur.lb, my - 1});
            }
        }
    }

    return 0;
}