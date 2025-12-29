#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cmath>
#include <random>

using namespace std;

// Global variables to store problem parameters and state
long long B;
int K, W;
const long long M = 100000000LL; // 10^8

// Structure to hold information about an additional query
struct Query {
    long long s, t; // Probe coordinates
    map<long long, int> dist_counts; // Multiset of returned distances
};

// U_vals stores potential values of (x + y)
// V_vals stores potential values of (x - y)
vector<long long> U_vals;
vector<long long> V_vals;
vector<Query> constraints; // History of random queries

struct Point {
    long long x, y;
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

vector<vector<Point>> solutions;
bool used_v[25]; // Tracks which values from V_vals are used
Point current_set[25]; // Current permutation being built

// Backtracking function to find valid sets of points
// Returns true if we should stop searching (i.e., found at least 2 valid sets -> ambiguous)
bool solve(int idx) {
    // If we already found ambiguity, no need to search further in this phase
    if (solutions.size() >= 2) return true;

    // If we have constructed a full set of K points
    if (idx == K) {
        vector<Point> sol;
        for (int i = 0; i < K; ++i) sol.push_back(current_set[i]);
        sort(sol.begin(), sol.end());
        solutions.push_back(sol);
        return solutions.size() >= 2;
    }

    // Try to pair the current u = U_vals[idx] with every available v
    long long u = U_vals[idx];
    
    for (int j = 0; j < K; ++j) {
        if (used_v[j]) continue;
        
        long long v = V_vals[j];
        
        // x+y = u, x-y = v => 2x = u+v, 2y = u-v
        // u and v must have the same parity
        if ((u + v) % 2 != 0) continue;
        
        long long x = (u + v) / 2;
        long long y = (u - v) / 2;
        
        // Coordinates must be within bounds
        if (x < -B || x > B || y < -B || y > B) continue;
        
        // Check consistency with all additional constraints
        bool ok = true;
        for (auto& q : constraints) {
            long long d = abs(x - q.s) + abs(y - q.t);
            auto it = q.dist_counts.find(d);
            if (it == q.dist_counts.end() || it->second <= 0) {
                ok = false;
                break;
            }
        }
        
        if (ok) {
            used_v[j] = true;
            current_set[idx] = {x, y};
            
            // Decrement counts in constraints to "use" this distance
            for (auto& q : constraints) {
                long long d = abs(x - q.s) + abs(y - q.t);
                q.dist_counts[d]--;
            }
            
            bool stop = solve(idx + 1);
            
            // Backtrack: restore counts
            for (auto& q : constraints) {
                long long d = abs(x - q.s) + abs(y - q.t);
                q.dist_counts[d]++;
            }
            used_v[j] = false;
            
            if (stop) return true;
        }
    }
    return false;
}

// Helper to send a query and read response
vector<long long> make_query(int d, vector<pair<long long, long long>> probes) {
    cout << "? " << d;
    for (auto& p : probes) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;
    vector<long long> resp(d * K);
    for (int i = 0; i < d * K; ++i) cin >> resp[i];
    return resp;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> B >> K >> W)) return 0;

    // Strategy:
    // 1. Determine the multiset of (x + y) for all points.
    //    We place a probe at (-M, -M). Since x, y >= -B >= -M,
    //    dist = |x - (-M)| + |y - (-M)| = x + M + y + M = (x + y) + 2M.
    vector<long long> resp1 = make_query(1, {{-M, -M}});
    for (long long val : resp1) U_vals.push_back(val - 2 * M);
    sort(U_vals.begin(), U_vals.end());

    // 2. Determine the multiset of (x - y) for all points.
    //    We place a probe at (-M, M). Since x >= -M and y <= B <= M,
    //    dist = |x - (-M)| + |y - M| = x + M + M - y = (x - y) + 2M.
    vector<long long> resp2 = make_query(1, {{-M, M}});
    for (long long val : resp2) V_vals.push_back(val - 2 * M);
    sort(V_vals.begin(), V_vals.end());

    // 3. Disambiguate pairings of U and V using random probes.
    mt19937_64 rng(1337);
    uniform_int_distribution<long long> distB(-B, B);

    while (true) {
        solutions.clear();
        for (int i = 0; i < K; ++i) used_v[i] = false;
        
        solve(0);
        
        // If exactly one solution is consistent with all data, we are done.
        if (solutions.size() == 1) {
            cout << "!";
            for (const auto& p : solutions[0]) {
                cout << " " << p.x << " " << p.y;
            }
            cout << endl;
            break;
        }
        
        // If multiple solutions exist (or 0, though 0 shouldn't happen with correct logic),
        // add a random probe to filter candidates.
        long long qx = distB(rng);
        long long qy = distB(rng);
        
        vector<long long> resp = make_query(1, {{qx, qy}});
        Query q;
        q.s = qx;
        q.t = qy;
        for (long long d : resp) q.dist_counts[d]++;
        constraints.push_back(q);
    }

    return 0;
}