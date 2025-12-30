#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

int n, m, S;
long long moves_made[105];
bool solved[105];
long long rel_pos[105]; // relative to probe: start_i - start_probe
int last_val;

int query(int id, int dir) {
    cout << "? " << id << " " << dir << endl;
    int val; 
    cin >> val;
    if (val == -1) exit(0); // Error or end
    moves_made[id] += dir;
    last_val = val;
    return val;
}

void move_ring(int id, int amount) {
    if (amount == 0) return;
    int d = (amount > 0) ? 1 : -1;
    int steps = abs(amount);
    for (int k=0; k<steps; ++k) query(id, d);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;
    S = n * m;

    // Initial dummy query to get starting value
    cout << "? 0 1" << endl;
    int v; cin >> v;
    moves_made[0]++;
    cout << "? 0 -1" << endl;
    cin >> v;
    moves_made[0]--;
    last_val = v;

    int probe = -1;
    // Try to find a probe with some variance
    for (int i = 0; i < n; ++i) {
        int base = last_val;
        bool varies = false;
        
        int v1 = query(i, 1);
        if (v1 != base) varies = true;
        query(i, -1);

        if (!varies) {
            // Try moving a bit more
            int v2 = query(i, 1);
            int v3 = query(i, 1);
            if (v2 != base || v3 != base) varies = true;
            query(i, -1);
            query(i, -1);
        }

        if (varies) {
            probe = i;
            break;
        }
    }
    if (probe == -1) probe = 0;

    solved[probe] = true;
    rel_pos[probe] = 0;
    int solved_count = 1;

    while (solved_count < n) {
        // Scan probe
        vector<int> profile(S);
        profile[0] = last_val;
        for (int k = 1; k < S; ++k) {
            profile[k] = query(probe, 1);
        }
        query(probe, 1); // Complete the loop back to 0 (mod S) relative to start

        // Find peaks
        vector<pair<int, int>> peaks;
        for (int k = 0; k < S; ++k) {
            peaks.push_back({profile[k], k});
        }
        sort(peaks.rbegin(), peaks.rend());

        int checks_budget = 2500; 
        int checks_done = 0;
        int max_peaks = 40; 

        // Try top peaks
        for (int p_idx = 0; p_idx < S && p_idx < max_peaks; ++p_idx) {
            int shift = peaks[p_idx].second;
            
            // Move probe to 'shift' relative to start of loop
            // Since we are at 0 relative to start, just move 'shift'
            move_ring(probe, shift);

            vector<int> just_solved;
            for (int i = 0; i < n; ++i) {
                if (!solved[i]) {
                    // Wiggle check
                    int base_p = last_val;
                    int v_p = query(probe, 1);
                    query(probe, -1);
                    int v_i = query(i, 1);
                    query(i, -1);
                    
                    bool aligned = false;
                    if (v_p == v_i) {
                        int v_p2 = query(probe, -1);
                        query(probe, 1);
                        int v_i2 = query(i, -1);
                        query(i, 1);
                        if (v_p2 == v_i2) aligned = true;
                    }
                    
                    if (aligned) {
                        solved[i] = true;
                        just_solved.push_back(i);
                        // start_i - start_probe = moves[probe] - moves[i]
                        rel_pos[i] = (moves_made[probe] - moves_made[i]) % S;
                    }
                    checks_done++;
                }
            }

            // Move newly found rings to expose what's underneath
            for (int id : just_solved) {
                move_ring(id, m);
                solved_count++;
            }

            // Return probe to 0
            move_ring(probe, -shift);

            if (solved_count == n) break;
            if (checks_done > checks_budget) break;
        }
        if (solved_count == n) break;
    }

    cout << "!";
    long long rp0 = rel_pos[0];
    for (int i = 1; i < n; ++i) {
        long long val = (rel_pos[i] - rp0) % S;
        if (val < 0) val += S;
        cout << " " << val;
    }
    cout << endl;

    return 0;
}