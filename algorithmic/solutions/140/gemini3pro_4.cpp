#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cmath>

using namespace std;

// Global variables for problem constraints and data
long long B;
int K, W;
const long long M = 100000000LL;

// Structure to hold data for extra waves used for disambiguation
struct Query {
    long long s, t;
    map<long long, int> counts;
};

vector<Query> extra_queries;
vector<long long> U_vals; // Stores multiset of (x + y)
vector<long long> V_vals; // Stores multiset of (x - y)
bool used_v[25]; // Track usage of V values in backtracking

struct Point {
    long long x, y;
};
vector<Point> solution;
bool found_sol = false;

// Function to perform a query with a single probe
// Returns a frequency map of the distances received
map<long long, int> ask(long long s, long long t) {
    cout << "? 1 " << s << " " << t << endl;
    map<long long, int> counts;
    for (int i = 0; i < K; ++i) {
        long long d;
        cin >> d;
        counts[d]++;
    }
    return counts;
}

// Check if a candidate point (x, y) is consistent with extra queries
// Decrements counts in the queries if consistent
// Returns true if consistent, false otherwise
// Records modified queries in 'affected' for backtracking restoration
bool check_and_decrement(long long x, long long y, vector<Query*>& affected) {
    for (auto& q : extra_queries) {
        long long d = abs(x - q.s) + abs(y - q.t);
        if (q.counts.find(d) != q.counts.end() && q.counts[d] > 0) {
            q.counts[d]--;
            affected.push_back(&q);
        } else {
            return false;
        }
    }
    return true;
}

// Backtracking solver to match values from U and V
void solve_clean(int u_idx) {
    if (found_sol) return;
    if (u_idx == K) {
        found_sol = true;
        return;
    }

    long long u = U_vals[u_idx];

    // Try to match current u with any available v
    for (int v_idx = 0; v_idx < K; ++v_idx) {
        if (used_v[v_idx]) continue;

        long long v = V_vals[v_idx];
        
        // Parity check: u = x+y, v = x-y imply u and v must have same parity
        if (abs(u % 2) != abs(v % 2)) continue;

        long long x = (u + v) / 2;
        long long y = (u - v) / 2;

        // Coordinate bound check
        if (abs(x) > B || abs(y) > B) continue;

        vector<Query*> affected;
        // Verify consistency with extra waves
        if (check_and_decrement(x, y, affected)) {
            used_v[v_idx] = true;
            solution.push_back({x, y});
            
            solve_clean(u_idx + 1);
            
            if (found_sol) return;
            
            // Backtrack
            solution.pop_back();
            used_v[v_idx] = false;
        }
        
        // Restore counts in extra queries for the next iteration
        for (auto* q : affected) {
            long long d = abs(x - q->s) + abs(y - q->t);
            q->counts[d]++;
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> B >> K >> W)) return 0;

    // We use a fixed strategy of 4 waves to uniquely determine the points.
    // 4 waves are generally sufficient to disambiguate 20 points.
    
    // Wave 1: Probe at (-M, -M)
    // Distance = |x - (-M)| + |y - (-M)| = (x + M) + (y + M) = x + y + 2M
    // Allows recovering the multiset of (x + y)
    cout << "? 1 " << -M << " " << -M << endl;
    for (int i = 0; i < K; ++i) {
        long long d;
        cin >> d;
        U_vals.push_back(d - 2 * M);
    }

    // Wave 2: Probe at (-M, M)
    // Distance = |x - (-M)| + |y - M| = (x + M) + (M - y) = x - y + 2M
    // Allows recovering the multiset of (x - y)
    cout << "? 1 " << -M << " " << M << endl;
    for (int i = 0; i < K; ++i) {
        long long d;
        cin >> d;
        V_vals.push_back(d - 2 * M);
    }
    
    // Wave 3: Probe at arbitrary asymmetric coordinates
    // Provides non-linear constraints to filter incorrect (u, v) pairings
    {
        Query q;
        q.s = -30000;
        q.t = -40000;
        q.counts = ask(q.s, q.t);
        extra_queries.push_back(q);
    }
    
    // Wave 4: Another asymmetric probe for robustness
    {
        Query q;
        q.s = 50000;
        q.t = 60000;
        q.counts = ask(q.s, q.t);
        extra_queries.push_back(q);
    }

    // Solve for the coordinates
    solve_clean(0);

    // Output result
    cout << "!";
    for (auto& p : solution) {
        cout << " " << p.x << " " << p.y;
    }
    cout << endl;

    return 0;
}