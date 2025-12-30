#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int n, m;
int L;
int current_u;

// Function to perform a query
// Rotates 'ring' by 'd' (1 or -1)
// Updates current_u and returns it
int query(int ring, int d) {
    cout << "? " << ring << " " << d << endl;
    int u;
    cin >> u;
    return u;
}

struct Peak {
    int pos;
    int val;
};

// Sort peaks by position to minimize travel distance
bool comparePeaksPos(const Peak& a, const Peak& b) {
    return a.pos < b.pos;
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;
    L = n * m;

    // Scan ring 0 to build the profile
    vector<int> prof(L);
    
    // We assume the starting position of ring 0 is index 0.
    // Get initial U value by wiggling or just moving forward.
    // To be consistent with 0..L-1 indexing, we can query +1 L times.
    // But we need the value at 0.
    // Let's rotate +1, get value at 1. Then -1, get value at 0.
    int u_at_1 = query(0, 1);
    int u_at_0 = query(0, -1);
    current_u = u_at_0;
    prof[0] = u_at_0;
    
    int pos0 = 0; // Tracks relative position of ring 0 from start
    // Scan loop
    for (int i = 1; i < L; ++i) {
        current_u = query(0, 1);
        pos0++;
        prof[pos0] = current_u;
    }
    // Return to 0
    current_u = query(0, 1); // This completes the circle (pos L equivalent to 0)
    pos0 = 0; 
    
    // Identify peaks (local maxima)
    vector<Peak> peaks;
    for (int i = 0; i < L; ++i) {
        int prev = prof[(i - 1 + L) % L];
        int next = prof[(i + 1) % L];
        // We include plateaus as peaks
        if (prof[i] >= prev && prof[i] >= next) {
            peaks.push_back({i, prof[i]});
        }
    }
    
    // Sort peaks by position for efficient traversal
    sort(peaks.begin(), peaks.end(), comparePeaksPos);
    
    vector<int> p(n); // Result relative positions
    vector<bool> found(n, false);
    int found_count = 0;
    vector<int> ring_pos(n, 0); // Tracks relative position of each ring from start
    
    // Iterate through peaks
    for (const auto& peak : peaks) {
        if (found_count == n - 1) break;
        
        int target = peak.pos;
        
        // Move ring 0 to target peak
        int diff = (target - pos0 + L) % L;
        if (diff <= L / 2) {
            for (int k = 0; k < diff; ++k) current_u = query(0, 1);
        } else {
            for (int k = 0; k < L - diff; ++k) current_u = query(0, -1);
        }
        pos0 = target;
        
        // Probe unassigned rings
        for (int j = 1; j < n; ++j) {
            if (found[j]) continue;
            
            int u_base = current_u;
            // Try moving ring j by +1
            int u_p1 = query(j, 1);
            ring_pos[j] = (ring_pos[j] + 1) % L;
            
            bool is_found = false;
            
            if (u_p1 > u_base) {
                // Hill climbing in +1 direction
                current_u = u_p1;
                while (true) {
                    int u_next = query(j, 1);
                    ring_pos[j] = (ring_pos[j] + 1) % L;
                    if (u_next > current_u) {
                        current_u = u_next;
                    } else {
                        // Peak passed, step back
                        current_u = query(j, -1);
                        ring_pos[j] = (ring_pos[j] - 1 + L) % L;
                        is_found = true;
                        break;
                    }
                }
            } else {
                // +1 didn't improve. Undo +1.
                current_u = query(j, -1);
                ring_pos[j] = (ring_pos[j] - 1 + L) % L;
                
                // Try moving ring j by -1
                int u_m1 = query(j, -1);
                ring_pos[j] = (ring_pos[j] - 1 + L) % L;
                
                if (u_m1 > u_base) {
                    // Hill climbing in -1 direction
                    current_u = u_m1;
                    while (true) {
                        int u_next = query(j, -1);
                        ring_pos[j] = (ring_pos[j] - 1 + L) % L;
                        if (u_next > current_u) {
                            current_u = u_next;
                        } else {
                            // Peak passed, step back
                            current_u = query(j, 1);
                            ring_pos[j] = (ring_pos[j] + 1) % L;
                            is_found = true;
                            break;
                        }
                    }
                } else {
                    // Both +1 and -1 are worse or equal.
                    // Check for significant drop indicating alignment.
                    // If u_p1 < u_base and u_m1 < u_base, we are at a local maximum.
                    if (u_p1 < u_base && u_m1 < u_base) {
                        is_found = true;
                        // Restore position from -1 to 0
                        current_u = query(j, 1);
                        ring_pos[j] = (ring_pos[j] + 1) % L;
                    } else {
                        // Not found or plateau/noise. Restore to base.
                        current_u = query(j, 1);
                        ring_pos[j] = (ring_pos[j] + 1) % L;
                    }
                }
            }
            
            if (is_found) {
                found[j] = true;
                found_count++;
                // Calculate initial relative position
                // pos0 and ring_pos[j] are displacements from start
                // They are currently aligned.
                // p[j] = (pos0 - ring_pos[j])
                int rel = (pos0 - ring_pos[j]) % L;
                if (rel < 0) rel += L;
                p[j] = rel;
            }
        }
    }
    
    cout << "!";
    for (int i = 1; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
    
    return 0;
}