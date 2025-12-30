#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>

using namespace std;

// Data structures
struct Point {
    int id;
    int x, y;
    int ux, uy; // Coordinates in compressed space (indices in uniq vectors)
};

int N;
int K;
int a[11];
vector<Point> points;
vector<int> uniq_x, uniq_y;
map<int, int> target_counts;
vector<int> counts_buf; // Buffer for piece counts

// Calculate score for a given set of cuts (indices in uniq arrays)
int calculate_score(const vector<int>& cx, const vector<int>& cy) {
    int cols = (int)cx.size() + 1;
    int rows = (int)cy.size() + 1;
    int total_cells = cols * rows;
    
    // Clear buffer (only the used part)
    for (int i = 0; i < total_cells; ++i) counts_buf[i] = 0;
    
    // Assign points to regions and count
    for (const auto& p : points) {
        // Find region x
        // The region index corresponds to the number of cuts strictly less than p.ux
        // Since cx is sorted, lower_bound gives the first cut >= p.ux.
        // The distance from begin is exactly the number of elements < p.ux.
        int c_idx = (int)(lower_bound(cx.begin(), cx.end(), p.ux) - cx.begin());
        
        // Find region y
        int r_idx = (int)(lower_bound(cy.begin(), cy.end(), p.uy) - cy.begin());
        
        counts_buf[r_idx * cols + c_idx]++;
    }
    
    // Tally sizes
    int size_counts[11] = {0};
    for (int i = 0; i < total_cells; ++i) {
        int c = counts_buf[i];
        if (c >= 1 && c <= 10) {
            size_counts[c]++;
        }
    }
    
    // Compute objective: sum of min(a_d, b_d)
    int score = 0;
    for (int d = 1; d <= 10; ++d) {
        score += min(target_counts[d], size_counts[d]);
    }
    return score;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    // Input
    if (!(cin >> N >> K)) return 0;
    int sum_attendees = 0;
    for (int i = 1; i <= 10; ++i) {
        cin >> a[i];
        target_counts[i] = a[i];
        sum_attendees += a[i];
    }
    
    points.resize(N);
    vector<int> raw_x, raw_y;
    raw_x.reserve(N);
    raw_y.reserve(N);
    
    for (int i = 0; i < N; ++i) {
        cin >> points[i].x >> points[i].y;
        points[i].id = i;
        raw_x.push_back(points[i].x);
        raw_y.push_back(points[i].y);
    }
    
    // Coordinate Compression
    sort(raw_x.begin(), raw_x.end());
    raw_x.erase(unique(raw_x.begin(), raw_x.end()), raw_x.end());
    uniq_x = raw_x;
    
    sort(raw_y.begin(), raw_y.end());
    raw_y.erase(unique(raw_y.begin(), raw_y.end()), raw_y.end());
    uniq_y = raw_y;
    
    for (int i = 0; i < N; ++i) {
        points[i].ux = (int)(lower_bound(uniq_x.begin(), uniq_x.end(), points[i].x) - uniq_x.begin());
        points[i].uy = (int)(lower_bound(uniq_y.begin(), uniq_y.end(), points[i].y) - uniq_y.begin());
    }
    
    // Resize buffer to max possible size (101 * 101)
    counts_buf.resize(102 * 102);
    
    // Initialization of solution
    vector<int> cuts_x, cuts_y;
    
    // Determine initial grid size based on total attendees
    // We aim for approx equal number of regions as attendees
    int grid_size = (int)sqrt(sum_attendees);
    // Limit by K (total cuts)
    if (grid_size * 2 > K) grid_size = K / 2;
    // Also limit by available gaps (uniq size - 1)
    int max_gaps_x = max(0, (int)uniq_x.size() - 1);
    int max_gaps_y = max(0, (int)uniq_y.size() - 1);
    
    int nx = min(grid_size, max_gaps_x);
    int ny = min(grid_size, max_gaps_y);
    
    // Helper to generate uniform cuts
    auto init_cuts = [](int k, int n_gaps) {
        vector<int> res;
        if (k <= 0 || n_gaps <= 0) return res;
        for (int i = 1; i <= k; ++i) {
            // Select index roughly at fraction i/(k+1)
            int val = (int)((long long)n_gaps * i / (k + 1)) - 1;
            if (val < 0) val = 0;
            if (val >= n_gaps) val = n_gaps - 1;
            res.push_back(val);
        }
        sort(res.begin(), res.end());
        res.erase(unique(res.begin(), res.end()), res.end());
        return res;
    };
    
    cuts_x = init_cuts(nx, max_gaps_x);
    cuts_y = init_cuts(ny, max_gaps_y);
    
    int current_score = calculate_score(cuts_x, cuts_y);
    int best_score = current_score;
    vector<int> best_cuts_x = cuts_x;
    vector<int> best_cuts_y = cuts_y;
    
    // Hill Climbing Loop
    mt19937 rng(12345);
    auto start_clock = chrono::steady_clock::now();
    double time_limit = 2.85; 
    
    int iter = 0;
    while (true) {
        iter++;
        // Check time every 128 iterations
        if ((iter & 127) == 0) {
            double el = chrono::duration<double>(chrono::steady_clock::now() - start_clock).count();
            if (el > time_limit) break;
        }
        
        // Randomly choose move type and axis
        // 0: Add cut, 1: Remove cut, 2: Move cut
        int type = rng() % 3;
        bool is_x = (rng() % 2 == 0);
        
        vector<int>& curr = is_x ? cuts_x : cuts_y;
        int max_g = is_x ? max_gaps_x : max_gaps_y;
        
        if (max_g == 0) continue; 
        
        vector<int> backup = curr;
        bool changed = false;
        
        if (type == 0) { // Add
            if (cuts_x.size() + cuts_y.size() < K) {
                int val = rng() % max_g;
                auto it = lower_bound(curr.begin(), curr.end(), val);
                // Insert only if not exists
                if (it == curr.end() || *it != val) {
                    curr.insert(it, val);
                    changed = true;
                }
            }
        } else if (type == 1) { // Remove
            if (!curr.empty()) {
                int idx = rng() % curr.size();
                curr.erase(curr.begin() + idx);
                changed = true;
            }
        } else { // Move
            if (!curr.empty()) {
                int idx = rng() % curr.size();
                int val = curr[idx];
                curr.erase(curr.begin() + idx);
                
                // Shift by small amount
                int shift = (int)(rng() % 9) - 4; // -4 to 4
                if (shift == 0) shift = (rng() % 2 == 0 ? 1 : -1);
                
                int nval = val + shift;
                // Clamp
                if (nval < 0) nval = 0;
                if (nval >= max_g) nval = max_g - 1;
                
                // Re-insert sorted
                auto it = lower_bound(curr.begin(), curr.end(), nval);
                if (it == curr.end() || *it != nval) {
                    curr.insert(it, nval);
                    changed = true;
                } else {
                    // Collision: effectively we just removed a line.
                    // This is valid move (transition to state with one less line).
                    changed = true;
                }
            }
        }
        
        if (changed) {
            int score = calculate_score(cuts_x, cuts_y);
            // Accept if score improves or stays same (allow plateau traversal)
            if (score >= current_score) {
                current_score = score;
                if (score > best_score) {
                    best_score = score;
                    best_cuts_x = cuts_x;
                    best_cuts_y = cuts_y;
                }
            } else {
                // Reject and revert
                if (is_x) cuts_x = backup;
                else cuts_y = backup;
            }
        }
    }
    
    // Output solution
    cout << best_cuts_x.size() + best_cuts_y.size() << "\n";
    
    // Output X cuts
    for (int val : best_cuts_x) {
        // Cut is strictly between uniq_x[val] and uniq_x[val+1]
        int x1 = uniq_x[val];
        int x2 = uniq_x[val+1];
        if (x2 - x1 > 1) {
            // Can use integer cut
            int mx = x1 + 1;
            cout << mx << " -1000000000 " << mx << " 1000000000\n"; 
        } else {
            // Gap is 1, use slanted line to emulate x = x1 + 0.5
            // Line through (x1, -1e9) and (x1+1, 1e9)
            cout << x1 << " -1000000000 " << x1 + 1 << " 1000000000\n";
        }
    }
    
    // Output Y cuts
    for (int val : best_cuts_y) {
        int y1 = uniq_y[val];
        int y2 = uniq_y[val+1];
        if (y2 - y1 > 1) {
            int my = y1 + 1;
            cout << "-1000000000 " << my << " 1000000000 " << my << "\n";
        } else {
            // Gap is 1, use slanted line to emulate y = y1 + 0.5
            // Line through (-1e9, y1) and (1e9, y1+1)
            cout << "-1000000000 " << y1 << " 1000000000 " << y1 + 1 << "\n";
        }
    }
    
    return 0;
}