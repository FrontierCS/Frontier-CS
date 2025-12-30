#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cmath>
#include <random>

using namespace std;

// Global variables
int B, K, W;
long long INF_COORD = 100000000;

struct Query {
    long long sx, sy;
    map<long long, int> counts;
};

vector<Query> extra_queries;
vector<long long> S_vals; // sums x+y
vector<long long> D_vals; // diffs x-y
struct Point {
    long long x, y;
};
vector<Point> final_deposits;
bool found_solution = false;

// Function to send a query and read the response
void ask_query(long long s, long long t, vector<long long>& result) {
    cout << "? 1 " << s << " " << t << endl;
    result.resize(K);
    for (int i = 0; i < K; ++i) {
        cin >> result[i];
    }
}

// Backtracking solver
// idx: current index in S_vals we are matching
// mask_D: bitmask of used indices in D_vals
// prev_j: the index j of D_vals used in the previous step (for duplicate S handling)
void solve(int idx, int mask_D, int prev_j) {
    if (found_solution) return;
    if (idx == K) {
        found_solution = true;
        return;
    }

    long long s_val = S_vals[idx];
    
    // Optimization for duplicates in S: enforce strict ordering of D indices
    // If S_vals[idx] == S_vals[idx-1], we must pick j > prev_j
    int start_j = 0;
    if (idx > 0 && S_vals[idx] == S_vals[idx-1]) {
        start_j = prev_j + 1;
    }

    for (int j = start_j; j < K; ++j) {
        // Optimization for duplicates in D:
        // If D_vals[j] == D_vals[j-1] and j-1 was NOT used, we should have used j-1 instead.
        if (j > 0 && D_vals[j] == D_vals[j-1] && !((mask_D >> (j-1)) & 1)) {
            continue;
        }

        if (!((mask_D >> j) & 1)) {
            long long d_val = D_vals[j];
            
            // Check parity for integer coordinates
            if ((s_val + d_val) % 2 != 0) continue;
            
            long long x = (s_val + d_val) / 2;
            long long y = (s_val - d_val) / 2;

            // Check boundary constraints
            if (abs(x) > B || abs(y) > B) continue;

            // Check consistency with random queries
            bool ok = true;
            for (auto& q : extra_queries) {
                long long dist = abs(x - q.sx) + abs(y - q.sy);
                if (q.counts.find(dist) == q.counts.end() || q.counts[dist] == 0) {
                    ok = false;
                    break;
                }
            }

            if (ok) {
                // Tentatively accept point and update counts
                for (auto& q : extra_queries) {
                    long long dist = abs(x - q.sx) + abs(y - q.sy);
                    q.counts[dist]--;
                }
                final_deposits.push_back({x, y});

                solve(idx + 1, mask_D | (1 << j), j);
                
                if (found_solution) return;

                // Backtrack
                final_deposits.pop_back();
                for (auto& q : extra_queries) {
                    long long dist = abs(x - q.sx) + abs(y - q.sy);
                    q.counts[dist]++;
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> B >> K >> W)) return 0;
    
    // Wave 1: Probe at (-10^8, -10^8) gives distances x + y + 2*10^8
    vector<long long> res1;
    ask_query(-INF_COORD, -INF_COORD, res1);
    for (long long val : res1) S_vals.push_back(val - 2 * INF_COORD);

    // Wave 2: Probe at (-10^8, 10^8) gives distances x - y + 2*10^8
    vector<long long> res2;
    ask_query(-INF_COORD, INF_COORD, res2);
    for (long long val : res2) D_vals.push_back(val - 2 * INF_COORD);
    
    // Responses are sorted, so S_vals and D_vals are sorted.
    // D_vals sorted property is required for duplicate optimization.
    sort(D_vals.begin(), D_vals.end());

    // Use random queries to disambiguate the pairing of sums and diffs.
    int num_random = 12;
    // Ensure we don't exceed max waves (W usually >= 2)
    num_random = min(num_random, W - 2);

    mt19937 rng(1337);
    uniform_int_distribution<long long> dist_coord(-B, B);

    for (int i = 0; i < num_random; ++i) {
        long long rx = dist_coord(rng);
        long long ry = dist_coord(rng);
        vector<long long> res;
        ask_query(rx, ry, res);
        
        Query q;
        q.sx = rx;
        q.sy = ry;
        for (long long d : res) {
            q.counts[d]++;
        }
        extra_queries.push_back(q);
    }

    // Solve for pairings
    solve(0, 0, -1);

    // Output results
    cout << "!";
    for (const auto& p : final_deposits) {
        cout << " " << p.x << " " << p.y;
    }
    cout << endl;

    return 0;
}