#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>

using namespace std;

struct Solver {
    int n;
    int queries = 0;
    map<pair<int, int>, int> dist_cache;
    mt19937 rng;

    Solver(int n) : n(n) {
        rng.seed(chrono::steady_clock::now().time_since_epoch().count());
    }

    int get_dist(int u, int v) {
        if (u == v) return 0;
        if (u > v) swap(u, v);
        if (dist_cache.count({u, v})) return dist_cache[{u, v}];
        
        cout << "? " << u << " " << v << endl;
        queries++;
        int d;
        cin >> d;
        return dist_cache[{u, v}] = d;
    }

    void solve() {
        int sample_size = min(n, 450); 
        vector<int> samples;
        vector<int> p(n);
        iota(p.begin(), p.end(), 1);
        shuffle(p.begin(), p.end(), rng);
        for(int i=0; i<sample_size; ++i) samples.push_back(p[i]);

        int curr = 1;
        // Pre-cache distances from initial curr to samples
        for (int s : samples) get_dist(curr, s);

        while (true) {
            // Find heavy branch at curr
            int heavy_target = -1;
            
            // Try random pivots to identify the heavy branch
            vector<int> pivots;
            if (samples.size() > 25) {
                for(int i=0; i<25; ++i) pivots.push_back(samples[rng() % samples.size()]);
            } else {
                pivots = samples;
            }

            for (int pivot : pivots) {
                if (pivot == curr) continue;
                
                int count = 0;
                int pivot_dist = get_dist(curr, pivot);
                for (int s : samples) {
                    if (s == curr) continue;
                    int d_curr_s = get_dist(curr, s);
                    int d_pivot_s = get_dist(pivot, s);
                    // Check if s is in the component of pivot (when rooted at curr)
                    // Logic: s is in pivot's branch iff meet(curr, pivot, s) != curr
                    // meet dist from curr: (dist(curr, pivot) + dist(curr, s) - dist(pivot, s)) / 2
                    if ((pivot_dist + d_curr_s - d_pivot_s) / 2 > 0) {
                        count++;
                    }
                }
                
                if (count > samples.size() / 2) {
                    heavy_target = pivot;
                    break;
                }
            }

            if (heavy_target == -1) {
                cout << "! " << curr << endl;
                return;
            }

            int next_node = heavy_target;
            
            // Check heavy direction at next_node
            // Determine if heavy branch is back towards curr or deeper
            int up_count = 0; // towards curr
            int d_next_curr = get_dist(next_node, curr);
            for (int s : samples) {
                if (s == next_node) continue;
                int d_next_s = get_dist(next_node, s);
                int d_curr_s = get_dist(curr, s);
                // s is towards curr if meet(next_node, curr, s) != next_node
                if ((d_next_curr + d_next_s - d_curr_s) / 2 > 0) {
                    up_count++;
                }
            }
            
            if (up_count <= samples.size() / 2) {
                // Heavy branch is deeper, move to next_node
                curr = next_node;
            } else {
                // Heavy branch is back towards curr. Centroid is on path curr...next_node
                int L = curr;
                int R = next_node;
                
                // Binary search on path
                bool path_resolved = false;
                while (!path_resolved) {
                    int dist_LR = get_dist(L, R);
                    if (dist_LR <= 1) {
                        int count_R = 0;
                        for (int s : samples) {
                             if (get_dist(L, s) > get_dist(R, s)) count_R++;
                        }
                        if (count_R > (int)samples.size()/2) cout << "! " << R << endl;
                        else cout << "! " << L << endl;
                        return;
                    }

                    int best_mid = -1;
                    int best_diff = 1e9;
                    
                    // Try to find a node on the path
                    for (int k=0; k<60; ++k) {
                        int cand = (rng() % n) + 1;
                        int dL = get_dist(L, cand);
                        int dR = get_dist(R, cand);
                        if (dL + dR == dist_LR) {
                            int diff = abs(dL - dR);
                            if (diff < best_diff) {
                                best_diff = diff;
                                best_mid = cand;
                            }
                            if (diff <= 1) break; 
                        }
                    }

                    if (best_mid == -1) {
                        // Failed to find mid, assume closest to R is better or break to outer loop
                        // Just pick based on vote between L and R
                        int count_R = 0;
                        for (int s : samples) {
                             if (get_dist(L, s) > get_dist(R, s)) count_R++;
                        }
                        if (count_R > (int)samples.size()/2) cout << "! " << R << endl;
                        else cout << "! " << L << endl;
                        return;
                    }

                    int mid = best_mid;
                    int count_towards_L = 0;
                    int count_towards_R = 0;
                    int d_mid_L = get_dist(mid, L);
                    int d_mid_R = get_dist(mid, R);

                    for (int s : samples) {
                        if (s == mid) continue;
                        int d_mid_s = get_dist(mid, s);
                        int d_L_s = get_dist(L, s);
                        int d_R_s = get_dist(R, s);
                        
                        if ((d_mid_L + d_mid_s - d_L_s)/2 > 0) count_towards_L++;
                        else if ((d_mid_R + d_mid_s - d_R_s)/2 > 0) count_towards_R++;
                    }

                    if (count_towards_L > (int)samples.size() / 2) {
                        R = mid;
                    } else if (count_towards_R > (int)samples.size() / 2) {
                        L = mid;
                    } else {
                        // Balanced on path, or side branch is heavy.
                        // Move curr to mid and restart outer loop logic to handle side branch.
                        curr = mid;
                        path_resolved = true; // Break inner loop
                    }
                }
            }
        }
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    if (cin >> n) {
        Solver solver(n);
        solver.solve();
    }
    return 0;
}