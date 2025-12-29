#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>

using namespace std;

int n, m;
int total_sections;
int query_count = 0;
const int MAX_QUERIES = 30000;

// Track the cumulative displacement of each ring from its initial position
vector<int> current_pos;
// Store the synchronization difference: sync_diff[i] = pos[0] - pos[i] at moment of alignment
// This implies x_i - x_0 = pos[0] - pos[i] (where x are initial positions)
vector<int> sync_diff;
vector<bool> found;

int query(int ring, int dir) {
    if (query_count >= MAX_QUERIES) {
        // Fallback or just return dummy, assuming loop handles it
        return -1;
    }
    cout << "? " << ring << " " << dir << endl;
    query_count++;
    
    current_pos[ring] += dir;
    
    int result;
    cin >> result;
    return result;
}

int main() {
    if (!(cin >> n >> m)) return 0;
    total_sections = n * m;
    
    current_pos.assign(n, 0);
    sync_diff.assign(n, 0);
    found.assign(n, false);
    
    // We scan ring 0 through checkpoints 0, m, 2m, ...
    // For each checkpoint, we check all unfound rings.
    
    // We need to keep track of ring 0's movement relative to start
    // current_pos[0] tracks this.
    
    // Initial query to get baseline
    // Actually we don't need a baseline if we just use differences.
    int current_val = -1;
    // Perform a dummy query to get current value? 
    // Or just rotate 0 by 0? Not allowed.
    // Rotate 0 by 1 then -1
    current_val = query(0, 1);
    current_val = query(0, -1);
    
    int num_found = 0;
    
    // Checkpoints
    for (int cp = 0; cp < n; ++cp) {
        if (num_found == n - 1) break;
        if (query_count >= MAX_QUERIES - 200) break; // Buffer
        
        // Target displacement for ring 0 is cp * m
        // But we want to visit efficiently.
        // Current ring 0 pos is current_pos[0].
        // Target is cp * m.
        // Move ring 0 to target
        int target = cp * m;
        int diff = target - current_pos[0];
        // Move towards target
        while (current_pos[0] != target && query_count < MAX_QUERIES) {
            int d = (diff > 0) ? 1 : -1;
            current_val = query(0, d);
            diff -= d; // diff decreases
        }
        
        // Now check unfound rings
        for (int i = 1; i < n; ++i) {
            if (found[i]) continue;
            if (query_count >= MAX_QUERIES - 50) break;
            
            // Check interaction
            // Move ring i by 1
            int v1 = current_val;
            int v2 = query(i, 1);
            
            bool interact = false;
            int direction = 0;
            
            if (v2 < v1) {
                // Moving +1 improved overlap (reduced unblocked count)
                interact = true;
                direction = 1;
            } else {
                // Try moving back (to 0) then -1
                int v3 = query(i, -1); // Back at start, val should be v1
                // Actually result might differ if env changed? No, static env.
                
                int v4 = query(i, -1); // Position -1
                if (v4 < v1) {
                    interact = true;
                    direction = -1;
                    // Update current_val to v4
                    current_val = v4;
                } else {
                    // Back to start
                    current_val = query(i, 1);
                    // Check for local peak or interaction
                    if (v2 > v1 && v4 > v1) {
                        // We are at a local peak (both dirs bad)
                        // This counts as found!
                        interact = true;
                        direction = 0;
                    }
                }
            }
            
            if (interact) {
                // Hill climb
                if (direction != 0) {
                    while (true) {
                         if (query_count >= MAX_QUERIES) break;
                         int next_val = query(i, direction);
                         if (next_val > current_val) {
                             // Got worse, step back
                             current_val = query(i, -direction);
                             break;
                         }
                         current_val = next_val;
                         // If equal, we continue? 
                         // With boolean overlap, plateau possible.
                         // But we want center. 
                         // Let's assume improvement stops means peak.
                         if (next_val == current_val) {
                             // If plateau, maybe continue?
                             // Risk of drifting. Stop.
                             break;
                         }
                    }
                }
                
                // Mark found
                found[i] = true;
                num_found++;
                // Record sync
                sync_diff[i] = current_pos[0] - current_pos[i];
            }
        }
    }
    
    cout << "!";
    for (int i = 1; i < n; ++i) {
        // Calculate final relative position
        // x_i - x_0 = sync_diff[i]
        // p_i = (x_i + current_pos[i]) - (x_0 + current_pos[0])
        //     = (x_i - x_0) + (current_pos[i] - current_pos[0])
        //     = sync_diff[i] + current_pos[i] - current_pos[0]
        long long p = (long long)sync_diff[i] + current_pos[i] - current_pos[0];
        p %= total_sections;
        if (p < 0) p += total_sections;
        cout << " " << p;
    }
    cout << endl;
    
    return 0;
}