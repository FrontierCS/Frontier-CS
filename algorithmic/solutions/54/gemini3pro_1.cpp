#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <map>

using namespace std;

// Function to perform query
int get_dist(int u, int v) {
    if (u == v) return 0;
    cout << "? " << u << " " << v << endl;
    int d;
    cin >> d;
    return d;
}

// Function to report answer
void report(int x) {
    cout << "! " << x << endl;
    exit(0);
}

int n;
vector<int> current_S;
mt19937 rng(1337);

void solve() {
    if (!(cin >> n)) return;
    
    current_S.resize(n);
    for(int i=0; i<n; ++i) current_S[i] = i+1;

    // Fixed parameter for sampling
    // 180 samples * 2 queries = 360 queries per step. 
    // This is small constant overhead.
    int sample_count = 180; 

    while(current_S.size() > 1) {
        // 1. Pick random pivot r from S
        int r = current_S[rng() % current_S.size()];

        // 2. Find farthest u from r in S
        int u = r;
        int max_d = -1;
        for(int x : current_S) {
            if(x == r) continue;
            int d = get_dist(r, x);
            if(d > max_d) {
                max_d = d;
                u = x;
            }
        }
        
        // 3. Find farthest v from u in S
        vector<int> dist_u(n + 1, 0); 
        int v = u;
        max_d = -1;
        for(int x : current_S) {
            if(x == u) {
                dist_u[x] = 0;
                continue;
            }
            int d = get_dist(u, x);
            dist_u[x] = d;
            if(d > max_d) {
                max_d = d;
                v = x;
            }
        }

        // 4. Get distances from v for all S (for projection)
        vector<int> dist_v(n + 1, 0);
        for(int x : current_S) {
            if(x == v) {
                dist_v[x] = 0;
                continue;
            }
            int d = get_dist(v, x);
            dist_v[x] = d;
        }

        int dist_uv = dist_u[v];
        
        // 5. Compute projections and find weighted median w* on path
        map<int, int> counts;
        
        for(int x : current_S) {
            // 2 * dist(u, pi(x)) = dist(u, x) - dist(v, x) + dist(u, v)
            int d_pi_u_2 = dist_u[x] - dist_v[x] + dist_uv; 
            // Store doubled distance to avoid division, though it's always even
            counts[d_pi_u_2]++;
        }

        int total_S = current_S.size();
        int current_sum = 0;
        int w_star_dist_2 = -1;
        
        for(auto const& [d_2, count] : counts) {
            // Check if this position is a valid median split
            // We want the point where neither side has > |S|/2 weight if possible
            // or the point that tips the balance.
            if (current_sum + count > total_S / 2) {
                w_star_dist_2 = d_2;
                break;
            }
            current_sum += count;
        }
        
        // 6. Check if global centroid is Left or Right of w* using sampling
        // We use the same projection logic on random nodes from the whole tree
        int votes_left = 0;
        int votes_right = 0;
        int valid_samples = 0;

        for(int k=0; k<sample_count; ++k) {
            int t = (rng() % n) + 1; // Random node 1..n
            int du = get_dist(u, t);
            int dv = get_dist(v, t);
            // Projection * 2
            int dpi_2 = du - dv + dist_uv;
            
            if(dpi_2 < w_star_dist_2) {
                votes_left++;
            } else if(dpi_2 > w_star_dist_2) {
                votes_right++;
            }
            valid_samples++;
        }

        bool go_left = (votes_left * 2 > valid_samples);
        bool go_right = (votes_right * 2 > valid_samples);

        vector<int> next_S;
        next_S.reserve(total_S / 2);

        if(go_left) {
            // Centroid is to the left (towards u)
            for(int x : current_S) {
                int d_pi_u_2 = dist_u[x] - dist_v[x] + dist_uv;
                if(d_pi_u_2 < w_star_dist_2) next_S.push_back(x);
            }
        } else if(go_right) {
            // Centroid is to the right (towards v)
            for(int x : current_S) {
                int d_pi_u_2 = dist_u[x] - dist_v[x] + dist_uv;
                if(d_pi_u_2 > w_star_dist_2) next_S.push_back(x);
            }
        } else {
            // Centroid is at w* or in a branch attached at w* (off-path)
            for(int x : current_S) {
                int d_pi_u_2 = dist_u[x] - dist_v[x] + dist_uv;
                if(d_pi_u_2 == w_star_dist_2) next_S.push_back(x);
            }
        }
        
        if(next_S.empty()) {
            // Should not happen, but safe fallback
            // Return w* node? We need to find node ID with proj w_star_dist_2
             for(int x : current_S) {
                int d_pi_u_2 = dist_u[x] - dist_v[x] + dist_uv;
                if(d_pi_u_2 == w_star_dist_2) {
                    report(x);
                }
            }
            report(current_S[0]);
        }
        
        current_S = next_S;
    }
    
    report(current_S[0]);
}

int main() {
    solve();
    return 0;
}